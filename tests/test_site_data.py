import json
from pathlib import Path

import pytest

from site_build.data import DataError
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def post(**over):
    item = {"id": "r01", "kind": "post", "slug": "r01", "title": "수동 후기", "subtitle": "소제목", "category": "degree",
            "body": "<p>본문</p>", "source": "시험"}
    item.update(over)
    return item


def test_load_site_reads_data_from_an_alternate_folder(tmp_path):
    write_json(tmp_path / "data/stats.json", [{"value": 5, "label": "시험 수치", "asOf": "2026-10"}])
    tokens, extra = load_site(ROOT, data_root=tmp_path)
    assert "시험 수치" in tokens["stats_strip"]
    assert tokens["site_footer"] == ""          # 그 폴더에 business.json이 없으면 푸터도 없다
    assert tokens["reviews_grid"] == "" and tokens["reviews_marquee"] == "" and extra == []


def test_load_site_merges_sources_sorts_newest_first_and_makes_a_page_per_post(tmp_path):
    write_json(tmp_path / "data/reviews.json", [post(date="2026-09-01")])
    write_json(tmp_path / "data/reviews.notion.json", [post(id="notion-aaaa1111", slug="r-aaaa1111", title="노션 후기", date="2026-10-01")])
    tokens, extra = load_site(ROOT, data_root=tmp_path)
    grid = tokens["reviews_grid"]
    assert grid.index("노션 후기") < grid.index("수동 후기")                  # 날짜가 최신인 것이 먼저
    assert [p.url_path for p in extra] == ["/pages/reviews/r-aaaa1111/", "/pages/reviews/r01/"]


def test_load_site_rejects_duplicate_ids_across_sources(tmp_path):
    write_json(tmp_path / "data/reviews.json", [post()])
    write_json(tmp_path / "data/reviews.notion.json", [post(slug="other", title="겹치는 id")])
    with pytest.raises(DataError, match="중복"):
        load_site(ROOT, data_root=tmp_path)
