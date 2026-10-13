import re

import pytest
from PIL import Image

from site_build import render


def text_review(**over):
    item = {"id": "r1", "kind": "text", "goal": ["degree", "license"], "source": "테스트", "featured": True,
            "headline": '"한 줄 <mark>제목</mark>"', "body": "본문 <strong>강조</strong>",
            "person": "김○○ 님 (30대)", "meta": "직장인 / 학사", "badge": "학사 학위"}
    item.update(over)
    return item


@pytest.fixture
def root(tmp_path):
    (tmp_path / "assets" / "proof").mkdir(parents=True)
    Image.new("RGB", (600, 900), "white").save(tmp_path / "assets" / "proof" / "한글 파일.jpg")
    Image.new("RGB", (300, 300), "white").save(tmp_path / "assets" / "p.jpg")
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
    assert render.reviews_extras([], root) == ""
    assert render.reviews_extras([text_review()], root) == ""


def test_filters_show_only_goals_that_exist_in_fixed_order():
    items = [text_review(goal=["transfer"]), text_review(id="r2", goal=["degree"])]
    html = render.reviews_filters(items)
    assert re.findall(r'data-filter="(\w+)"', html) == ["all", "degree", "transfer"]
    assert "대학원" not in html


def test_featured_uses_main_prefix_and_skips_non_featured(root):
    items = [text_review(), text_review(id="r2", featured=False, person="이○○ 님")]
    html = render.reviews_featured(items)
    assert html.count('class="es5-card"') == 1 and "이○○" not in html and "data-cat" not in html


# ---- 팀

def member(**over):
    item = {"id": "t1", "name": "홍길동 담당자", "role": "학위 · 편입 전문 플래너", "photo": "assets/p.jpg",
            "bio": "소개 <strong>강조</strong>", "tags": ["편입", "대학원"]}
    item.update(over)
    return item


def test_team_card_basic_markup_matches_existing_page_structure():
    html = render.team_cards([member()])
    assert "<!-- 홍길동 담당자 -->" in html
    assert 'src="../../assets/p.jpg"' in html and "<strong>강조</strong>" in html
    assert html.count('class="pt-mem-tag"') == 2
    assert "pt-mem-career" not in html and "pt-mem-cases" not in html
    assert render.team_extras([member()]) == ""


def test_team_card_shows_career_and_case_links():
    cases = {"t1": [{"slug": "a-2026", "title": "A대 합격"}, {"slug": "b-2026", "title": "B대 합격"}]}
    html = render.team_cards([member(career=["경력 5년", "사회복지사 2급"])], cases_by_planner=cases)
    assert html.count("<li>") == 2
    assert 'href="/pages/reviews/a-2026/"' in html and "B대 합격" in html
    assert "pt-mem-career" in render.team_extras([member(career=["경력"])])
    assert render.team_extras([member()], cases) != ""


# ---- 캡처·합격 사례

def capture(**over):
    item = {"id": "c1", "kind": "capture", "goal": ["transfer"], "source": "테스트",
            "image": "assets/proof/한글 파일.jpg", "alt": '대화 <캡처> & "인용"', "person": "홍○○ 님", "period": "2026.09"}
    item.update(over)
    return item


def test_capture_card_encodes_path_escapes_alt_and_lazy_loads(root):
    html = render.reviews_grid([capture()], root)
    assert 'src="/assets/proof/%ED%95%9C%EA%B8%80%20%ED%8C%8C%EC%9D%BC.jpg"' in html     # 한글·공백 인코딩
    assert 'alt="대화 &lt;캡처&gt; &amp; &quot;인용&quot;"' in html
    assert 'width="600" height="900"' in html and 'loading="lazy"' in html
    assert "홍○○ 님 · 2026.09" in html and "편입" in html


def test_capture_without_period_shows_only_name(root):
    html = render.reviews_grid([capture(period=None)], root)
    assert "홍○○ 님" in html and "None" not in html


def case(**over):
    item = {"id": "k1", "kind": "case", "goal": ["transfer"], "source": "테스트", "slug": "univ-a-2026",
            "title": "A대 <편입> 합격", "school": "A대학교", "track": "일반편입", "duration": "8개월",
            "profile": {"age": "20대", "background": "전문대 졸업", "credits": "80학점"},
            "plan": [{"label": "1학기", "detail": "전공 18학점"}], "result": "최종 합격",
            "planner": "t1", "seoDescription": "설명"}
    item.update(over)
    return item


def test_case_card_links_to_detail_page_and_escapes(root):
    html = render.reviews_grid([case()], root)
    assert 'href="/pages/reviews/univ-a-2026/"' in html
    assert "A대 &lt;편입&gt; 합격" in html and "A대학교 · 일반편입" in html
    assert "20대 · 전문대 졸업 · 8개월" in html


def test_extras_appear_only_when_needed(root):
    assert "pr-lb" in render.reviews_extras([capture()], root)
    assert "pr-case-badge" in render.reviews_extras([case()], root)


def test_url_path_quotes_unicode_and_spaces():
    assert render.url_path("assets/한 글.jpg") == "/assets/%ED%95%9C%20%EA%B8%80.jpg"
    assert render.url_path("/assets/a.jpg") == "/assets/a.jpg"


# ---- 수치 띠·푸터

def test_stats_strip_formats_numbers_and_shows_basis():
    stats = [{"value": 1200, "suffix": "명+", "label": "누적 수강생", "asOf": "2026-10", "source": "자체 집계"},
             {"value": 4.9, "label": "만족도", "asOf": "2026-10-12", "source": "설문 <120명>"}]
    html = render.stats_strip(stats)
    assert 'data-count="1200">1,200</span><span class="est-s">명+</span>' in html
    assert 'data-count="4.9">4.9</span></p>' in html
    assert "2026.10 기준 · 자체 집계" in html and "2026.10.12 기준 · 설문 &lt;120명&gt;" in html
    assert render.stats_strip([]) == ""


def test_footer_renders_required_and_optional_rows_and_escapes():
    biz = {"company": "에듀 & 솔루션", "ceo": "홍길동", "regno": "000-00-00000", "address": "서울",
           "reports": [{"label": "신고번호", "value": "제1호"}], "phone": "010-0000-0000"}
    html = render.site_footer(biz)
    for text in ("에듀 &amp; 솔루션", "홍길동", "000-00-00000", "신고번호", "제1호", "010-0000-0000", "서울"):
        assert text in html
    assert "이메일" not in html
    assert render.site_footer({}) == ""


def test_footer_omits_ceo_row_when_name_is_not_given():
    html = render.site_footer({"company": "에듀솔루션", "regno": "000-00-00000", "address": "서울"})
    assert "대표자" not in html and "000-00-00000" in html and "에듀솔루션" in html
    assert "<b>대표자</b>" in render.site_footer({"company": "에듀솔루션", "ceo": "홍길동", "regno": "1", "address": "서울"})


def test_stats_note_omits_basis_when_source_is_not_given():
    html = render.stats_strip([{"value": 9000, "suffix": "명+", "label": "누적 수강생", "asOf": "2026-10"}])
    assert '<p class="est-note">2026.10 기준</p>' in html


# ---- 유튜브 채널

def test_member_card_gets_small_youtube_link_only_when_given():
    assert "pt-mem-yt" not in render.team_cards([member()])
    html = render.team_cards([member(youtube="https://www.youtube.com/@Heekyoungsam?a=1&b=2")])
    assert 'href="https://www.youtube.com/@Heekyoungsam?a=1&amp;b=2"' in html
    assert 'target="_blank"' in html and 'rel="noopener noreferrer"' in html and "유튜브 채널" in html


def test_team_channel_block_renders_name_description_and_safe_link():
    html = render.team_channel({"name": "에듀솔루션 <팀> 채널", "url": "https://www.youtube.com/@EDUSOLUTIONN",
                                "description": "소개 문장"})
    assert "에듀솔루션 &lt;팀&gt; 채널" in html and "소개 문장" in html
    assert 'href="https://www.youtube.com/@EDUSOLUTIONN"' in html and 'rel="noopener noreferrer"' in html
    assert "pt-yt-desc" not in render.team_channel({"name": "팀", "url": "https://www.youtube.com/@a"})
    assert render.team_channel({}) == ""


def test_team_extras_includes_youtube_css_when_channels_exist():
    assert render.team_extras([member()]) == ""
    assert "pt-yt-team" in render.team_extras([member()], channel={"name": "팀", "url": "https://www.youtube.com/@a"})
    assert "pt-mem-yt" in render.team_extras([member(youtube="https://www.youtube.com/@a")])
