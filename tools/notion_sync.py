"""노션 후기 데이터베이스를 읽어 data/reviews.notion.json 과 assets/proof/notion-*.jpg 를 만든다.

사용법(저장소 루트):  NOTION_TOKEN=... NOTION_DATABASE_ID=... python tools/notion_sync.py
표준 라이브러리와 Pillow만 쓴다. 노션 칸 구성과 지원 블록은 docs/superpowers/specs/2026-10-13-review-posts-design.md 3번을 따른다.
토큰은 어떤 출력·오류 메시지에도 넣지 않는다.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from site_build import notion  # noqa: E402
from site_build.core import BuildError  # noqa: E402
from site_build.notion import NotionError  # noqa: E402
from tools.mask import mask_image  # noqa: E402

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
PACE_SECONDS = 0.35         # 노션 한도(초당 약 3회)를 지키려고 요청 사이에 쉬는 시간
MAX_BLOCK_DEPTH = 3
JSON_LIMIT = 50 * 1024 * 1024
IMAGE_LIMIT = 20 * 1024 * 1024


def _call(make_request: Callable, urlopen, sleep, limit: int) -> bytes:
    """요청을 보내고 본문을 돌려준다. 일시적 오류(429·5xx·연결 실패)는 늘려 가며 다시 시도한다."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urlopen(make_request(), timeout=30) as resp:
                body = resp.read(limit + 1)
            if len(body) > limit:
                raise NotionError("응답이 너무 큽니다(%d MB 초과)" % (limit // (1024 * 1024)))
            return body
        except urllib.error.HTTPError as exc:
            if exc.code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                sleep(2 ** attempt)
                continue
            raise NotionError("노션 요청이 실패했습니다 (HTTP %d)" % exc.code) from None
        except urllib.error.URLError as exc:
            if attempt < MAX_ATTEMPTS:
                sleep(2 ** attempt)
                continue
            raise NotionError("노션에 연결하지 못했습니다: %s" % exc.reason) from None
    raise NotionError("노션 요청이 반복해서 실패했습니다")      # 도달하지 않는다


def query_database(database_id: str, token: str, urlopen=urllib.request.urlopen, sleep=time.sleep) -> list:
    """공개 칸이 켜진 행을 모두 가져온다(100개씩 페이지를 넘긴다)."""
    url = "%s/databases/%s/query" % (API, database_id)
    rows: list = []
    cursor = None
    while True:
        body = {"page_size": 100, "filter": {"property": "공개", "checkbox": {"equals": True}}}
        if cursor:
            body["start_cursor"] = cursor
        payload_bytes = json.dumps(body).encode("utf-8")

        def make_request(data=payload_bytes):
            return urllib.request.Request(url, data=data, method="POST", headers={
                "Authorization": "Bearer " + token, "Notion-Version": NOTION_VERSION, "Content-Type": "application/json"})

        payload = json.loads(_call(make_request, urlopen, sleep, JSON_LIMIT).decode("utf-8"))
        rows.extend(payload.get("results", []))
        if not payload.get("has_more"):
            return rows
        cursor = payload["next_cursor"]


def _get_json(url: str, token: str, urlopen, sleep) -> dict:
    sleep(PACE_SECONDS)

    def make_request():
        return urllib.request.Request(url, method="GET", headers={
            "Authorization": "Bearer " + token, "Notion-Version": NOTION_VERSION})

    return json.loads(_call(make_request, urlopen, sleep, JSON_LIMIT).decode("utf-8"))


def fetch_blocks(block_id: str, token: str, urlopen=urllib.request.urlopen, sleep=time.sleep,
                 depth: int = MAX_BLOCK_DEPTH) -> list:
    """페이지(또는 블록)의 하위 블록을 모두 가져온다(100개씩 페이지를 넘기고, 하위 블록은 깊이 depth까지 children에 담는다)."""
    blocks: list = []
    cursor = None
    while True:
        url = "%s/blocks/%s/children?page_size=100" % (API, block_id)
        if cursor:
            url += "&start_cursor=" + urllib.parse.quote(cursor, safe="")
        payload = _get_json(url, token, urlopen, sleep)
        blocks.extend(payload.get("results", []))
        if not payload.get("has_more"):
            break
        cursor = payload["next_cursor"]
    if depth > 0:
        for block in blocks:
            if block.get("has_children") and block.get("type") not in ("child_page", "child_database"):
                block["children"] = fetch_blocks(block["id"], token, urlopen, sleep, depth - 1)
    return blocks


def download(url: str, urlopen=urllib.request.urlopen, sleep=time.sleep) -> bytes:
    return _call(lambda: urllib.request.Request(url), urlopen, sleep, IMAGE_LIMIT)


def make_image_resolver(root: Path, fetch: Callable[[str], bytes]) -> Callable[[str], str]:
    """노션 파일 주소를 받아 가공한 JPEG를 assets/proof/notion-<해시>.jpg 로 저장하고 사이트 안 경로를 돌려준다.

    파일 이름은 같은 파일이면 같아야 다시 받지 않는다. 노션이 올린 파일의 주소에는 만료되는 서명(X-Amz-…)이 붙으므로
    그때는 경로 부분만, 서명이 없는 외부 주소는 주소 전체(호스트·쿼리 포함)로 이름을 만든다.
    """
    def cache_key(url: str) -> str:
        parts = urllib.parse.urlparse(url)
        signed = any(k.lower().startswith("x-amz-") for k, _ in urllib.parse.parse_qsl(parts.query))
        return parts.path if signed else urllib.parse.urlunparse(parts._replace(fragment=""))

    def resolve(url: str) -> str:
        key = hashlib.sha1(cache_key(url).encode("utf-8")).hexdigest()[:12]
        rel = "assets/proof/notion-%s.jpg" % key
        dst = root / rel
        if dst.exists():
            return rel
        raw = fetch(url)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "download"
            src.write_bytes(raw)
            part = Path(tmp) / "result.jpg"
            try:
                mask_image(src, part, [])       # 가로 1200px 이하 JPEG로 줄이고 EXIF를 지운다
            except Exception as exc:            # Pillow가 열지 못하는 파일(이미지가 아님)
                raise NotionError("이미지 파일을 열 수 없습니다(%s)" % type(exc).__name__) from None
            dst.parent.mkdir(parents=True, exist_ok=True)
            staging = dst.with_name(dst.name + ".part")
            shutil.copyfile(part, staging)
            os.replace(staging, dst)            # 다 만든 뒤에 이름을 바꾼다(저장 중 끊겨도 깨진 파일이 남지 않는다)
        return rel
    return resolve


def sync(root: Path, rows: Sequence, fetch_page_blocks: Callable[[str], Sequence], fetch: Callable[[str], bytes]) -> dict:
    """행과 본문을 post 항목으로 바꿔 data/reviews.notion.json 에 쓰고, 쓰이지 않는 노션 이미지는 지운다."""
    resolve = make_image_resolver(root, fetch)
    used: set = set()

    def download_image(url: str) -> str:
        rel = resolve(url)
        used.add(rel)
        return rel

    skipped = collections.Counter()
    items = notion.rows_to_items(rows, fetch_page_blocks, download_image, skipped)
    removed = 0
    proof = root / "assets" / "proof"
    if proof.is_dir():
        for path in proof.glob("notion-*.jpg"):
            if "assets/proof/%s" % path.name not in used:
                path.unlink()
                removed += 1
    out = root / "data" / "reviews.notion.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(items, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {"items": len(items), "images": len(used), "removed_images": removed, "skipped_blocks": dict(skipped)}


def _database_id(value: str) -> str:
    """환경 변수에 주소 전체나 하이픈 있는 ID를 넣어도 32자리 ID를 뽑아 쓴다."""
    found = re.search(r"[0-9a-fA-F]{32}", value.replace("-", ""))
    return found.group(0) if found else value.strip()


def main(argv=None) -> int:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    database = os.environ.get("NOTION_DATABASE_ID", "").strip()
    missing = [name for name, value in (("NOTION_TOKEN", token), ("NOTION_DATABASE_ID", database)) if not value]
    if missing:
        print("환경 변수가 없습니다: %s (GitHub 저장소 설정의 Secrets·Variables에 넣어야 합니다)" % ", ".join(missing), file=sys.stderr)
        return 1
    try:
        rows = query_database(_database_id(database), token)
        summary = sync(ROOT, rows, lambda page_id: fetch_blocks(page_id, token), download)
    except BuildError as exc:
        print("노션 동기화 실패: %s" % exc, file=sys.stderr)
        return 1
    print("노션 동기화 완료: 후기 %(items)d개, 이미지 %(images)d개, 정리한 이미지 %(removed_images)d개" % summary)
    if summary["skipped_blocks"]:
        print("지원하지 않아 건너뛴 블록: %s" % ", ".join("%s %d개" % kv for kv in sorted(summary["skipped_blocks"].items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
