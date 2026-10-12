import json

import pytest

from site_build import data
from site_build.data import DataError


def text_review(**over):
    item = {"id": "r1", "kind": "text", "goal": ["degree"], "source": "테스트",
            "headline": "제목", "body": "본문", "person": "김○○ 님 (30대)", "meta": "직장인", "badge": "학사"}
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


# ---- 후기

def test_valid_text_review_passes(root):
    data.validate_reviews([text_review()], root)


@pytest.mark.parametrize("key", ["headline", "body", "person", "meta", "badge", "source", "goal"])
def test_missing_required_field_names_the_item_and_field(root, key):
    item = text_review()
    del item[key]
    with pytest.raises(DataError, match=r"r1.*%s" % key):
        data.validate_reviews([item], root)


def test_duplicate_id_and_unknown_goal_and_unknown_kind(root):
    with pytest.raises(DataError, match="중복"):
        data.validate_reviews([text_review(), text_review()], root)
    with pytest.raises(DataError, match="goal"):
        data.validate_reviews([text_review(goal=["nope"])], root)
    with pytest.raises(DataError, match="kind"):
        data.validate_reviews([text_review(kind="video")], root)


def test_featured_only_for_text_reviews(root):
    data.validate_reviews([text_review(featured=True)], root)
