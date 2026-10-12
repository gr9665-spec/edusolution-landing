import pytest
from PIL import Image

from site_build.cases import case_html, case_page
from site_build.core import Inline

TEAM = {"t1": {"id": "t1", "name": "홍길동 담당자", "role": "학위 · 편입 전문 플래너", "photo": "assets/p.jpg"}}


@pytest.fixture
def root(tmp_path):
    (tmp_path / "assets" / "proof").mkdir(parents=True)
    Image.new("RGB", (800, 500), "white").save(tmp_path / "assets" / "proof" / "case a.jpg")
    return tmp_path


def case(**over):
    item = {"id": "k1", "kind": "case", "goal": ["transfer"], "source": "테스트", "slug": "univ-a-2026",
            "title": 'A대 "편입" 합격', "school": "A대학교", "track": "일반편입", "duration": "8개월",
            "profile": {"age": "20대", "background": "전문대 <졸업>", "credits": "80학점"},
            "plan": [{"label": "1학기", "detail": "전공 18학점 & 교양"}, {"label": "2학기", "detail": "전공 18학점"}],
            "result": "최종 합격", "planner": "t1", "seoDescription": "A대 편입 합격 사례입니다."}
    item.update(over)
    return item


def test_case_page_has_expected_address_title_and_description(root):
    page = case_page(case(), TEAM, root)
    assert page.rel_dir == "pages/reviews/univ-a-2026"
    assert page.url_path == "/pages/reviews/univ-a-2026/"
    assert page.title == 'A대 "편입" 합격 | 에듀솔루션'          # 따옴표 이스케이프는 head 생성 단계에서 처리
    assert page.desc == "A대 편입 합격 사례입니다."
    assert page.parts[0] == root / "sections" / "00-nav.html"
    assert isinstance(page.parts[1], Inline)


def test_seo_title_overrides_default(root):
    assert case_page(case(seoTitle="A대학교 편입 후기 | 에듀솔루션"), TEAM, root).title == "A대학교 편입 후기 | 에듀솔루션"


def test_case_html_contains_tables_planner_cta_and_escapes(root):
    html = case_html(case(), TEAM["t1"], root)
    assert "전문대 &lt;졸업&gt;" in html and "전공 18학점 &amp; 교양" in html
    assert html.count("<th>1학기</th>") == 1 and html.count("<th>2학기</th>") == 1
    assert "홍길동 담당자" in html and 'href="/#es-form"' in html and 'href="/pages/reviews/"' in html
    assert "인증 자료" not in html              # 인증 이미지가 없으면 영역 자체를 만들지 않는다


def test_case_html_with_proof_images_uses_encoded_path_and_size(root):
    html = case_html(case(proofImages=["assets/proof/case a.jpg"]), TEAM["t1"], root)
    assert 'src="/assets/proof/case%20a.jpg"' in html and 'width="800" height="500"' in html
    assert "인증 자료" in html
