"""data/*.json 읽기와 검증. 규칙에 어긋나면 DataError로 어디가 문제인지 알려준다."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .core import BuildError

GOALS = ("degree", "license", "transfer", "grad")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
AS_OF_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


class DataError(BuildError):
    """데이터 파일의 내용이 규칙에 맞지 않을 때."""


def load(root: Path, name: str, default: Any) -> Any:
    path = root / "data" / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_bytes().decode("utf-8-sig"))   # 메모장이 붙이는 BOM도 허용
    except json.JSONDecodeError as exc:
        raise DataError("%s: JSON 형식 오류 (%s)" % (name, exc)) from exc


def _require(item: Mapping, keys: Sequence[str], where: str) -> None:
    for key in keys:
        value = item.get(key)
        if value is None or (isinstance(value, (str, list, dict)) and not value):
            raise DataError("%s: 필수 항목 '%s'이(가) 없거나 비어 있습니다" % (where, key))


def _exists(root: Path, rel: str, where: str, key: str) -> None:
    """이미지 경로는 assets/ 안의 상대경로여야 한다(원본 폴더·저장소 밖을 가리키면 사이트에서 깨지거나 원본이 노출된다)."""
    parts = rel.replace("\\", "/").split("/") if isinstance(rel, str) else []
    if (not isinstance(rel, str) or "\\" in rel or ":" in rel or rel.startswith("/")
            or ".." in parts or parts[0] != "assets" or len(parts) < 2):
        raise DataError("%s: '%s'은(는) assets/ 폴더 안의 상대경로여야 합니다 (예: assets/proof/a.jpg): %s" % (where, key, rel))
    if not (root / rel).is_file():
        raise DataError("%s: '%s'에 적힌 파일이 없습니다: %s" % (where, key, rel))


PII_RE = re.compile(r"(?<!\d)01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)|[\w.+-]+@[\w-]+\.[\w.-]+")


def _no_pii(value, where: str) -> None:
    """공개되는 데이터에 전화번호·이메일이 섞여 들어가지 않게 한다(data/*.json은 사이트에 그대로 공개된다)."""
    if isinstance(value, str):
        m = PII_RE.search(value)
        if m:
            raise DataError("%s: 개인정보로 보이는 값이 들어 있습니다 (%s). 전화번호·이메일은 쓰지 마세요" % (where, m.group(0)))
    elif isinstance(value, Mapping):
        for v in value.values():
            _no_pii(v, where)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _no_pii(v, where)


# ---------------------------------------------------------------- 후기 (reviews.json)

def _check_text(item, root, where, team_ids) -> None:
    _require(item, ["headline", "body", "person", "meta", "badge"], where)


def _check_capture(item, root, where, team_ids) -> None:
    _require(item, ["image", "alt", "person"], where)
    _exists(root, item["image"], where, "image")


def _check_case(item, root, where, team_ids) -> None:
    _require(item, ["slug", "title", "school", "track", "profile", "plan", "duration", "result",
                    "planner", "seoDescription"], where)
    if not SLUG_RE.match(item["slug"]):
        raise DataError("%s: slug '%s'은(는) 영문 소문자·숫자·하이픈만 쓸 수 있습니다 (예: konkuk-transfer-2026)" % (where, item["slug"]))
    _require(item["profile"], ["age", "background", "credits"], where + ".profile")
    for row in item["plan"]:
        _require(row, ["label", "detail"], where + ".plan")
    if item["planner"] not in team_ids:
        raise DataError("%s: planner '%s'이(가) team.json에 없습니다" % (where, item["planner"]))
    for rel in item.get("proofImages", []):
        _exists(root, rel, where, "proofImages")


KIND_CHECKS = {"text": _check_text, "capture": _check_capture, "case": _check_case}


def validate_reviews(items: Sequence[Mapping], root: Path, team_ids=frozenset()) -> None:
    ids, slugs = set(), set()
    for item in items:
        where = "reviews.json[%s]" % item.get("id", "?")
        _require(item, ["id", "kind", "goal", "source"], where)
        _no_pii(item, where)
        if item["id"] in ids:
            raise DataError("%s: id가 중복됩니다" % where)
        ids.add(item["id"])
        bad = [g for g in item["goal"] if g not in GOALS]
        if bad:
            raise DataError("%s: 알 수 없는 goal %s (허용: %s)" % (where, bad, ", ".join(GOALS)))
        check = KIND_CHECKS.get(item["kind"])
        if check is None:
            raise DataError("%s: 알 수 없는 kind '%s' (허용: %s)" % (where, item["kind"], ", ".join(KIND_CHECKS)))
        if item.get("featured") and item["kind"] != "text":
            raise DataError("%s: featured는 글 후기(text)에만 쓸 수 있습니다" % where)
        check(item, root, where, team_ids)
        if "slug" in item:
            if item["slug"] in slugs:
                raise DataError("%s: slug '%s'이(가) 중복됩니다" % (where, item["slug"]))
            slugs.add(item["slug"])


# ---------------------------------------------------------------- 팀 (team.json)

YOUTUBE_RE = re.compile(r"^https://(www\.|m\.)?(youtube\.com|youtu\.be)/\S+$")


def _check_youtube(url, where: str, key: str = "youtube") -> None:
    """유튜브 주소는 https://www.youtube.com/… 형태만 허용한다(엉뚱한 사이트·스크립트 링크 차단)."""
    if not isinstance(url, str) or not YOUTUBE_RE.match(url):
        raise DataError("%s: '%s'는 https://www.youtube.com/@채널이름 같은 유튜브 주소여야 합니다: %s" % (where, key, url))


def validate_team(items: Sequence[Mapping], root: Path) -> set:
    ids = set()
    for item in items:
        where = "team.json[%s]" % item.get("id", "?")
        _require(item, ["id", "name", "role", "photo", "bio", "tags"], where)
        if item["id"] in ids:
            raise DataError("%s: id가 중복됩니다" % where)
        ids.add(item["id"])
        _exists(root, item["photo"], where, "photo")
        career = item.get("career", [])
        if not isinstance(career, list) or not all(isinstance(c, str) and c for c in career):
            raise DataError("%s: career는 비어 있지 않은 문자열 목록이어야 합니다" % where)
        if item.get("youtube"):
            _check_youtube(item["youtube"], where)
    return ids


def validate_youtube(channel: Mapping) -> None:
    """팀 유튜브 채널(data/youtube.json). 비어 있으면 구역이 나오지 않는다."""
    if not channel:
        return
    _require(channel, ["name", "url"], "youtube.json")
    _check_youtube(channel["url"], "youtube.json", "url")


# ---------------------------------------------------------------- 실적 수치 (stats.json)

def validate_stats(items: Sequence[Mapping]) -> None:
    if len(items) > 6:
        raise DataError("stats.json: 수치는 최대 6개까지 쓸 수 있습니다 (현재 %d개)" % len(items))
    for n, item in enumerate(items, 1):
        where = "stats.json[%d]" % n
        _require(item, ["value", "label", "asOf"], where)      # source(근거 문구)는 선택
        value = item["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise DataError("%s: value는 0 이상의 숫자여야 합니다" % where)
        if not AS_OF_RE.match(item["asOf"]):
            raise DataError("%s: asOf는 '2026-10' 또는 '2026-10-12' 형식이어야 합니다" % where)


# ---------------------------------------------------------------- 사업자 정보 (business.json)

def validate_business(biz: Mapping) -> None:
    if not biz:
        return
    _require(biz, ["company", "regno", "address"], "business.json")      # ceo(대표자)는 선택
    for rep in biz.get("reports", []):
        _require(rep, ["label", "value"], "business.json.reports")
