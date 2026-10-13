import io
import json
import urllib.error

import pytest
from PIL import Image

from site_build import data, notion
from site_build.notion import NotionError
from site_build.site import load_site
from tools import notion_sync


class FakeResponse:
    def __init__(self, payload: bytes):
        self._buf = io.BytesIO(payload)

    def read(self, n=-1):
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def png_bytes(color="white", size=(300, 200)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def rt(text, bold=False):
    return {"plain_text": text, "annotations": {"bold": bold}}


def row(row_id, kind="글 후기", url=None, **over):
    props = {
        "이름": {"type": "title", "title": [rt("김○○ 님")]},
        "종류": {"type": "select", "select": {"name": kind}},
        "분류": {"type": "multi_select", "multi_select": [{"name": "학위 취득"}]},
        "공개": {"type": "checkbox", "checkbox": True},
        "한줄제목": {"type": "rich_text", "rich_text": [rt("제목")]},
        "본문": {"type": "rich_text", "rich_text": [rt("본문")]},
        "소개": {"type": "rich_text", "rich_text": [rt("직장인")]},
        "배지": {"type": "rich_text", "rich_text": [rt("학사")]},
        "이미지": {"type": "files", "files": [{"type": "file", "file": {"url": url}}] if url else []},
    }
    props.update(over)
    return {"id": row_id, "created_time": "2026-10-01T00:00:00.000Z", "properties": props}


# ---- 데이터베이스 조회

def test_query_database_pages_through_results_and_filters_published_rows():
    calls = []
    pages = [{"results": [{"id": "a"}, {"id": "b"}], "has_more": True, "next_cursor": "CUR"},
             {"results": [{"id": "c"}], "has_more": False, "next_cursor": None}]

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        return FakeResponse(json.dumps(pages[len(calls) - 1]).encode("utf-8"))

    rows = notion_sync.query_database("DB123", "secret-token", urlopen=fake_urlopen, sleep=lambda s: None)
    assert [r["id"] for r in rows] == ["a", "b", "c"]
    first, second = calls
    assert first.full_url == "https://api.notion.com/v1/databases/DB123/query"
    assert first.get_header("Authorization") == "Bearer secret-token" and first.get_header("Notion-version") == "2022-06-28"
    body1, body2 = json.loads(first.data), json.loads(second.data)
    assert body1["filter"] == {"property": "공개", "checkbox": {"equals": True}} and body1["page_size"] == 100
    assert "start_cursor" not in body1 and body2["start_cursor"] == "CUR"


def test_transient_errors_are_retried_then_succeed():
    attempts = []

    def flaky(req, timeout=None):
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return FakeResponse(b'{"results": [], "has_more": false}')

    assert notion_sync.query_database("DB", "tok", urlopen=flaky, sleep=lambda s: None) == []
    assert len(attempts) == 3


def test_permanent_errors_fail_without_leaking_the_token():
    def denied(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    with pytest.raises(NotionError) as err:
        notion_sync.query_database("DB", "super-secret-token", urlopen=denied, sleep=lambda s: None)
    assert "401" in str(err.value) and "super-secret-token" not in str(err.value)


def test_giving_up_after_repeated_server_errors():
    def down(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)

    with pytest.raises(NotionError, match="503"):
        notion_sync.query_database("DB", "tok", urlopen=down, sleep=lambda s: None)


# ---- 이미지

def test_image_is_saved_as_small_clean_jpeg_and_not_downloaded_twice(tmp_path):
    fetched = []

    def fetch(url):
        fetched.append(url)
        return png_bytes(size=(2400, 1200))

    resolve = notion_sync.make_image_resolver(tmp_path, fetch)
    rel = resolve("https://s3.example.com/ws/uuid-aaa/chat.png?X-Amz-Signature=one")
    again = resolve("https://s3.example.com/ws/uuid-aaa/chat.png?X-Amz-Signature=two")   # 서명(쿼리)만 다른 같은 파일
    assert rel == again and rel.startswith("assets/proof/notion-") and rel.endswith(".jpg")
    assert len(fetched) == 1
    with Image.open(tmp_path / rel) as im:
        assert im.format == "JPEG" and im.size == (1200, 600) and len(im.getexif()) == 0


def test_different_files_get_different_names(tmp_path):
    resolve = notion_sync.make_image_resolver(tmp_path, lambda url: png_bytes())
    assert resolve("https://s3.example.com/ws/uuid-aaa/a.png?s=1") != resolve("https://s3.example.com/ws/uuid-bbb/a.png?s=1")


def test_non_image_download_is_an_error(tmp_path):
    resolve = notion_sync.make_image_resolver(tmp_path, lambda url: b"<html>not an image</html>")
    with pytest.raises(NotionError, match="이미지"):
        resolve("https://s3.example.com/ws/uuid-aaa/chat.png?s=1")


# ---- 동기화(파일 쓰기)

def test_sync_writes_deterministic_json_and_prunes_unreferenced_notion_images(tmp_path):
    proof = tmp_path / "assets" / "proof"
    proof.mkdir(parents=True)
    (proof / "notion-stale000000.jpg").write_bytes(b"old")        # 더는 쓰이지 않는 노션 이미지 -> 삭제
    (proof / "manual-case.jpg").write_bytes(b"keep")              # 수동으로 올린 이미지 -> 유지
    rows = [row("1a2b3c4d-0000-0000-0000-000000000000"),
            row("9f8e7d6c-0000-0000-0000-000000000000", kind="대화 캡처", url="https://s3.example.com/ws/uuid-aaa/c.png?s=1")]
    summary = notion_sync.sync(tmp_path, rows, lambda url: png_bytes())
    out = (tmp_path / "data" / "reviews.notion.json")
    first = out.read_bytes()
    items = json.loads(first.decode("utf-8"))
    assert [i["id"] for i in items] == ["notion-1a2b3c4d", "notion-9f8e7d6c"] or {i["id"] for i in items} == {"notion-1a2b3c4d", "notion-9f8e7d6c"}
    assert b"\r\n" not in first and first.endswith(b"\n")
    assert not (proof / "notion-stale000000.jpg").exists() and (proof / "manual-case.jpg").exists()
    assert summary == {"items": 2, "images": 1, "removed_images": 1}
    notion_sync.sync(tmp_path, rows, lambda url: png_bytes())
    assert out.read_bytes() == first                              # 같은 입력이면 파일이 그대로(불필요한 커밋 없음)


def test_sync_output_passes_site_validation_and_renders(tmp_path):
    rows = [row("1a2b3c4d-0000-0000-0000-000000000000"),
            row("9f8e7d6c-0000-0000-0000-000000000000", kind="대화 캡처", url="https://s3.example.com/ws/uuid-aaa/c.png?s=1")]
    notion_sync.sync(tmp_path, rows, lambda url: png_bytes())
    tokens, _ = load_site(tmp_path)
    assert "제목" in tokens["reviews_grid"] and "pr-cap" in tokens["reviews_grid"] and "pr-lb" in tokens["reviews_extras"]


def test_sync_with_no_published_rows_writes_empty_list_and_removes_notion_images(tmp_path):
    proof = tmp_path / "assets" / "proof"
    proof.mkdir(parents=True)
    (proof / "notion-aaaaaaaaaaaa.jpg").write_bytes(b"old")
    notion_sync.sync(tmp_path, [], lambda url: png_bytes())
    assert json.loads((tmp_path / "data" / "reviews.notion.json").read_text(encoding="utf-8")) == []
    assert not list(proof.glob("notion-*.jpg"))


def test_phone_number_typed_in_notion_stops_the_sync_validation(tmp_path):
    bad = row("1a2b3c4d-0000-0000-0000-000000000000", 본문={"type": "rich_text", "rich_text": [rt("연락주세요 010-1234-5678")]})
    notion_sync.sync(tmp_path, [bad], lambda url: png_bytes())
    with pytest.raises(data.DataError, match="개인정보"):
        load_site(tmp_path)


def test_main_requires_environment_variables(monkeypatch, capsys):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    assert notion_sync.main([]) == 1
    assert "NOTION_TOKEN" in capsys.readouterr().err


@pytest.mark.parametrize("given", [
    "0123456789abcdef0123456789abcdef",
    "01234567-89ab-cdef-0123-456789abcdef",
    "https://www.notion.so/workspace/0123456789abcdef0123456789abcdef?v=fedcba9876543210fedcba9876543210",
    "  0123456789ABCDEF0123456789ABCDEF  ",
])
def test_database_id_accepts_plain_hyphenated_and_url_forms(given):
    assert notion_sync._database_id(given).lower() == "0123456789abcdef0123456789abcdef"
