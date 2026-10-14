import json
from pathlib import Path

import pytest

from site_build import data, render
from site_build.articles import article_page, articles_section, sort_articles
from site_build.core import SITE, build_all
from site_build.data import DataError
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent


def art(**over):
    item = {"id": "a1", "slug": "degree-credits", "title": "학위 학점 <총정리>", "description": "전문학사 80학점·학사 140학점의 구성을 정리했어요.",
            "category": "degree", "date": "2026-10-14", "source": "국가평생교육진흥원 학점은행제",
            "body": "<h2>제목</h2><p>본문 <strong>강조</strong> <a href=\"/pages/education-info/#grad\">대학원</a></p>"
                    "<table><tr><th>구분</th><th>학점</th></tr><tr><td>학사</td><td>140</td></tr></table>"}
    item.update(over)
    return item


@pytest.fixture
def root(tmp_path):
    (tmp_path / "assets").mkdir()
    return tmp_path


# ---- 검증

def test_valid_article_passes(root):
    data.validate_articles([art(), art(id="a2", slug="second", updated="2026-10-20", related=["degree-credits"])], root)


@pytest.mark.parametrize("key", ["slug", "title", "description", "category", "date", "body", "source"])
def test_missing_required_field_names_the_article_and_field(root, key):
    item = art()
    del item[key]
    with pytest.raises(DataError, match=r"a1.*%s" % key):
        data.validate_articles([item], root)


def test_duplicate_id_slug_bad_category_bad_dates_and_unknown_related(root):
    with pytest.raises(DataError, match="중복"):
        data.validate_articles([art(), art()], root)
    with pytest.raises(DataError, match="slug"):
        data.validate_articles([art(slug="Bad Slug")], root)
    with pytest.raises(DataError, match="category"):
        data.validate_articles([art(category="nope")], root)
    with pytest.raises(DataError, match="date"):
        data.validate_articles([art(date="2026-13-40")], root)
    with pytest.raises(DataError, match="updated"):
        data.validate_articles([art(updated="어제")], root)
    with pytest.raises(DataError, match="related"):
        data.validate_articles([art(related=["no-such-article"])], root)


@pytest.mark.parametrize("html", [
    "<script>alert(1)</script>",
    '<a href="//evil.example.com/x">링크</a>',
    '<a href="javascript:alert(1)">링크</a>',
    '<table onclick="x()"><tr><td>a</td></tr></table>',
    "<p>짝이 안 맞는 <strong>태그</p>",
])
def test_unsafe_body_is_rejected(root, html):
    with pytest.raises(DataError, match="body"):
        data.validate_articles([art(body=html)], root)


def test_phone_numbers_and_emails_are_rejected(root):
    with pytest.raises(DataError, match="개인정보"):
        data.validate_articles([art(body="<p>문의 010-1234-5678</p>")], root)


# ---- 목록

def test_sort_is_newest_first_then_by_title():
    items = [art(id="x", slug="x", title="나", date="2026-10-01"), art(id="y", slug="y", title="가", date="2026-10-01"),
             art(id="z", slug="z", title="다", date="2026-10-10")]
    assert [i["id"] for i in sort_articles(items)] == ["z", "y", "x"]


def test_section_lists_cards_with_links_labels_and_escaping():
    html = articles_section([art()])
    assert 'href="/pages/education-info/degree-credits/"' in html
    assert "학위 학점 &lt;총정리&gt;" in html and "학위 취득" in html and "2026.10.14" in html
    assert "전문학사 80학점" in html
    assert articles_section([]) == ""


# ---- 상세 페이지

def test_article_page_has_seo_fields_and_structured_data():
    page = article_page(art(updated="2026-10-20"), [art(), art(id="a2", slug="second", title="둘째 글")], ROOT)
    assert page.rel_dir == "pages/education-info/degree-credits" and page.url_path == "/pages/education-info/degree-credits/"
    assert page.title == "학위 학점 <총정리> | 에듀솔루션" and page.desc.startswith("전문학사 80학점")
    html = next(p.html for p in page.parts if hasattr(p, "html"))
    assert "<h1" in html and "학위 학점 &lt;총정리&gt;" in html
    assert 'href="/pages/education-info/"' in html and "<table" in html and "국가평생교육진흥원 학점은행제" in html
    start = html.index('<script type="application/ld+json">') + len('<script type="application/ld+json">')
    ld = json.loads(html[start:html.index("</script>", start)].replace("<\\/", "</"))
    assert ld["@type"] == "Article" and ld["headline"] == "학위 학점 <총정리>"
    assert ld["datePublished"] == "2026-10-14" and ld["dateModified"] == "2026-10-20"
    assert ld["mainEntityOfPage"] == SITE + "/pages/education-info/degree-credits/"


def test_related_articles_are_listed_when_given():
    first = art(related=["second"])
    other = art(id="a2", slug="second", title="둘째 글")
    html = next(p.html for p in article_page(first, [first, other], ROOT).parts if hasattr(p, "html"))
    assert 'href="/pages/education-info/second/"' in html and "둘째 글" in html
    plain = next(p.html for p in article_page(other, [first, other], ROOT).parts if hasattr(p, "html"))
    assert "함께 보면 좋은 글" not in plain


# ---- 사이트에 반영

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_load_site_adds_article_pages_and_token_and_stale_pages_are_removed(tmp_path):
    write(tmp_path / "data/articles.json", [art(), art(id="a2", slug="second", title="둘째 글", date="2026-10-01")])
    tokens, extra = load_site(ROOT, data_root=tmp_path)
    assert "pe-art" in tokens["education_articles"] and {p.url_path for p in extra} == {
        "/pages/education-info/degree-credits/", "/pages/education-info/second/"}
    out = tmp_path / "out"
    build_all(ROOT, out, tokens, extra)
    assert (out / "pages/education-info/degree-credits/index.html").exists()
    assert "/pages/education-info/second/" in (out / "sitemap.xml").read_text(encoding="utf-8")
    write(tmp_path / "data/articles.json", [art()])
    tokens, extra = load_site(ROOT, data_root=tmp_path)
    build_all(ROOT, out, tokens, extra)
    assert not (out / "pages/education-info/second").exists()          # 지운 글의 페이지도 함께 사라진다
    assert (out / "pages/education-info/index.html").exists()          # 목록 페이지는 그대로
