import re

import pytest

from site_build import render


def text_review(**over):
    item = {"id": "r1", "kind": "text", "goal": ["degree", "license"], "source": "테스트", "featured": True,
            "headline": '"한 줄 <mark>제목</mark>"', "body": "본문 <strong>강조</strong>",
            "person": "김○○ 님 (30대)", "meta": "직장인 / 학사", "badge": "학사 학위"}
    item.update(over)
    return item


@pytest.fixture
def root(tmp_path):
    return tmp_path


# ---- 글 후기

def test_text_card_keeps_authored_html_but_escapes_plain_fields(root):
    html = render.reviews_grid([text_review(person='김"○○ <님> & (30대)', meta="a<b", badge="x&y")], root)
    assert "<mark>제목</mark>" in html and "<strong>강조</strong>" in html      # 제목·본문은 HTML 허용
    assert "김&quot;○○ &lt;님&gt; &amp; (30대)" in html                         # 나머지는 이스케이프
    assert "a&lt;b" in html and "x&amp;y" in html
    assert html.count('class="pr-star"') == 5


def test_text_card_joins_goals_and_uses_first_char_as_avatar(root):
    html = render.reviews_grid([text_review()], root)
    assert 'data-cat="degree license"' in html
    assert '<div class="pr-av">김</div>' in html


def test_empty_data_renders_nothing(root):
    assert render.reviews_grid([], root) == ""
    assert render.reviews_featured([]) == ""


def test_filters_show_only_goals_that_exist_in_fixed_order():
    items = [text_review(goal=["transfer"]), text_review(id="r2", goal=["degree"])]
    html = render.reviews_filters(items)
    assert re.findall(r'data-filter="(\w+)"', html) == ["all", "degree", "transfer"]
    assert "대학원" not in html


def test_featured_uses_main_prefix_and_skips_non_featured(root):
    items = [text_review(), text_review(id="r2", featured=False, person="이○○ 님")]
    html = render.reviews_featured(items)
    assert html.count('class="es5-card"') == 1 and "이○○" not in html and "data-cat" not in html
