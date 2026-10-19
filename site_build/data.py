"""data/*.json 읽기와 검증. 규칙에 어긋나면 DataError로 어디가 문제인지 알려준다."""
from __future__ import annotations

import datetime
import json
import re
import urllib.parse
from html.parser import HTMLParser
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

DEFAULT_IMAGE = "assets/review-default.jpg"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SAFE_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
INTERNAL_URL_RE = re.compile(r"/(?!/)[^\s\"'<>]*")      # 사이트 안 주소(/pages/…). '//' 로 시작하는 외부 주소는 거부

# 본문에 쓸 수 있는 태그와, 태그마다 허용하는 속성
BODY_TAGS = {
    "p": (), "h2": (), "h3": (), "strong": (), "em": (), "ul": (), "ol": (), "li": (), "blockquote": (),
    "hr": (), "br": (), "figure": (), "figcaption": (),
    "table": (), "thead": (), "tbody": (), "tr": (), "th": (), "td": (),
    "a": ("href", "target", "rel"),
    "img": ("src", "alt", "loading", "decoding", "width", "height"),
}
VOID_TAGS = {"hr", "br", "img"}
FIXED_ATTRS = {("a", "target"): "_blank", ("a", "rel"): "noopener noreferrer"}


class _BodyChecker(HTMLParser):
    """본문 HTML이 허용 목록 안에 있는지 검사한다. 주석·선언·끝맺지 않은 태그·짝이 안 맞는 태그처럼
    브라우저와 파서가 다르게 읽을 수 있는 구조는 모두 거부한다(이스케이프하지 않은 '<'도 거부)."""

    def __init__(self, root: Path, where: str):
        super().__init__(convert_charrefs=False)
        self.root, self.where, self.stack = root, where, []

    def _bad(self, why: str) -> DataError:
        return DataError("%s: body에 허용되지 않는 내용이 있습니다 (%s)" % (self.where, why))

    def _check_start(self, tag, attrs):
        if tag not in BODY_TAGS:
            raise self._bad("<%s> 태그는 쓸 수 없습니다" % tag)
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            raise self._bad("<%s>에 같은 속성이 두 번 있습니다" % tag)
        for name, value in attrs:
            if name not in BODY_TAGS[tag]:
                raise self._bad("<%s>의 '%s' 속성은 쓸 수 없습니다" % (tag, name))
            if (tag, name) in FIXED_ATTRS and value != FIXED_ATTRS[(tag, name)]:
                raise self._bad("<%s>의 %s는 '%s'만 쓸 수 있습니다" % (tag, name, FIXED_ATTRS[(tag, name)]))
            if tag == "a" and name == "href" and not (SAFE_URL_RE.fullmatch(value or "") or INTERNAL_URL_RE.fullmatch(value or "")):
                raise self._bad("링크는 http·https 주소이거나 /로 시작하는 사이트 안 주소여야 합니다: %s" % value)
            if tag == "img" and name == "src":
                if not (value or "").startswith("/"):
                    raise self._bad("이미지 주소는 /assets/… 처럼 /로 시작해야 합니다: %s" % value)
                _exists(self.root, urllib.parse.unquote(value.lstrip("/")), self.where, "body 이미지")
        if tag == "img" and "src" not in names:
            raise self._bad("<img>에는 src가 필요합니다")

    def handle_starttag(self, tag, attrs):
        self._check_start(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self._check_start(tag, attrs)
        if tag not in VOID_TAGS:
            raise self._bad("<%s/> 형태로는 쓸 수 없습니다" % tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS or not self.stack or self.stack.pop() != tag:
            raise self._bad("</%s> 태그의 짝이 맞지 않습니다" % tag)

    def handle_data(self, data):
        if "<" in data:
            raise self._bad("끝맺지 않은 태그이거나 이스케이프하지 않은 '<'가 있습니다")

    def handle_comment(self, data):
        raise self._bad("주석은 쓸 수 없습니다")

    def handle_decl(self, decl):
        raise self._bad("선언(<!…>)은 쓸 수 없습니다")

    def handle_pi(self, data):
        raise self._bad("처리 명령(<?…>)은 쓸 수 없습니다")

    def unknown_decl(self, data):
        raise self._bad("선언(<![…]>)은 쓸 수 없습니다")


def _check_body(body, root: Path, where: str) -> None:
    if not isinstance(body, str):
        raise DataError("%s: body는 문자열이어야 합니다" % where)
    checker = _BodyChecker(root, where)
    checker.feed(body)
    checker.close()
    if checker.stack:
        raise checker._bad("<%s> 태그가 닫히지 않았습니다" % checker.stack[-1])


def validate_reviews(items: Sequence[Mapping], root: Path) -> None:
    ids, slugs = set(), set()
    for item in items:
        where = "reviews.json[%s]" % item.get("id", "?")
        _require(item, ["id", "kind", "slug", "title", "subtitle", "category", "body", "source"], where)
        _no_pii(item, where)
        if item["kind"] != "post":
            raise DataError("%s: 알 수 없는 kind '%s' (허용: post)" % (where, item["kind"]))
        if item["id"] in ids:
            raise DataError("%s: id가 중복됩니다" % where)
        ids.add(item["id"])
        if item["category"] not in GOALS:
            raise DataError("%s: 알 수 없는 category '%s' (허용: %s)" % (where, item["category"], ", ".join(GOALS)))
        if not isinstance(item["slug"], str) or not SLUG_RE.match(item["slug"]):
            raise DataError("%s: slug '%s'은(는) 영문 소문자·숫자·하이픈만 쓸 수 있습니다 (예: r-1a2b3c4d)" % (where, item["slug"]))
        if item["slug"] in slugs:
            raise DataError("%s: slug '%s'이(가) 중복됩니다" % (where, item["slug"]))
        slugs.add(item["slug"])
        if "date" in item:
            _check_date(item["date"], where, "date")
        if item.get("image"):
            _exists(root, item["image"], where, "image")
        _check_body(item["body"], root, where)


def _check_date(value, where: str, key: str) -> None:
    try:
        if not (isinstance(value, str) and DATE_RE.fullmatch(value)):
            raise ValueError
        datetime.date.fromisoformat(value)
    except ValueError:
        raise DataError("%s: %s는 2026-10-13 형식의 실제 날짜여야 합니다: %s" % (where, key, value)) from None


# ---------------------------------------------------------------- 교육정보 글 (articles.json)

def validate_articles(items: Sequence[Mapping], root: Path) -> None:
    ids, slugs = set(), set()
    for item in items:
        where = "articles.json[%s]" % item.get("id", "?")
        _require(item, ["id", "slug", "title", "description", "category", "date", "body", "source"], where)
        _no_pii(item, where)
        if item["id"] in ids:
            raise DataError("%s: id가 중복됩니다" % where)
        ids.add(item["id"])
        if item["category"] not in GOALS:
            raise DataError("%s: 알 수 없는 category '%s' (허용: %s)" % (where, item["category"], ", ".join(GOALS)))
        if not isinstance(item["slug"], str) or not SLUG_RE.match(item["slug"]):
            raise DataError("%s: slug '%s'은(는) 영문 소문자·숫자·하이픈만 쓸 수 있습니다 (예: credit-bank-degree-credits)" % (where, item["slug"]))
        if item["slug"] in slugs:
            raise DataError("%s: slug '%s'이(가) 중복됩니다" % (where, item["slug"]))
        slugs.add(item["slug"])
        _check_date(item["date"], where, "date")
        if "updated" in item:
            _check_date(item["updated"], where, "updated")
        _check_body(item["body"], root, where)
    for item in items:
        for slug in item.get("related", []):
            if slug not in slugs:
                raise DataError("articles.json[%s]: related에 적은 '%s' 글이 없습니다" % (item["id"], slug))


# ---------------------------------------------------------------- 팀 (team.json)

PHONE_RE = re.compile(r"0\d{1,2}-\d{3,4}-\d{4}")
KAKAO_ID_RE = re.compile(r"[A-Za-z0-9._-]{3,30}")
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
        if "slogan" in item and not (isinstance(item["slogan"], str) and item["slogan"].strip()):
            raise DataError("%s: slogan은 비어 있지 않은 문장이어야 합니다 (쓰지 않으려면 항목을 지우세요)" % where)
        if "phone" in item and not (isinstance(item["phone"], str) and PHONE_RE.fullmatch(item["phone"])):
            raise DataError("%s: phone은 010-1234-5678 같은 형식이어야 합니다: %s" % (where, item["phone"]))
        if "kakao" in item and not (isinstance(item["kakao"], str) and KAKAO_ID_RE.fullmatch(item["kakao"])):
            raise DataError("%s: kakao는 영문·숫자·밑줄(_)·점(.)·하이픈(-)으로 된 3~30자 카카오톡 아이디여야 합니다: %s" % (where, item["kakao"]))
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


# ---------------------------------------------------------------- 분석 도구 (analytics.json)

GA4_RE = re.compile(r"G-[A-Z0-9]{6,14}")
NAVER_WA_RE = re.compile(r"[A-Za-z0-9_]{6,30}")


def validate_analytics(cfg: Mapping) -> None:
    """구글 애널리틱스 4 측정 ID(G-…)와 네이버 애널리틱스 ID. 둘 다 선택이며, 코드에 그대로 들어가므로 형식을 엄격히 검사한다."""
    for key, rule, example in (("ga4", GA4_RE, "G-ABC123XYZ9"), ("naver", NAVER_WA_RE, "s_1a2b3c4d5e6f")):
        if key in cfg and not (isinstance(cfg[key], str) and rule.fullmatch(cfg[key])):
            raise DataError("analytics.json: %s 형식이 올바르지 않습니다 (예: %s): %s" % (key, example, cfg[key]))


# ---------------------------------------------------------------- 사업자 정보 (business.json)

def validate_business(biz: Mapping) -> None:
    if not biz:
        return
    _require(biz, ["company", "regno", "address"], "business.json")      # ceo(대표자)는 선택
    for rep in biz.get("reports", []):
        _require(rep, ["label", "value"], "business.json.reports")
