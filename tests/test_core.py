from pathlib import Path

from site_build.core import ExtraPage, Inline, build_all
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent


def page(slug):
    return ExtraPage(rel_dir="pages/reviews/%s" % slug, title="t", desc="d",
                     url_path="/pages/reviews/%s/" % slug, parts=[Inline("<p>x</p>")])


def test_case_page_removed_from_data_is_not_left_published(tmp_path):
    tokens, _ = load_site(ROOT)
    build_all(ROOT, tmp_path, tokens, [page("a-2026"), page("b-2026")])
    assert (tmp_path / "pages/reviews/a-2026/index.html").exists()
    build_all(ROOT, tmp_path, tokens, [page("b-2026")])
    assert not (tmp_path / "pages/reviews/a-2026").exists()           # 삭제한 사례는 공개에서도 사라져야 한다
    assert (tmp_path / "pages/reviews/b-2026/index.html").exists()
    assert (tmp_path / "pages/reviews/index.html").exists()           # 후기 목록 페이지는 그대로


def test_stale_cleanup_leaves_unrelated_folders_alone(tmp_path):
    tokens, _ = load_site(ROOT)
    keep = tmp_path / "pages/reviews/not-a-case"
    keep.mkdir(parents=True)
    (keep / "notes.txt").write_text("keep", encoding="utf-8")        # index.html이 없는 폴더는 건드리지 않는다
    build_all(ROOT, tmp_path, tokens, [])
    assert (keep / "notes.txt").exists()
