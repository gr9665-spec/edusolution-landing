import json
from pathlib import Path

from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_load_site_reads_data_from_an_alternate_folder(tmp_path):
    write_json(tmp_path / "data/stats.json", [{"value": 5, "label": "시험 수치", "asOf": "2026-10"}])
    tokens, _ = load_site(ROOT, data_root=tmp_path)
    assert "시험 수치" in tokens["stats_strip"]
    assert tokens["site_footer"] == ""          # 그 폴더에 business.json이 없으면 푸터도 없다
    assert tokens["reviews_grid"] == ""         # 후기도 비어 있다(운영 데이터가 섞이지 않는다)


def test_load_site_merges_manual_and_notion_reviews_and_rejects_duplicate_ids(tmp_path):
    base = {"kind": "text", "goal": ["degree"], "source": "시험", "headline": "제목", "body": "본문",
            "person": "김○○ 님", "meta": "직장인", "badge": "학사"}
    write_json(tmp_path / "data/reviews.json", [dict(base, id="r01", headline="수동 후기")])
    write_json(tmp_path / "data/reviews.notion.json", [dict(base, id="notion-aaaa1111", headline="노션 후기")])
    tokens, _ = load_site(ROOT, data_root=tmp_path)
    grid = tokens["reviews_grid"]
    assert "수동 후기" in grid and "노션 후기" in grid
    assert grid.index("수동 후기") < grid.index("노션 후기")      # 수동 후기가 먼저, 노션 후기가 뒤

    write_json(tmp_path / "data/reviews.notion.json", [dict(base, id="r01", headline="겹치는 id")])
    import pytest
    from site_build.data import DataError
    with pytest.raises(DataError, match="중복"):
        load_site(ROOT, data_root=tmp_path)
