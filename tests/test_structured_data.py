"""메인 페이지의 검색엔진용 구조화 정보(EducationalOrganization)가 빠지지 않게 지킨다."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_main_page_organization():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    org = next(b for b in blocks if b.get("@type") == "EducationalOrganization")
    assert org["name"] == "에듀솔루션"
    assert org["url"] == "https://edu-solution.co.kr/"
    assert (ROOT / "assets" / "logo.png").exists()
