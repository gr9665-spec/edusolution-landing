import pytest

from site_build import notion
from site_build.notion import NotionError


def rt(text, bold=False):
    return {"plain_text": text, "annotations": {"bold": bold}}


def page(**props):
    base = {
        "이름": {"type": "title", "title": [rt("김○○ 님 (30대)")]},
        "종류": {"type": "select", "select": {"name": "글 후기"}},
        "분류": {"type": "multi_select", "multi_select": [{"name": "학위 취득"}, {"name": "자격증"}]},
        "공개": {"type": "checkbox", "checkbox": True},
        "한줄제목": {"type": "rich_text", "rich_text": [rt("과제를 "), rt("놓치지 않고", True), rt(" 성적 UP")]},
        "본문": {"type": "rich_text", "rich_text": [rt("첫 줄\n둘째 줄 "), rt("강조", True)]},
        "소개": {"type": "rich_text", "rich_text": [rt("직장인 / 학사")]},
        "배지": {"type": "rich_text", "rich_text": [rt("학사 학위")]},
        "대표": {"type": "checkbox", "checkbox": True},
    }
    base.update(props)
    return {"id": "1a2b3c4d-1111-2222-3333-444455556666", "created_time": "2026-10-01T00:00:00.000Z", "properties": base}


def capture_page(**props):
    base = {
        "이름": {"type": "title", "title": [rt("홍○○ 님")]},
        "종류": {"type": "select", "select": {"name": "대화 캡처"}},
        "분류": {"type": "multi_select", "multi_select": [{"name": "편입"}]},
        "공개": {"type": "checkbox", "checkbox": True},
        "시기": {"type": "rich_text", "rich_text": [rt("2026.09")]},
        "이미지": {"type": "files", "files": [{"name": "a.png", "type": "file", "file": {"url": "https://s3.example.com/x/uuid-1/a.png?sig=1"}}]},
    }
    base.update(props)
    return {"id": "9f8e7d6c-1111-2222-3333-444455556666", "created_time": "2026-10-02T00:00:00.000Z", "properties": base}


IMG = lambda url: "assets/proof/notion-fixed.jpg"   # noqa: E731  (이미지 내려받기는 호출자가 맡는다)


# ---- 서식 변환

def test_rich_text_is_escaped_and_bold_becomes_the_given_tag_and_newline_becomes_br():
    html = notion.rich_text_to_html([rt('<b>"위험"</b> & '), rt("굵게", True), rt("\n끝")], "strong")
    assert html == '&lt;b&gt;&quot;위험&quot;&lt;/b&gt; &amp; <strong>굵게</strong><br>끝'
    assert notion.rich_text_to_html([rt("강조", True)], "mark") == "<mark>강조</mark>"
    assert notion.rich_text_to_html([], "strong") == ""


def test_script_tags_typed_in_notion_cannot_reach_the_site():
    html = notion.rich_text_to_html([rt("<script>alert(1)</script>")], "strong")
    assert "<script" not in html and "&lt;script&gt;" in html


# ---- 글 후기 행

def test_text_review_row_maps_all_fields():
    item = notion.row_to_item(page(), IMG)
    assert item["id"] == "notion-1a2b3c4d" and item["kind"] == "text"
    assert item["goal"] == ["degree", "license"] and item["featured"] is True
    assert item["headline"] == "과제를 <mark>놓치지 않고</mark> 성적 UP"
    assert item["body"] == "첫 줄<br>둘째 줄 <strong>강조</strong>"
    assert item["person"] == "김○○ 님 (30대)" and item["meta"] == "직장인 / 학사" and item["badge"] == "학사 학위"
    assert "Notion" in item["source"]


def test_featured_is_dropped_for_captures_and_defaults_to_false():
    assert notion.row_to_item(page(대표={"type": "checkbox", "checkbox": False}), IMG)["featured"] is False
    item = notion.row_to_item(capture_page(대표={"type": "checkbox", "checkbox": True}), IMG)
    assert "featured" not in item


@pytest.mark.parametrize("key", ["한줄제목", "본문", "소개", "배지"])
def test_text_review_requires_its_text_columns_and_names_the_row(key):
    empty = {"type": "rich_text", "rich_text": []}
    with pytest.raises(NotionError, match=r"김○○.*%s" % key):
        notion.row_to_item(page(**{key: empty}), IMG)


# ---- 캡처 행

def test_capture_row_maps_image_period_and_alt():
    calls = []

    def resolver(url):
        calls.append(url)
        return "assets/proof/notion-9f8e7d6c-abc.jpg"
    item = notion.row_to_item(capture_page(), resolver)
    assert item["kind"] == "capture" and item["goal"] == ["transfer"] and item["period"] == "2026.09"
    assert item["image"] == "assets/proof/notion-9f8e7d6c-abc.jpg" and item["person"] == "홍○○ 님"
    assert calls == ["https://s3.example.com/x/uuid-1/a.png?sig=1"]      # 첫 번째 파일만, 원래 주소 그대로 전달
    assert item["alt"]


def test_capture_without_image_is_an_error_that_names_the_row():
    with pytest.raises(NotionError, match=r"홍○○.*이미지"):
        notion.row_to_item(capture_page(이미지={"type": "files", "files": []}), IMG)


def test_external_file_urls_are_supported_too():
    files = {"type": "files", "files": [{"name": "b.png", "type": "external", "external": {"url": "https://img.example.com/b.png"}}]}
    seen = []
    notion.row_to_item(capture_page(이미지=files), lambda u: seen.append(u) or "assets/proof/x.jpg")
    assert seen == ["https://img.example.com/b.png"]


# ---- 공통 검사

@pytest.mark.parametrize("bad", [{"type": "select", "select": None}, {"type": "select", "select": {"name": "동영상"}}])
def test_unknown_or_missing_kind_is_an_error(bad):
    with pytest.raises(NotionError, match="종류"):
        notion.row_to_item(page(종류=bad), IMG)


def test_missing_or_unknown_category_and_missing_name_are_errors():
    with pytest.raises(NotionError, match="분류"):
        notion.row_to_item(page(분류={"type": "multi_select", "multi_select": []}), IMG)
    with pytest.raises(NotionError, match="분류.*동영상"):
        notion.row_to_item(page(분류={"type": "multi_select", "multi_select": [{"name": "동영상"}]}), IMG)
    with pytest.raises(NotionError, match="이름"):
        notion.row_to_item(page(이름={"type": "title", "title": []}), IMG)


def test_missing_column_in_the_database_is_reported_by_column_name():
    p = page()
    del p["properties"]["본문"]
    with pytest.raises(NotionError, match="본문"):
        notion.row_to_item(p, IMG)


# ---- 여러 행

def test_rows_are_sorted_by_order_then_newest_first_and_unpublished_rows_are_skipped():
    a = page(순서={"type": "number", "number": 2})
    b = dict(page(순서={"type": "number", "number": 1}), id="bbbbbbbb-1111-2222-3333-444455556666")
    c = dict(page(), id="cccccccc-1111-2222-3333-444455556666", created_time="2026-10-05T00:00:00.000Z")
    d = dict(page(), id="dddddddd-1111-2222-3333-444455556666", created_time="2026-10-09T00:00:00.000Z")
    hidden = dict(page(공개={"type": "checkbox", "checkbox": False}), id="eeeeeeee-1111-2222-3333-444455556666")
    items = notion.rows_to_items([a, c, hidden, d, b], IMG)
    assert [i["id"] for i in items] == ["notion-bbbbbbbb", "notion-1a2b3c4d", "notion-dddddddd", "notion-cccccccc"]


def test_duplicate_row_prefixes_are_rejected():
    twin = dict(page(), id="1a2b3c4d-9999-9999-9999-999999999999")
    with pytest.raises(NotionError, match="중복"):
        notion.rows_to_items([page(), twin], IMG)
