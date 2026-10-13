from pathlib import Path

from site_build.core import build_all
from site_build.site import load_site
from tools.check_links import check

ROOT = Path(__file__).resolve().parent.parent


def test_built_site_has_no_broken_internal_links(tmp_path):
    tokens, extra = load_site(ROOT)
    build_all(ROOT, tmp_path, tokens, extra)
    assert check(tmp_path, extra_roots=[ROOT]) == []
