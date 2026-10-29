import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from PIL import Image

from site_build import data, render
from site_build.analytics import analytics_head
from site_build.core import SITE, ExtraPage, Inline, build_all
from site_build.data import DataError
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


# ---- 분석 도구(구글 애널리틱스 4 / 네이버 애널리틱스)

def test_analytics_is_empty_without_ids():
    assert analytics_head({}) == ""


def test_ga4_and_naver_snippets_use_the_given_ids_only():
    html = analytics_head({"ga4": "G-ABC123XYZ9", "naver": "s_1a2b3c4d5e6f"})
    assert "gtag('config', 'G-ABC123XYZ9')" in html
    assert 'wcs_add["wa"] = "s_1a2b3c4d5e6f"' in html and "wcslog.js" in html
    assert "wcslog" not in analytics_head({"ga4": "G-ABC123XYZ9"})


@pytest.mark.parametrize("bad", [{"ga4": "UA-123"}, {"ga4": "G-<script>"}, {"naver": "has space"}, {"naver": "x'; alert(1);//"}, {"ga4": 5}])
def test_analytics_ids_are_validated(bad):
    with pytest.raises(DataError, match="analytics"):
        data.validate_analytics(bad)


def test_head_extra_receives_analytics_when_configured(tmp_path):
    write(tmp_path / "data/analytics.json", {"ga4": "G-ABC123XYZ9"})
    tokens, extra = load_site(ROOT, data_root=tmp_path)
    out = tmp_path / "out"
    build_all(ROOT, out, tokens, extra)
    assert "gtag('config', 'G-ABC123XYZ9')" in (out / "index.html").read_text(encoding="utf-8")
    write(tmp_path / "data/analytics.json", {})
    tokens, extra = load_site(ROOT, data_root=tmp_path)
    build_all(ROOT, out, tokens, extra)
    assert "G-ABC123XYZ9" not in (out / "index.html").read_text(encoding="utf-8")


# ---- 사업자 구조화 정보

def test_organization_jsonld_uses_business_and_channel_data_without_phone_numbers():
    html = render.org_jsonld({"company": "에듀 <솔루션>", "regno": "000-00-00000", "address": "서울시 성북구 종암로"},
                             {"name": "팀 채널", "url": "https://www.youtube.com/@EDUSOLUTIONN"})
    blocks = [json.loads(b.replace("<\\/", "</")) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    doc = next(b for b in blocks if b["@type"] == "EducationalOrganization")
    site = next(b for b in blocks if b["@type"] == "WebSite")
    assert site["name"] == "에듀 <솔루션>" and site["url"] == SITE + "/" and site["inLanguage"] == "ko-KR"
    assert doc["@type"] == "EducationalOrganization" and doc["name"] == "에듀 <솔루션>" and doc["url"] == SITE + "/"
    assert doc["logo"] == SITE + "/assets/logo.png" and doc["sameAs"] == ["https://www.youtube.com/@EDUSOLUTIONN"]
    assert doc["address"]["streetAddress"] == "서울시 성북구 종암로"
    assert "telephone" not in doc and "email" not in doc
    assert render.org_jsonld({}, {}) == ""


# ---- 사이트맵 수정일

def page(path, lastmod=""):
    return ExtraPage(rel_dir=path.strip("/"), title="t", desc="d", url_path=path, parts=[Inline("<p>x</p>")], lastmod=lastmod)


def test_sitemap_has_lastmod_for_data_pages_and_the_index_pages_that_list_them(tmp_path):
    tokens, _ = load_site(ROOT, data_root=tmp_path / "no-data")
    extra = [page("/pages/education-info/a/", "2026-10-14"), page("/pages/education-info/b/", "2026-10-20"),
             page("/pages/reviews/r-1/", "2026-10-01"), page("/pages/reviews/r-2/")]
    build_all(ROOT, tmp_path, tokens, extra)
    xml = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    entry = lambda path: re.search(r"<url><loc>%s%s</loc>(.*?)</url>" % (re.escape(SITE), re.escape(path)), xml).group(1)
    assert entry("/pages/education-info/b/") == "<lastmod>2026-10-20</lastmod>"
    assert entry("/pages/reviews/r-2/") == ""                                  # 날짜가 없으면 적지 않는다
    assert entry("/pages/education-info/") == "<lastmod>2026-10-20</lastmod>"  # 목록은 가장 최근 글의 날짜
    assert entry("/pages/reviews/") == "<lastmod>2026-10-01</lastmod>"
    assert entry("/") == "<lastmod>2026-10-20</lastmod>"
    assert entry("/pages/team/") == ""


# ---- 파비콘

def test_favicon_ico_exists_at_the_site_root_and_is_a_real_icon():
    with Image.open(ROOT / "favicon.ico") as im:
        assert im.format == "ICO" and {16, 32, 48} <= {s[0] for s in im.info.get("sizes", {(im.width, im.height)})}


# ---- 상담 폼 접근성

class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.labels_for, self.controls, self.in_label = set(), [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "label":
            self.in_label += 1
            if a.get("for"):
                self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit", "button"):
            self.controls.append((tag, a, self.in_label > 0))

    def handle_endtag(self, tag):
        if tag == "label":
            self.in_label -= 1


def test_every_consult_form_control_has_a_label(tmp_path):
    tokens, extra = load_site(ROOT, data_root=tmp_path / "no-data")
    build_all(ROOT, tmp_path, tokens, extra)
    p = Controls()
    p.feed((tmp_path / "index.html").read_text(encoding="utf-8"))
    form = [c for c in p.controls if (c[1].get("id") or "").startswith("es6-")]
    assert len(form) >= 5
    for tag, attrs, wrapped in form:
        assert wrapped or attrs.get("aria-label") or attrs.get("id") in p.labels_for, "라벨이 연결되지 않은 입력: %s" % attrs


def test_llms_txt_is_markdown_with_real_page_links(tmp_path):
    tokens, _ = load_site(ROOT, data_root=tmp_path / "no-data")
    build_all(ROOT, tmp_path, tokens, [page("/pages/education-info/a/", "2026-10-14")])
    text = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert text.startswith("# 에듀솔루션\n")
    assert "](%s/pages/credit-bank/)" % SITE in text and "](%s/pages/education-info/a/)" % SITE in text
    assert "](%s/sitemap.xml)" % SITE in text
    assert 'rel="alternate" type="text/plain" href="/llms.txt"' in (tmp_path / "index.html").read_text(encoding="utf-8")
