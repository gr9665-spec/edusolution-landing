"""빌드 결과가 기준본(tests/golden)과 같은지 확인한다.

LOOSE에 든 페이지는 데이터로 만들어지는 부분이 있어 태그 사이 공백만 다를 수 있으므로
공백을 무시하고 비교한다. 나머지는 바이트 단위(줄바꿈 LF 기준)로 같아야 한다.
"""
import re
from pathlib import Path

import pytest

from site_build.core import build_all
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"
GOLDEN_FILES = sorted(p.relative_to(GOLDEN).as_posix() for p in GOLDEN.rglob("*") if p.is_file())

LOOSE = {"index.html", "pages/reviews/index.html"}


def prepare(rel: str, data: bytes) -> str:
    text = data.decode("utf-8").replace("\r\n", "\n")
    if rel in LOOSE:
        text = re.sub(r">\s+<", "><", text).strip()
    return text


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("built")
    tokens, extra = load_site(ROOT)
    build_all(ROOT, out, tokens, extra)
    return out


def test_golden_snapshot_is_complete():
    assert len(GOLDEN_FILES) == 23


@pytest.mark.parametrize("rel", GOLDEN_FILES)
def test_output_matches_golden(built, rel):
    assert prepare(rel, (built / rel).read_bytes()) == prepare(rel, (GOLDEN / rel).read_bytes()), \
        "%s 이(가) 기준본과 다릅니다" % rel
