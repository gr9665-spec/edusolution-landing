#!/usr/bin/env python3
"""사이트를 빌드한다.  사용법: python build.py   (저장소 루트에서)

sections/, pages/<이름>/ 의 HTML 조각과 data/*.json 으로 모든 index.html, sitemap.xml, robots.txt,
옛 아임웹 주소(/27~/30) 이동 페이지를 만든다. 조각이나 데이터를 고친 뒤에는 항상 다시 실행한다.
"""
import sys
from pathlib import Path

from site_build.core import BuildError, build_all
from site_build.site import load_site

ROOT = Path(__file__).resolve().parent


def main() -> int:
    try:
        tokens, extra = load_site(ROOT)
        build_all(ROOT, ROOT, tokens, extra)
    except BuildError as exc:
        print("빌드 실패: %s" % exc, file=sys.stderr)
        return 1
    print("build done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
