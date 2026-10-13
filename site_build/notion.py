"""노션 데이터베이스 행과 페이지 본문 블록을 reviews 항목(post)으로 바꾸는 순수 함수들(네트워크 없음).

노션 데이터베이스의 칸 이름·형식과 지원하는 블록은 docs/superpowers/specs/2026-10-13-review-posts-design.md 3번을 따른다.
"""
from __future__ import annotations

import datetime
import html
import re
from collections import Counter
from typing import Callable, Mapping, Optional, Sequence

from .core import BuildError
from .render import sort_posts

CATEGORY_LABELS = {"학위 취득": "degree", "자격증": "license", "편입": "transfer", "대학원": "grad"}
SOURCE = "Notion 후기 데이터베이스"
LINK_RE = re.compile(r"https?://[^\s\"'<>]+")
KST = datetime.timezone(datetime.timedelta(hours=9))


class NotionError(BuildError):
    """노션 행이 규칙에 맞지 않을 때. 어느 행(제목)·어느 칸인지 메시지에 담는다."""


def plain(rich_text: Sequence[Mapping]) -> str:
    return "".join(part.get("plain_text", "") for part in rich_text or [])


def rich_text_to_html(rich_text: Sequence[Mapping]) -> str:
    """노션 텍스트를 안전한 HTML로 바꾼다. 모든 글자는 이스케이프하고, 줄바꿈은 <br>,
    굵게·기울임·http(s) 링크만 태그로 바꾼다. 그 밖의 서식은 무시한다."""
    out = []
    for part in rich_text or []:
        text = html.escape(part.get("plain_text", ""), quote=True).replace("\r\n", "\n").replace("\n", "<br>")
        if not text:
            continue
        notes = part.get("annotations") or {}
        if notes.get("italic"):
            text = "<em>%s</em>" % text
        if notes.get("bold"):
            text = "<strong>%s</strong>" % text
        href = part.get("href")
        if href and LINK_RE.fullmatch(href):
            text = '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (html.escape(href, quote=True), text)
        out.append(text)
    return "".join(out)


# ---------------------------------------------------------------- 본문 블록

def _file_url(file_obj: Mapping) -> str:
    kind = file_obj.get("type")
    url = (file_obj.get(kind) or {}).get("url") if kind in ("file", "external") else None
    if not url:
        raise NotionError("이미지 주소를 읽을 수 없습니다 (이미지 블록 또는 페이지 커버를 확인해 주세요)")
    return url


def _children(block: Mapping, download_image, skipped) -> str:
    return blocks_to_html(block.get("children") or [], download_image, skipped)


def _list(blocks: Sequence[Mapping], tag: str, download_image, skipped) -> str:
    items = []
    for b in blocks:
        data = b[b["type"]]
        items.append("<li>%s%s</li>" % (rich_text_to_html(data.get("rich_text")), _children(b, download_image, skipped)))
    return "<%s>%s</%s>" % (tag, "".join(items), tag)


def blocks_to_html(blocks: Sequence[Mapping], download_image: Callable[[str], str],
                   skipped: Optional[Counter] = None) -> str:
    """페이지 본문 블록을 허용된 태그만 쓴 HTML로 바꾼다. 지원하지 않는 블록은 건너뛰고 skipped에 종류별 개수를 센다."""
    skipped = skipped if skipped is not None else Counter()
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        kind = b.get("type")
        data = b.get(kind) or {}
        if kind in ("bulleted_list_item", "numbered_list_item"):
            j = i
            while j < len(blocks) and blocks[j].get("type") == kind:
                j += 1
            out.append(_list(blocks[i:j], "ul" if kind == "bulleted_list_item" else "ol", download_image, skipped))
            i = j
            continue
        i += 1
        rich = data.get("rich_text")
        if kind == "paragraph":
            text = rich_text_to_html(rich)
            if text:
                out.append("<p>%s</p>" % text)
        elif kind in ("heading_1", "heading_2", "heading_3"):
            tag = "h3" if kind == "heading_3" else "h2"
            out.append("<%s>%s</%s>" % (tag, rich_text_to_html(rich), tag))
        elif kind == "quote":
            out.append("<blockquote>%s</blockquote>" % rich_text_to_html(rich))
        elif kind == "divider":
            out.append("<hr>")
        elif kind == "image":
            rel = download_image(_file_url(data))
            caption = plain(data.get("caption"))
            alt = html.escape(caption, quote=True)
            figcaption = "<figcaption>%s</figcaption>" % alt if caption else ""
            out.append('<figure><img src="/%s" alt="%s" loading="lazy" decoding="async">%s</figure>' % (rel, alt, figcaption))
        else:
            skipped[kind] += 1
            continue
        if kind in ("paragraph", "quote"):          # 하위 블록은 같은 글 흐름 안에 이어서 둔다
            out.append(_children(b, download_image, skipped))
    return "".join(out)


# ---------------------------------------------------------------- 행

def _prop(page: Mapping, name: str, who: str) -> Mapping:
    props = page.get("properties", {})
    if name not in props:
        raise NotionError("%s: 노션 데이터베이스에 '%s' 칸이 없습니다 (칸 이름이 정확히 같아야 합니다)" % (who, name))
    return props[name]


def _title(page: Mapping) -> str:
    prop = page.get("properties", {}).get("제목") or {}
    return plain(prop.get("title", [])).strip()


def _date(created_time: str) -> str:
    stamp = datetime.datetime.fromisoformat(created_time.replace("Z", "+00:00"))
    return stamp.astimezone(KST).date().isoformat()


def _row_id(page: Mapping) -> str:
    """행 ID의 끝 12자. 앞부분은 같은 시기에 만든 행끼리 똑같아서(예: 3f80820b-1e5d-80…) 구분에 쓸 수 없다."""
    return page["id"].replace("-", "")[-12:]


def row_to_item(page: Mapping, blocks: Sequence[Mapping], download_image: Callable[[str], str],
                skipped: Optional[Counter] = None) -> dict:
    """노션 행 하나와 그 페이지 본문 블록을 post 항목으로 바꾼다. download_image(url)는 사이트 안의 이미지 경로(assets/…)를 돌려준다."""
    row_id = _row_id(page)
    who = _title(page)
    if not who:
        raise NotionError("행 %s: '제목' 칸이 비어 있습니다" % row_id)

    subtitle = plain(_prop(page, "소제목", who).get("rich_text", [])).strip()
    if not subtitle:
        raise NotionError("%s: '소제목' 칸이 비어 있습니다" % who)

    selected = _prop(page, "분류", who).get("select")
    if not selected:
        raise NotionError("%s: '분류' 칸이 비어 있습니다" % who)
    if selected["name"] not in CATEGORY_LABELS:
        raise NotionError("%s: '분류' 칸에 알 수 없는 값 '%s'가 있습니다 (허용: %s)" % (who, selected["name"], ", ".join(CATEGORY_LABELS)))

    body = blocks_to_html(blocks, download_image, skipped)
    if not body.strip():
        raise NotionError("%s: 페이지 본문이 비어 있습니다 (글을 쓰거나 '공개'를 꺼 주세요)" % who)

    item = {"id": "notion-%s" % row_id, "kind": "post", "slug": "r-%s" % row_id, "title": who, "subtitle": subtitle,
            "category": CATEGORY_LABELS[selected["name"]], "date": _date(page["created_time"]), "body": body, "source": SOURCE}
    cover = page.get("cover")                      # 노션 페이지 맨 위 커버 이미지가 대표 이미지
    if cover:
        item["image"] = download_image(_file_url(cover))
    return item


def rows_to_items(pages: Sequence[Mapping], fetch_blocks: Callable[[str], Sequence[Mapping]],
                  download_image: Callable[[str], str], skipped: Optional[Counter] = None) -> list:
    """공개된 행만 골라 본문을 가져와 항목으로 바꾸고, 최신 날짜순(같으면 제목순)으로 정렬한다."""
    published = [p for p in pages if p.get("properties", {}).get("공개", {}).get("checkbox")]
    items = [row_to_item(p, fetch_blocks(p["id"]), download_image, skipped) for p in published]
    seen = set()
    for item in items:
        if item["id"] in seen:
            raise NotionError("행 ID 끝 12자가 겹치는 행이 있습니다(중복): %s" % item["id"])
        seen.add(item["id"])
    return sort_posts(items)
