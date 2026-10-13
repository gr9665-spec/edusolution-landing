"""노션 데이터베이스 행을 reviews 항목으로 바꾸는 순수 함수들(네트워크 없음).

노션 데이터베이스의 칸 이름·형식은 docs/superpowers/specs/2026-10-13-notion-sync-design.md 3번을 따른다.
"""
from __future__ import annotations

import html
from typing import Callable, Mapping, Sequence

from .core import BuildError

KIND_LABELS = {"글 후기": "text", "대화 캡처": "capture"}
GOAL_LABELS = {"학위 취득": "degree", "자격증": "license", "편입": "transfer", "대학원": "grad"}
TEXT_COLUMNS = (("한줄제목", "headline"), ("본문", "body"), ("소개", "meta"), ("배지", "badge"))
SOURCE = "Notion 후기 데이터베이스"


class NotionError(BuildError):
    """노션 행이 규칙에 맞지 않을 때. 어느 행(수강생 이름)·어느 칸인지 메시지에 담는다."""


def plain(rich_text: Sequence[Mapping]) -> str:
    return "".join(part.get("plain_text", "") for part in rich_text or [])


def rich_text_to_html(rich_text: Sequence[Mapping], bold_tag: str) -> str:
    """노션 텍스트를 안전한 HTML로 바꾼다. 모든 글자는 이스케이프하고, 줄바꿈은 <br>, 굵게는 bold_tag로만 바꾼다."""
    out = []
    for part in rich_text or []:
        text = html.escape(part.get("plain_text", ""), quote=True).replace("\r\n", "\n").replace("\n", "<br>")
        if text and part.get("annotations", {}).get("bold"):
            text = "<%s>%s</%s>" % (bold_tag, text, bold_tag)
        out.append(text)
    return "".join(out)


def _prop(page: Mapping, name: str, who: str) -> Mapping:
    props = page.get("properties", {})
    if name not in props:
        raise NotionError("%s: 노션 데이터베이스에 '%s' 칸이 없습니다 (칸 이름이 정확히 같아야 합니다)" % (who, name))
    return props[name]


def _title(page: Mapping) -> str:
    prop = page.get("properties", {}).get("이름") or {}
    return plain(prop.get("title", [])).strip()


def row_to_item(page: Mapping, download_image: Callable[[str], str]) -> dict:
    """노션 행 하나를 reviews 항목으로 바꾼다. download_image(url)는 사이트 안의 이미지 경로(assets/…)를 돌려준다."""
    who = _title(page)
    if not who:
        raise NotionError("행 %s: '이름' 칸이 비어 있습니다" % page.get("id", "?")[:8])
    row_id = page["id"].replace("-", "")[:8]

    kind_sel = _prop(page, "종류", who).get("select")
    kind = KIND_LABELS.get(kind_sel["name"]) if kind_sel else None
    if kind is None:
        raise NotionError("%s: '종류' 칸은 %s 중 하나여야 합니다" % (who, " / ".join(KIND_LABELS)))

    goals = []
    for opt in _prop(page, "분류", who).get("multi_select", []):
        if opt["name"] not in GOAL_LABELS:
            raise NotionError("%s: '분류' 칸에 알 수 없는 값 '%s'가 있습니다 (허용: %s)" % (who, opt["name"], ", ".join(GOAL_LABELS)))
        goals.append(GOAL_LABELS[opt["name"]])
    if not goals:
        raise NotionError("%s: '분류' 칸이 비어 있습니다" % who)

    item = {"id": "notion-%s" % row_id, "kind": kind, "goal": goals, "person": who, "source": SOURCE}

    if kind == "text":
        for column, key in TEXT_COLUMNS:
            rich = _prop(page, column, who).get("rich_text", [])
            if not plain(rich).strip():
                raise NotionError("%s: 글 후기는 '%s' 칸이 필요합니다" % (who, column))
            item[key] = rich_text_to_html(rich, "mark" if column == "한줄제목" else "strong") if column in ("한줄제목", "본문") \
                else plain(rich).strip()
        item["featured"] = bool(page["properties"].get("대표", {}).get("checkbox"))
    else:
        files = _prop(page, "이미지", who).get("files", [])
        if not files:
            raise NotionError("%s: 대화 캡처는 '이미지' 칸에 파일이 필요합니다" % who)
        first = files[0]
        url = first["file"]["url"] if first.get("type") == "file" else first["external"]["url"]
        item["image"] = download_image(url)
        item["alt"] = "%s의 수강 후기 대화 캡처" % who
        period = plain(page["properties"].get("시기", {}).get("rich_text", [])).strip()
        if period:
            item["period"] = period
    return item


def rows_to_items(pages: Sequence[Mapping], download_image: Callable[[str], str]) -> list:
    """공개된 행만 골라 항목으로 바꾸고 정렬한다(순서 칸 오름차순, 순서가 없으면 최신 등록순)."""
    published = [p for p in pages if p.get("properties", {}).get("공개", {}).get("checkbox")]

    def order(p):
        number = (p["properties"].get("순서") or {}).get("number")
        return (0, number, "") if number is not None else (1, 0, "")

    # 최신 등록순(내림차순) -> 순서 칸 오름차순(안정 정렬이라 순서가 같거나 없으면 최신순이 유지된다)
    published = sorted(published, key=lambda p: p.get("created_time", ""), reverse=True)
    published = sorted(published, key=order)
    items = [row_to_item(p, download_image) for p in published]
    seen = set()
    for item in items:
        if item["id"] in seen:
            raise NotionError("행 ID 앞 8자가 겹치는 행이 있습니다(중복): %s" % item["id"])
        seen.add(item["id"])
    return items
