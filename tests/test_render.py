import re

import pytest
from PIL import Image

from site_build import render


def post(**over):
    item = {"id": "r1", "kind": "post", "slug": "r1", "title": "첫 번째 후기", "subtitle": "직장인 / 학사 학위",
            "category": "degree", "body": "<p>본문</p>", "source": "테스트", "date": "2026-10-13",
            "image": "assets/proof/한글 파일.jpg"}
    item.update(over)
    return item


def posts(n):
    return [post(id="r%d" % i, slug="r%d" % i, title="후기 %d" % i, date="2026-10-%02d" % (i + 1)) for i in range(n)]


# ---- 목록 카드

def test_list_card_links_to_detail_and_shows_image_title_subtitle_category_date():
    html = render.reviews_grid([post()])
    assert 'class="pr-card pr-post"' in html and 'href="/pages/reviews/r1/"' in html
    assert 'data-cat="degree"' in html
    assert 'src="/assets/proof/%ED%95%9C%EA%B8%80%20%ED%8C%8C%EC%9D%BC.jpg"' in html     # 한글·공백 인코딩
    assert 'alt="첫 번째 후기"' in html and 'loading="lazy"' in html
    assert "첫 번째 후기" in html and "직장인 / 학사 학위" in html
    assert "학위 취득" in html and '<time datetime="2026-10-13">2026.10.13</time>' in html


def test_list_card_uses_default_image_and_hides_missing_date():
    html = render.reviews_grid([post(image=None, date=None)])
    assert 'src="/assets/review-default.jpg"' in html
    assert "<time" not in html and "None" not in html


def test_list_card_escapes_plain_fields():
    html = render.reviews_grid([post(title='a<b>"&', subtitle="x<y")])
    assert "a&lt;b&gt;&quot;&amp;" in html and "x&lt;y" in html and "<b>" not in html


def test_empty_data_renders_nothing():
    assert render.reviews_grid([]) == ""
    assert render.reviews_marquee([]) == ""


def test_posts_are_sorted_newest_first_then_by_title_and_undated_last():
    items = [post(id="a", slug="a", title="나", date="2026-10-01"), post(id="b", slug="b", title="가", date="2026-10-01"),
             post(id="c", slug="c", title="다", date=None), post(id="d", slug="d", title="라", date="2026-10-05")]
    assert [i["id"] for i in render.sort_posts(items)] == ["d", "b", "a", "c"]


def test_sort_is_stable_for_equal_date_and_title_by_id():
    a, b = post(id="b-id", slug="b-id", date="2026-10-01"), post(id="a-id", slug="a-id", date="2026-10-01")
    assert [i["id"] for i in render.sort_posts([a, b])] == ["a-id", "b-id"] == [i["id"] for i in render.sort_posts([b, a])]


def test_filters_show_only_categories_that_exist_in_fixed_order():
    items = [post(category="transfer"), post(id="r2", slug="r2", category="degree")]
    html = render.reviews_filters(items)
    assert re.findall(r'data-filter="(\w+)"', html) == ["all", "degree", "transfer"]
    assert "대학원" not in html


# ---- 메인 흐르는 후기

def test_marquee_flows_when_four_or_more_and_clones_are_hidden_from_assistive_tech():
    html = render.reviews_marquee(posts(5))
    assert 'class="es5-marq is-flow"' in html
    assert html.count('class="es5-card"') == 5 + 5                       # 원본 + 복제
    assert html.count("data-clone") == 1                                   # 복제 묶음 하나
    assert html.count('aria-hidden="true"') == 1 and html.count('tabindex="-1"') == 5   # 복제는 보조기기·탭 이동에서 제외


def test_marquee_is_static_with_fewer_than_four_and_has_no_clones():
    html = render.reviews_marquee(posts(3))
    assert 'class="es5-marq is-static"' in html and html.count('class="es5-card"') == 3
    assert "data-clone" not in html and "tabindex" not in html


def test_marquee_shows_at_most_eight_latest():
    html = render.reviews_marquee(render.sort_posts(posts(12)))
    assert html.count('class="es5-card"') == 16
    assert "후기 11" in html and "후기 4" in html and "후기 3<" not in html


def test_marquee_duration_scales_with_card_count():
    assert "--dur:60s" in render.reviews_marquee(posts(8))
    assert "--dur:30s" in render.reviews_marquee(posts(4))


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
    assert "pt-mem-career" not in html
    assert render.team_extras([member()]) == ""


def test_team_card_shows_career():
    html = render.team_cards([member(career=["경력 5년", "사회복지사 2급"])])
    assert html.count("<li>") == 2
    assert "pt-mem-career" in render.team_extras([member(career=["경력"])])


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
