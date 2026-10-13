from pathlib import Path

from site_build.core import Inline, SITE, build_all
from site_build.posts import post_html, post_page
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent


def TOKENS(tmp_path):
    return load_site(ROOT, data_root=tmp_path / "no-data")[0]       # 데이터가 없는 폴더 -> 토큰은 모두 빈 문자열


def post(**over):
    item = {"id": "r1", "kind": "post", "slug": "r-1a2b3c4d", "title": '학사 "취득" <후기>', "subtitle": "직장인 / 학사 학위",
            "category": "degree", "body": "<p>본문 <strong>강조</strong></p>", "source": "테스트",
            "date": "2026-10-13", "image": "assets/proof/한글 사진.jpg"}
    item.update(over)
    return item


def test_detail_shows_back_link_badge_title_subtitle_image_body_and_cta_but_no_date():
    html = post_html(post())
    assert 'href="/pages/reviews/"' in html and "학위 취득" in html
    assert "<h1" in html and "학사 &quot;취득&quot; &lt;후기&gt;" in html
    assert "직장인 / 학사 학위" in html
    assert "<time" not in html and "2026.10.13" not in html and "2026-10-13" not in html
    assert 'src="/assets/proof/%ED%95%9C%EA%B8%80%20%EC%82%AC%EC%A7%84.jpg"' in html
    assert "<p>본문 <strong>강조</strong></p>" in html                 # 본문은 이미 안전한 HTML
    assert 'href="/#es-form"' in html


def test_default_image_is_hidden():
    html = post_html(post(image=None, date=None))
    assert "review-default" not in html and "<img" not in html and "<time" not in html


def test_page_has_title_description_url_and_og_image():
    page = post_page(post(), ROOT)
    assert page.rel_dir == "pages/reviews/r-1a2b3c4d" and page.url_path == "/pages/reviews/r-1a2b3c4d/"
    assert page.title == '학사 "취득" <후기> | 에듀솔루션' and page.desc == "직장인 / 학사 학위"
    assert page.og_image == SITE + "/assets/proof/%ED%95%9C%EA%B8%80%20%EC%82%AC%EC%A7%84.jpg"
    assert post_page(post(image=None), ROOT).og_image == ""           # 비어 있으면 사이트 기본 이미지
    assert any(isinstance(p, Inline) for p in page.parts)


def test_built_detail_page_carries_og_image_and_is_in_sitemap(tmp_path):
    page = post_page(post(), ROOT)
    build_all(ROOT, tmp_path, TOKENS(tmp_path), [page])
    built = (tmp_path / "pages/reviews/r-1a2b3c4d/index.html").read_text(encoding="utf-8")
    assert 'property="og:image" content="%s"' % page.og_image.replace("&", "&amp;") in built
    assert "<title>학사 &quot;취득&quot; &lt;후기&gt; | 에듀솔루션</title>" in built
    assert "/pages/reviews/r-1a2b3c4d/" in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")


def test_page_without_og_image_keeps_the_site_default(tmp_path):
    build_all(ROOT, tmp_path, TOKENS(tmp_path), [post_page(post(image=None), ROOT)])
    built = (tmp_path / "pages/reviews/r-1a2b3c4d/index.html").read_text(encoding="utf-8")
    assert 'property="og:image" content="%s/assets/og-image.png"' % SITE in built
