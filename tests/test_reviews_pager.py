from pathlib import Path

from site_build.core import build_all
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent


def built_reviews_page(tmp_path):
    tokens, extra = load_site(ROOT)
    build_all(ROOT, tmp_path, tokens, extra)
    return (tmp_path / "pages/reviews/index.html").read_text(encoding="utf-8")


def test_reviews_list_has_a_pager_slot_after_the_grid(tmp_path):
    page = built_reviews_page(tmp_path)
    assert page.index('id="pr-grid"') < page.index('id="pr-pager"')
    assert 'aria-label="후기 페이지"' in page


def test_pager_script_shows_two_rows_per_page_and_remembers_the_page(tmp_path):
    page = built_reviews_page(tmp_path)
    assert "gridTemplateColumns" in page and "* 2" in page          # 한 줄 카드 수(화면 폭에 따라 달라짐) x 2줄
    assert "pr-off" in page and ".pr-card.pr-off{display:none;}" in page
    assert "history.replaceState" in page and "?p=" in page           # 후기를 읽고 뒤로 와도 보던 페이지 유지


def test_every_review_link_stays_in_the_html_even_when_paged(tmp_path):
    page = built_reviews_page(tmp_path)
    tokens, _ = load_site(ROOT)
    assert page.count('class="pr-card pr-post"') == tokens["reviews_grid"].count('class="pr-card pr-post"') > 0
