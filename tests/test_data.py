import json

import pytest

from site_build import data
from site_build.data import DataError


def post(**over):
    item = {"id": "r1", "kind": "post", "slug": "r1", "title": "제목", "subtitle": "소제목", "category": "degree",
            "body": "<p>본문 <strong>강조</strong></p>", "source": "테스트"}
    item.update(over)
    return item


@pytest.fixture
def root(tmp_path):
    (tmp_path / "assets").mkdir()
    for name in ("p.jpg", "cap.jpg", "proof.jpg"):
        (tmp_path / "assets" / name).write_bytes(b"x")
    return tmp_path


# ---- 읽기

def test_load_returns_default_when_file_missing(tmp_path):
    assert data.load(tmp_path, "reviews.json", []) == []


def test_load_accepts_utf8_bom_and_korean(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"a": "한글"}, ensure_ascii=False).encode("utf-8"))
    assert data.load(tmp_path, "x.json", None) == {"a": "한글"}


def test_load_reports_broken_json_with_file_name(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.json").write_text("{ 깨진 json", encoding="utf-8")
    with pytest.raises(DataError, match="x.json"):
        data.load(tmp_path, "x.json", None)


# ---- 후기(post)

def test_valid_post_passes_with_and_without_optional_fields(root):
    data.validate_reviews([post()], root)
    data.validate_reviews([post(id="r2", slug="r-2", image="assets/cap.jpg", date="2026-10-13")], root)


@pytest.mark.parametrize("key", ["title", "subtitle", "category", "body", "source", "slug"])
def test_missing_required_field_names_the_item_and_field(root, key):
    item = post()
    del item[key]
    with pytest.raises(DataError, match=r"r1.*%s" % key):
        data.validate_reviews([item], root)


def test_duplicate_id_unknown_category_and_unknown_kind(root):
    with pytest.raises(DataError, match="중복"):
        data.validate_reviews([post(), post(slug="other")], root)
    with pytest.raises(DataError, match="category"):
        data.validate_reviews([post(category="nope")], root)
    with pytest.raises(DataError, match="kind"):
        data.validate_reviews([post(kind="text")], root)


@pytest.mark.parametrize("slug", ["Univ-A", "univ a", "대학교", "a_b", "-a", "a--b", "index.html"])
def test_bad_slug_is_rejected(root, slug):
    with pytest.raises(DataError, match="slug"):
        data.validate_reviews([post(slug=slug)], root)


def test_duplicate_slug_is_rejected(root):
    with pytest.raises(DataError, match="slug.*중복"):
        data.validate_reviews([post(), post(id="r2")], root)


@pytest.mark.parametrize("bad", ["2026-13-01", "2026-10-32", "2026.10.13", "어제", "2026-10-13T00:00"])
def test_date_must_be_a_real_iso_date(root, bad):
    with pytest.raises(DataError, match="date"):
        data.validate_reviews([post(date=bad)], root)


def test_image_must_exist(root):
    with pytest.raises(DataError, match="파일이 없습니다"):
        data.validate_reviews([post(image="assets/none.jpg")], root)


@pytest.mark.parametrize("html", [
    "<p>일반 <strong>본문</strong> <em>기울임</em><br></p><h2>a</h2><h3>b</h3><ul><li>x</li></ul><ol><li>y</li></ol>"
    "<blockquote>q</blockquote><hr>",
    '<p><a href="https://example.com/a?b=1" target="_blank" rel="noopener noreferrer">링크</a></p>',
    '<figure><img src="/assets/cap.jpg" alt="설명"><figcaption>캡션</figcaption></figure>',
])
def test_body_accepts_the_allowed_tags(root, html):
    data.validate_reviews([post(body=html)], root)


@pytest.mark.parametrize("html", [
    "<script>alert(1)</script>",
    "<p onclick=\"x()\">클릭</p>",
    '<a href="javascript:alert(1)">링크</a>',
    '<img src="https://evil.example.com/x.jpg" alt="x">',
    "<iframe src=\"https://example.com\"></iframe>",
    '<p style="color:red">x</p>',
])
def test_body_rejects_unsafe_tags_attributes_and_urls(root, html):
    with pytest.raises(DataError, match="body"):
        data.validate_reviews([post(body=html)], root)


# ---- 팀

def team_member(**over):
    item = {"id": "t1", "name": "홍길동 담당자", "role": "학위 · 편입 전문 플래너", "photo": "assets/p.jpg",
            "bio": "소개", "tags": ["편입"]}
    item.update(over)
    return item


def test_team_valid_returns_ids_and_checks_photo(root):
    assert data.validate_team([team_member()], root) == {"t1"}
    with pytest.raises(DataError, match="photo"):
        data.validate_team([team_member(photo="assets/none.jpg")], root)
    with pytest.raises(DataError, match="career"):
        data.validate_team([team_member(career=["ok", ""])], root)
    with pytest.raises(DataError, match="중복"):
        data.validate_team([team_member(), team_member()], root)


# ---- 수치

def stat(**over):
    item = {"value": 1200, "label": "누적 수강생", "asOf": "2026-10", "source": "자체 집계"}
    item.update(over)
    return item


def test_stats_require_value_label_and_as_of(root):
    data.validate_stats([stat(), stat(asOf="2026-10-12", value=4.9)])
    for key in ("asOf", "label", "value"):
        item = stat()
        del item[key]
        with pytest.raises(DataError, match=key):
            data.validate_stats([item])
    with pytest.raises(DataError, match="asOf"):
        data.validate_stats([stat(asOf="올해")])
    with pytest.raises(DataError, match="value"):
        data.validate_stats([stat(value="천이백")])
    with pytest.raises(DataError, match="value"):
        data.validate_stats([stat(value=True)])
    with pytest.raises(DataError, match="최대 6개"):
        data.validate_stats([stat() for _ in range(7)])


# ---- 사업자 정보

def test_business_optional_but_checked_when_present():
    data.validate_business({})
    data.validate_business({"company": "에듀", "ceo": "홍", "regno": "000-00-00000", "address": "서울"})
    with pytest.raises(DataError, match="regno"):
        data.validate_business({"company": "에듀", "ceo": "홍", "address": "서울"})
    with pytest.raises(DataError, match="label"):
        data.validate_business({"company": "에듀", "ceo": "홍", "regno": "1", "address": "서울", "reports": [{"value": "x"}]})


# ---- 안전 검사 (공개 저장소에 올라가는 데이터)

@pytest.mark.parametrize("bad", ["raw-proof/a.jpg", "/assets/cap.jpg", "../r/assets/cap.jpg",
                                 "assets/../raw-proof/a.jpg", r"assets\cap.jpg", "C:/x/cap.jpg"])
def test_image_paths_must_stay_inside_assets(root, bad):
    (root / "raw-proof").mkdir()
    (root / "raw-proof" / "a.jpg").write_bytes(b"x")
    with pytest.raises(DataError, match="assets/ 폴더"):
        data.validate_reviews([post(image=bad)], root)
    with pytest.raises(DataError, match="assets/ 폴더"):
        data.validate_team([team_member(photo=bad)], root)


@pytest.mark.parametrize("field,value", [
    ("source", "카톡 김민수 님 010-1234-5678"),
    ("subtitle", "연락처 01012345678"),
    ("body", "<p>문의는 hong@example.com 으로</p>"),
    ("title", "김○○ 010 1234 5678"),
])
def test_reviews_reject_phone_numbers_and_emails(root, field, value):
    with pytest.raises(DataError, match="개인정보"):
        data.validate_reviews([post(**{field: value})], root)


def test_ordinary_numbers_are_not_mistaken_for_pii(root):
    ok = post(body="<p>106학점 중 전공 60학점, 2026.09 기준 8개월, 80~140학점</p>", source="2026-10-12 수강생 동의")
    data.validate_reviews([ok], root)


def test_business_ceo_name_is_optional():
    data.validate_business({"company": "에듀솔루션", "regno": "000-00-00000", "address": "서울"})


def test_stats_source_is_optional(root):
    item = stat()
    del item["source"]
    data.validate_stats([item])


# ---- 유튜브 채널

GOOD_YT = "https://www.youtube.com/@EDUSOLUTIONN"


@pytest.mark.parametrize("bad", ["http://www.youtube.com/@a", "https://evil.example.com/@a", "javascript:alert(1)",
                                 "youtube.com/@a", "https://www.youtube.com.evil.com/@a", "https://www.youtube.com/"])
def test_youtube_url_must_be_an_https_youtube_address(root, bad):
    with pytest.raises(DataError, match="youtube"):
        data.validate_team([team_member(youtube=bad)], root)
    with pytest.raises(DataError, match="youtube"):
        data.validate_youtube({"name": "팀 채널", "url": bad})


def test_team_member_and_team_channel_accept_good_youtube_urls(root):
    data.validate_team([team_member(youtube=GOOD_YT)], root)
    data.validate_team([team_member(youtube="https://www.youtube.com/@%ED%95%99%EC%A0%90")], root)
    data.validate_youtube({})
    data.validate_youtube({"name": "팀 채널", "url": GOOD_YT})


def test_team_channel_requires_name_and_url():
    for key in ("name", "url"):
        item = {"name": "팀 채널", "url": GOOD_YT}
        del item[key]
        with pytest.raises(DataError, match=key):
            data.validate_youtube(item)
