from collections import Counter

import pytest

from site_build import notion
from site_build.notion import NotionError


def rt(text, bold=False, italic=False, href=None):
    return {"plain_text": text, "href": href, "annotations": {"bold": bold, "italic": italic}}


def block(kind, text="", **extra):
    body = {"rich_text": [rt(text)] if text else []}
    body.update(extra)
    return {"type": kind, kind: body}


def page(**props):
    base = {
        "제목": {"type": "title", "title": [rt("학사 학위를 따기까지")]},
        "소제목": {"type": "rich_text", "rich_text": [rt("직장인 / 학사 학위")]},
        "분류": {"type": "select", "select": {"name": "학위 취득"}},
        "공개": {"type": "checkbox", "checkbox": True},
    }
    base.update(props)
    return {"id": "11111111-1111-2222-3333-1a2b3c4d5e6f", "created_time": "2026-10-01T03:00:00.000Z", "properties": base}


BODY = [block("paragraph", "본문입니다")]
IMG = lambda url: "assets/proof/notion-fixed.jpg"   # noqa: E731  (이미지 내려받기는 호출자가 맡는다)


# ---- 서식 변환

def test_rich_text_is_escaped_and_formats_map_to_safe_tags_and_newline_becomes_br():
    html = notion.rich_text_to_html([rt('<b>"위험"</b> & '), rt("굵게", bold=True), rt("기울임", italic=True), rt("\n끝")])
    assert html == '&lt;b&gt;&quot;위험&quot;&lt;/b&gt; &amp; <strong>굵게</strong><em>기울임</em><br>끝'
    assert notion.rich_text_to_html([rt("굵고 기울임", bold=True, italic=True)]) == "<strong><em>굵고 기울임</em></strong>"
    assert notion.rich_text_to_html([]) == ""


def test_links_are_kept_only_for_http_and_https_and_get_safe_attributes():
    html = notion.rich_text_to_html([rt("공식", href="https://example.com/a?x=1&y=2")])
    assert html == '<a href="https://example.com/a?x=1&amp;y=2" target="_blank" rel="noopener noreferrer">공식</a>'
    for bad in ("javascript:alert(1)", "mailto:a@b.com", "/relative", "data:text/html,x"):
        assert notion.rich_text_to_html([rt("링크", href=bad)]) == "링크"


def test_script_tags_typed_in_notion_cannot_reach_the_site():
    html = notion.rich_text_to_html([rt("<script>alert(1)</script>")])
    assert "<script" not in html and "&lt;script&gt;" in html


# ---- 블록 변환

def test_basic_blocks_become_html():
    blocks = [block("heading_1", "큰 제목"), block("heading_2", "중간"), block("heading_3", "작은"),
              block("paragraph", "문단"), block("quote", "인용"), {"type": "divider", "divider": {}}]
    html = notion.blocks_to_html(blocks, IMG)
    assert html == "<h2>큰 제목</h2><h2>중간</h2><h3>작은</h3><p>문단</p><blockquote>인용</blockquote><hr>"


def test_consecutive_list_items_are_grouped_and_nested_children_stay_inside():
    blocks = [block("bulleted_list_item", "가"), block("bulleted_list_item", "나"),
              block("numbered_list_item", "하나"), block("numbered_list_item", "둘"),
              block("paragraph", "끝"), block("bulleted_list_item", "다")]
    blocks[1]["children"] = [block("bulleted_list_item", "나-1")]
    html = notion.blocks_to_html(blocks, IMG)
    assert html == ("<ul><li>가</li><li>나<ul><li>나-1</li></ul></li></ul><ol><li>하나</li><li>둘</li></ol>"
                    "<p>끝</p><ul><li>다</li></ul>")


def test_empty_paragraphs_are_skipped():
    assert notion.blocks_to_html([block("paragraph"), block("paragraph", "내용")], IMG) == "<p>내용</p>"


def test_image_block_is_downloaded_and_caption_becomes_alt_and_figcaption():
    calls = []

    def resolver(url):
        calls.append(url)
        return "assets/proof/notion-aaaa.jpg"
    blocks = [{"type": "image", "image": {"type": "file", "file": {"url": "https://s3.example.com/x.png?sig=1"},
                                           "caption": [rt('캡션 "하나"')]}}]
    html = notion.blocks_to_html(blocks, resolver)
    assert html == ('<figure><img src="/assets/proof/notion-aaaa.jpg" alt="캡션 &quot;하나&quot;" loading="lazy" decoding="async">'
                    '<figcaption>캡션 &quot;하나&quot;</figcaption></figure>')
    assert calls == ["https://s3.example.com/x.png?sig=1"]
    external = [{"type": "image", "image": {"type": "external", "external": {"url": "https://img.example.com/b.png"}, "caption": []}}]
    assert notion.blocks_to_html(external, resolver).startswith('<figure><img src="/assets/proof/notion-aaaa.jpg" alt=""')
    assert "figcaption" not in notion.blocks_to_html(external, resolver)


def test_unsupported_blocks_are_ignored_but_counted():
    skipped = Counter()
    blocks = [block("paragraph", "남는 문단"), {"type": "code", "code": {"rich_text": [rt("x = 1")]}},
              {"type": "callout", "callout": {"rich_text": [rt("강조")]}}, {"type": "code", "code": {"rich_text": []}}]
    assert notion.blocks_to_html(blocks, IMG, skipped) == "<p>남는 문단</p>"
    assert skipped == {"code": 2, "callout": 1}


# ---- 행

def test_row_maps_all_fields():
    item = notion.row_to_item(page(), BODY, IMG)
    assert item == {"id": "notion-1a2b3c4d5e6f", "kind": "post", "slug": "r-1a2b3c4d5e6f", "title": "학사 학위를 따기까지",
                    "subtitle": "직장인 / 학사 학위", "category": "degree", "date": "2026-10-01",
                    "body": "<p>본문입니다</p>", "source": "Notion 후기 데이터베이스"}


def test_date_uses_korean_time():
    # 2026-10-12 16:00 UTC == 2026-10-13 01:00 KST
    assert notion.row_to_item(dict(page(), created_time="2026-10-12T16:00:00.000Z"), BODY, IMG)["date"] == "2026-10-13"


def test_page_cover_is_the_representative_image_and_optional():
    cover = {"type": "file", "file": {"url": "https://s3.example.com/x/a.png?sig=1"}}
    seen = []
    item = notion.row_to_item(dict(page(), cover=cover), BODY, lambda u: seen.append(u) or "assets/proof/notion-c.jpg")
    assert item["image"] == "assets/proof/notion-c.jpg" and seen == ["https://s3.example.com/x/a.png?sig=1"]
    assert "image" not in notion.row_to_item(page(), BODY, IMG)                       # 커버가 없으면 기본 이미지
    assert "image" not in notion.row_to_item(dict(page(), cover=None), BODY, IMG)
    external = {"type": "external", "external": {"url": "https://img.example.com/b.png"}}
    seen.clear()
    notion.row_to_item(dict(page(), cover=external), BODY, lambda u: seen.append(u) or "assets/proof/x.jpg")
    assert seen == ["https://img.example.com/b.png"]


def test_the_old_cover_image_column_is_ignored_and_not_required():
    files = {"type": "files", "files": [{"name": "a.png", "type": "file", "file": {"url": "https://s3.example.com/x/a.png?sig=1"}}]}
    assert "image" not in notion.row_to_item(page(대표이미지=files), BODY, IMG)        # 커버만 본다
    p = page()
    p["properties"].pop("대표이미지", None)
    assert "image" not in notion.row_to_item(p, BODY, IMG)


@pytest.mark.parametrize("key", ["제목", "소제목"])
def test_title_and_subtitle_are_required_and_error_names_the_row(key):
    empty = {"type": "title", "title": []} if key == "제목" else {"type": "rich_text", "rich_text": []}
    with pytest.raises(NotionError, match=key):
        notion.row_to_item(page(**{key: empty}), BODY, IMG)


def test_empty_page_body_is_an_error_that_names_the_row():
    with pytest.raises(NotionError, match=r"학사 학위를 따기까지.*본문"):
        notion.row_to_item(page(), [], IMG)
    with pytest.raises(NotionError, match="본문"):
        notion.row_to_item(page(), [{"type": "code", "code": {"rich_text": []}}], IMG)


def test_missing_or_unknown_category_is_an_error():
    with pytest.raises(NotionError, match="분류"):
        notion.row_to_item(page(분류={"type": "select", "select": None}), BODY, IMG)
    with pytest.raises(NotionError, match="분류.*동영상"):
        notion.row_to_item(page(분류={"type": "select", "select": {"name": "동영상"}}), BODY, IMG)


def test_missing_column_in_the_database_is_reported_by_column_name():
    p = page()
    del p["properties"]["소제목"]
    with pytest.raises(NotionError, match="소제목"):
        notion.row_to_item(p, BODY, IMG)


# ---- 여러 행

def test_rows_are_sorted_newest_first_then_by_title_and_unpublished_rows_are_skipped():
    older = dict(page(), id="11111111-1111-2222-3333-aaaaaaaaaaaa", created_time="2026-10-01T03:00:00.000Z")
    newest = dict(page(), id="11111111-1111-2222-3333-bbbbbbbbbbbb", created_time="2026-10-09T03:00:00.000Z")
    same_day = dict(page(제목={"type": "title", "title": [rt("가나다")]}), id="11111111-1111-2222-3333-cccccccccccc",
                    created_time="2026-10-01T05:00:00.000Z")
    hidden = dict(page(공개={"type": "checkbox", "checkbox": False}), id="11111111-1111-2222-3333-dddddddddddd")
    fetched = []

    def fetch_blocks(page_id):
        fetched.append(page_id)
        return BODY

    items = notion.rows_to_items([older, hidden, newest, same_day], fetch_blocks, IMG)
    assert [i["id"] for i in items] == ["notion-bbbbbbbbbbbb", "notion-cccccccccccc", "notion-aaaaaaaaaaaa"]
    assert "11111111-1111-2222-3333-dddddddddddd" not in fetched          # 비공개 행은 본문도 가져오지 않는다


def test_duplicate_row_prefixes_are_rejected():
    twin = dict(page(), id="99999999-9999-9999-9999-1a2b3c4d5e6f")
    with pytest.raises(NotionError, match="중복"):
        notion.rows_to_items([page(), twin], lambda page_id: BODY, IMG)


def test_image_block_without_a_usable_url_is_a_notion_error_not_a_crash():
    with pytest.raises(NotionError, match="이미지"):
        notion.blocks_to_html([{"type": "image", "image": {"type": "file", "caption": []}}], IMG)
    with pytest.raises(NotionError, match="이미지"):
        notion.blocks_to_html([{"type": "image", "image": {"type": "unknown"}}], IMG)


def test_link_with_trailing_newline_is_not_a_link():
    assert notion.rich_text_to_html([rt("x", href="https://example.com/\n")]) == "x"


def test_ids_come_from_the_end_of_the_page_id_because_the_start_is_shared_by_rows_created_around_the_same_time():
    first = dict(page(), id="3f80820b-1e5d-80c9-a333-d9b69dfcaa04")
    second = dict(page(), id="3f80820b-1e5d-80c9-b444-0123456789ab")      # 앞 8자(와 그 뒤)가 같은 새 행
    items = notion.rows_to_items([first, second], lambda page_id: BODY, IMG)
    assert {i["id"] for i in items} == {"notion-d9b69dfcaa04", "notion-0123456789ab"}
    assert {i["slug"] for i in items} == {"r-d9b69dfcaa04", "r-0123456789ab"}
