"""노션 후기 데이터베이스를 읽어 data/reviews.notion.json 과 assets/proof/notion-*.jpg 를 만든다.

사용법(저장소 루트):  NOTION_TOKEN=... NOTION_DATABASE_ID=... python tools/notion_sync.py
표준 라이브러리와 Pillow만 쓴다. 노션 칸 구성은 docs/superpowers/specs/2026-10-13-notion-sync-design.md 3번을 따른다.
토큰은 어떤 출력·오류 메시지에도 넣지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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


def download(url: str, urlopen=urllib.request.urlopen, sleep=time.sleep) -> bytes:
    return _call(lambda: urllib.request.Request(url), urlopen, sleep, IMAGE_LIMIT)


def make_image_resolver(root: Path, fetch: Callable[[str], bytes]) -> Callable[[str], str]:
    """노션 파일 주소를 받아 가공한 JPEG를 assets/proof/notion-<해시>.jpg 로 저장하고 사이트 안 경로를 돌려준다.

    파일 이름은 주소의 경로 부분(쿼리의 만료되는 서명 제외)으로 만들어 같은 파일은 다시 받지 않는다.
    """
    def resolve(url: str) -> str:
        key = hashlib.sha1(urllib.parse.urlparse(url).path.encode("utf-8")).hexdigest()[:12]
        rel = "assets/proof/notion-%s.jpg" % key
        dst = root / rel
        if dst.exists():
            return rel
        raw = fetch(url)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "download"
            src.write_bytes(raw)
            try:
                mask_image(src, dst, [])        # 가로 1200px 이하 JPEG로 줄이고 EXIF를 지운다
            except Exception as exc:            # Pillow가 열지 못하는 파일(이미지가 아님)
                raise NotionError("이미지 파일을 열 수 없습니다(%s)" % type(exc).__name__) from None
        return rel
    return resolve


def sync(root: Path, rows: Sequence, fetch: Callable[[str], bytes]) -> dict:
    """행을 reviews 항목으로 바꿔 data/reviews.notion.json 에 쓰고, 쓰이지 않는 노션 이미지는 지운다."""
    items = notion.rows_to_items(rows, make_image_resolver(root, fetch))
    referenced = {item["image"] for item in items if "image" in item}
    removed = 0
    proof = root / "assets" / "proof"
    if proof.is_dir():
        for path in proof.glob("notion-*.jpg"):
            if "assets/proof/%s" % path.name not in referenced:
                path.unlink()
                removed += 1
    out = root / "data" / "reviews.notion.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(items, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {"items": len(items), "images": len(referenced), "removed_images": removed}


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
        summary = sync(ROOT, rows, download)
    except BuildError as exc:
        print("노션 동기화 실패: %s" % exc, file=sys.stderr)
        return 1
    print("노션 동기화 완료: 후기 %(items)d개, 이미지 %(images)d개, 정리한 이미지 %(removed_images)d개" % summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
