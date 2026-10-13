"""빌드 결과(HTML)의 내부 링크·이미지·앵커가 실제로 존재하는지 검사한다.

사용법: python tools/check_links.py        (저장소 루트에서. 먼저 python build.py 를 실행해 둘 것)
"""
from __future__ import annotations

import posixpath
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

EXTERNAL_PREFIXES = ("http://", "https://", "//", "mailto:", "tel:", "javascript:", "data:")
REF_ATTRS = ("href", "src", "data-full")
NON_SITE_DIRS = {"tests", "docs", "sections", ".superpowers", ".git"}   # 사이트로 배포되지 않는 폴더


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list = []
        self.ids: set = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key in REF_ATTRS:
            if attrs.get(key):
                self.refs.append((tag, attrs[key]))


def _parse(path: Path) -> _Collector:
    collector = _Collector()
    collector.feed(path.read_bytes().decode("utf-8"))
    return collector


def _find(search_roots, rel: str):
    for base in search_roots:
        candidate = base / rel
        if candidate.is_file():
            return candidate
    return None


def check(site_root: Path, extra_roots=()) -> list:
    """site_root의 모든 페이지를 검사해 문제 목록을 돌려준다. 파일은 site_root, extra_roots 순서로 찾는다."""
    roots = [site_root, *extra_roots]
    pages = [p for p in site_root.rglob("*.html")
             if p.name in ("index.html", "404.html")
             and not set(p.relative_to(site_root).parts[:-1]) & NON_SITE_DIRS]
    problems: list = []
    id_cache: dict = {}
    for page in sorted(pages):
        rel_page = page.relative_to(site_root).as_posix()
        collector = _parse(page)
        id_cache[rel_page] = collector.ids
        for tag, ref in collector.refs:
            if ref.startswith(EXTERNAL_PREFIXES):
                continue
            path_part, fragment = urldefrag(ref)
            if path_part == "":
                target_rel = rel_page
            else:
                url_path = unquote(urlparse(path_part).path)
                joined = url_path if url_path.startswith("/") else posixpath.join(posixpath.dirname(rel_page), url_path)
                target_rel = posixpath.normpath(joined.lstrip("/"))
                if target_rel == ".":
                    target_rel = ""
                if target_rel == "" or url_path.endswith("/"):
                    target_rel = (target_rel + "/index.html").lstrip("/")
            found = _find(roots, target_rel)
            if found is None:
                problems.append("%s: <%s> %s -> 파일 없음 (%s)" % (rel_page, tag, ref, target_rel))
                continue
            if fragment and found.suffix == ".html":
                key = found.relative_to(next(r for r in roots if str(found).startswith(str(r)))).as_posix()
                if key not in id_cache:
                    id_cache[key] = _parse(found).ids
                if fragment not in id_cache[key]:
                    problems.append("%s: %s -> 앵커 #%s 없음" % (rel_page, ref, fragment))
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    problems = check(root)
    for line in problems:
        print(line)
    print("링크 문제 %d건" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
