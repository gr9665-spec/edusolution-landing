# 신뢰도 강화 · 데이터 기반 후기·합격 사례 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 후기·합격 사례·실적 수치·팀 이력·사업자 정보를 데이터 파일로 관리하고, 파일만 고쳐 빌드하면 페이지·sitemap·검색용 정보가 함께 갱신되는 사이트로 바꾼다.

**Architecture:** `build.sh`를 Python 빌더(`build.py` + `site_build/`)로 교체한다. 기존 HTML 조각(`sections/`, `pages/*/`)은 그대로 두고, 데이터에서 만든 HTML을 `{{토큰}}` 자리에 끼워 넣는다. 데이터가 비어 있으면 토큰은 빈 문자열이 되고, 빈 조각은 출력에서 건너뛰어 기존 페이지가 한 글자도 바뀌지 않는다.

**Tech Stack:** Python 3.12, Pillow, pytest (정적 HTML/CSS/JS, GitHub Pages, Cloudflare)

**Spec:** `docs/superpowers/specs/2026-10-12-trust-content-design.md`

## Global Constraints

- 실제로 증명 가능한 자료만 쓴다. 후기·수치를 만들어 넣지 않는다. 테스트용 가짜 값은 테스트 코드 안에서만 쓰고 `data/`에 커밋하지 않는다.
- 수치 항목은 `source`(근거)와 `asOf`(기준 시점)가 필수이며, 비어 있으면 빌드가 실패한다.
- 수강생 이름은 `김○○` 표기를 유지한다. 캡처의 이름·연락처·프로필 사진은 가려진 상태로만 게시하고, 가림 결과를 사용자가 직접 확인하기 전에는 게시하지 않는다. 원본은 저장소에 올리지 않는다(`raw-proof/`는 `.gitignore`).
- 구글 후기 별점 구조화 마크업(Review schema), 후기 개수 표시, 탭형 후기 구분, 메뉴 추가는 하지 않는다. 메뉴는 4개 그대로다.
- 기존 디자인(색·폰트·카드)을 이어 쓴다. 위젯 코드의 `rem`은 `html{font-size:10px}` 기준이다.
- 모든 빌드 입출력은 UTF-8, 줄바꿈은 LF다(`read_text`가 CRLF를 LF로 읽는다).
- 작업은 `site-trust` 브랜치에서 하고, 사용자 승인 전에는 master에 합치지 않는다.
- 커밋은 `git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit`으로 하고, 메시지 끝에 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` 줄을 붙인다.
- 테스트는 저장소 루트에서 `python -m pytest -q`로 실행한다. 한글 출력이 깨지면 `PYTHONIOENCODING=utf-8`을 앞에 붙인다.

## Review Focus

스펙은 방향만 정하고 아래 입력들의 동작은 정하지 않았다. 각 줄은 소유한 Task에 테스트로 고정한다.

1. **특수문자(`<`, `&`, `"`)가 들어간 이름·제목·대체 텍스트** — 화면이 깨지거나 태그가 새어 나오면 안 된다. (Task 3 `test_text_card_keeps_authored_html_but_escapes_plain_fields`, Task 5 `test_capture_card_encodes_path_escapes_alt_and_lazy_loads`, `test_case_card_links_to_detail_page_and_escapes`, `test_case_html_contains_tables_planner_cta_and_escapes`)
2. **한글·공백이 든 이미지 파일명** — 주소로 퍼센트 인코딩되어 실제로 열려야 한다. (Task 5 `test_capture_card_encodes_path_escapes_alt_and_lazy_loads`, `test_url_path_quotes_unicode_and_spaces`, `test_case_html_with_proof_images_uses_encoded_path_and_size`, Task 7 링크 검사)
3. **데이터가 비었거나 파일이 없을 때** — 수치·사업자 정보·합격 사례가 없어도 빌드는 성공하고 기존 페이지는 바뀌지 않아야 한다. 이미지 경로가 틀리면 빌드가 멈추고 알려줘야 한다. (Task 3 `test_empty_data_renders_nothing`, Task 5 `test_capture_requires_existing_image`, Task 6 `test_footer_renders_...`·`test_stats_strip_...`의 빈 입력, 그리고 Task 6 이후에도 통과해야 하는 `tests/test_golden.py`)
4. **slug 형식·중복** — 대문자·공백·한글·중복 slug는 주소 충돌이나 깨진 주소가 되므로 막는다. (Task 5 `test_bad_slug_is_rejected`, `test_duplicate_slug_is_rejected`)
5. **메모장으로 저장한 JSON(UTF-8 BOM)과 깨진 JSON** — BOM은 허용하고, 깨진 JSON은 파일 이름을 알려 주며 실패해야 한다. (Task 3 `test_load_accepts_utf8_bom_and_korean`, `test_load_reports_broken_json_with_file_name`)

---

## 파일 구조

```
build.py                      빌드 진입점 (build.sh 대체)
requirements.txt  pytest.ini  .gitattributes  .gitignore
site_build/
  core.py      페이지 조립, {{토큰}} 치환, 옛 주소 이동 페이지, sitemap, robots
  data.py      data/*.json 읽기와 검증 (DataError)
  render.py    데이터 -> HTML 조각 (후기, 팀, 수치 띠, 푸터)
  cases.py     합격 사례 상세 페이지
  site.py      data 읽기 + 검증 + 토큰·추가 페이지 만들기 (load_site)
tools/
  mask.py          개인정보 가림 도구
  check_links.py   빌드 결과의 링크·이미지·앵커 검사
data/   reviews.json  team.json  stats.json  business.json
assets/proof/   가림 처리된 후기·인증 이미지
sections/11-stats-strip.html  sections/12-footer.html   (토큰 한 줄짜리 조각)
tests/  golden/ + test_*.py
```

> **Task 순서는 스펙의 작업 순서와 조금 다르다.** 합격 사례가 담당 플래너(`team.json`의 id)를 참조하므로 팀 데이터(Task 4)를 사례(Task 5)보다 먼저 한다.

---

### Task 1: build.py로 교체하고 기존 출력이 한 글자도 안 바뀌는지 증명

**Files:**
- Create: `.gitattributes`, `.gitignore`, `requirements.txt`, `pytest.ini`, `site_build/__init__.py`, `site_build/core.py`, `site_build/site.py`, `build.py`, `tests/snapshot_golden.py`, `tests/test_golden.py`, `tests/golden/**`
- Modify: `README.md` (build.sh -> build.py)
- Delete: `build.sh`

**Interfaces:**
- Produces: `site_build.core.build_all(root: Path, out: Path, tokens: Mapping[str,str] | None, extra_pages: Sequence[ExtraPage]) -> None`, `ExtraPage(rel_dir, title, desc, url_path, parts, logo)`, `Inline(html)`, `BuildError`, `expand(text, tokens, where)`, `read_text(path)`, `write_text(path, text)`; `site_build.site.load_site(root) -> (tokens: dict, extra_pages: list)`

- [ ] **Step 1: 현재 상태 확인 — build.sh의 출력이 커밋된 파일과 같은지**

```bash
git status --short
git branch --show-current
bash build.sh
git status --short
```
Expected: `site-trust` 브랜치이고, `bash build.sh` 전후 `git status --short`가 모두 비어 있다(생성물이 커밋된 것과 같다). 비어 있지 않으면 중단하고 원인을 먼저 확인한다.

- [ ] **Step 2: 줄바꿈·의존성 설정 파일 만들기**

`.gitattributes`
```
* text=auto eol=lf
```

`.gitignore`
```
__pycache__/
.pytest_cache/
```

`requirements.txt`
```
Pillow
pytest
```

`pytest.ini`
```
[pytest]
pythonpath = .
testpaths = tests
```

```bash
git status --short
```
Expected: 새 파일 4개(`.gitattributes`, `.gitignore`, `pytest.ini`, `requirements.txt`)만 `??`로 나오고, 기존 파일에 `M`이 없다. 기존 파일에 `M`이 보이면 `.gitattributes`를 되돌리고 중단한다. (`docs/superpowers/plans/` 계획 파일이 `??`로 보이는 것은 정상이다.)

- [ ] **Step 3: 기준본(golden) 만들기 — 현재 생성물을 복사**

`tests/snapshot_golden.py`
```python
"""현재 저장소의 생성물을 tests/golden 으로 복사한다(줄바꿈은 LF로 통일).

사람이 화면 변화를 확인하고 승인한 변경 뒤에만 실행한다.  사용법: python tests/snapshot_golden.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"

FILES = ["index.html", "sitemap.xml", "robots.txt",
         "27/index.html", "28/index.html", "29/index.html", "30/index.html"]
for folder in ("team", "credit-bank", "education-info", "reviews"):
    FILES += ["pages/%s/%s" % (folder, name)
              for name in ("index.html", "00-nav.html", "03-kakao-float-button.html", "04-diagnostic-popup.html")]


def main() -> None:
    if GOLDEN.exists():
        shutil.rmtree(GOLDEN)
    for rel in FILES:
        dst = GOLDEN / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    print("golden %d개 저장" % len(FILES))


if __name__ == "__main__":
    main()
```

```bash
python tests/snapshot_golden.py
```
Expected: `golden 23개 저장`

- [ ] **Step 4: 실패하는 테스트 작성**

`tests/test_golden.py`
```python
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

LOOSE = set()


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
```

```bash
python -m pytest tests/test_golden.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'site_build'`

- [ ] **Step 5: 빌더 구현**

`site_build/__init__.py` — 빈 파일.

`site_build/core.py`
```python
"""정적 사이트 빌더의 핵심: 페이지 조립, 토큰 치환, 옛 주소 이동 페이지, sitemap, robots."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Mapping, Sequence, Union

SITE = "https://edu-solution.co.kr"
OG_IMAGE = SITE + "/assets/og-image.png"
TOKEN_RE = re.compile(r"\{\{([a-z_]+)\}\}")

HEAD = Template("""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<meta name="description" content="$desc">
<link rel="canonical" href="$site$path">
<link rel="icon" href="/assets/logo.png">
<meta name="theme-color" content="#1a2d4a">
<meta property="og:type" content="website">
<meta property="og:site_name" content="에듀솔루션">
<meta property="og:title" content="$title">
<meta property="og:description" content="$desc">
<meta property="og:url" content="$site$path">
<meta property="og:image" content="$og_image">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="648">
<meta name="twitter:card" content="summary_large_image">
<style>
/* 아임웹이 기본으로 깔아주던 부트스트랩 기본 스타일 중 레이아웃에 영향을 주는 것만 복원 (위젯 코드의 rem 단위는 html 10px 기준) */
html{font-size:10px;-webkit-tap-highlight-color:rgba(0,0,0,0)}
*,*::before,*::after{box-sizing:border-box}
h1,h2,h3,h4,h5,h6{font-family:'Noto Sans KR',sans-serif}
body{margin:0;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#333;background-color:#fff}
p{margin:0 0 10px}
a{color:#337ab7;text-decoration:none}
button,input,optgroup,select,textarea{margin:0;font:inherit;color:inherit}
label{display:inline-block;max-width:100%;margin-bottom:5px;font-weight:700}
</style>
""")

REDIRECT = Template("""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>페이지가 이동했습니다 | 에듀솔루션</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=$target">
<link rel="canonical" href="$site$target">
<script>location.replace("$target");</script>
</head>
<body>
<p>페이지가 이동했습니다. <a href="$target">이동하기</a></p>
</body>
</html>
""")

MAIN_TITLE = "학점은행제 전문 플래너 | 에듀솔루션 edusolution"
MAIN_DESC = (
    "학점은행제 전문 플래너 팀이 학위 취득 목표에 맞는 수강 플랜을 1:1로 설계해 드립니다. "
    "사회복지사, 보육교사, 편입 준비 등 다양한 목적에 맞춰 빠르고 정확하게 안내해 드리니 "
    "지금 바로 무료 상담을 신청해보세요!"
)

MAIN_FRAGMENTS = [
    "sections/00-nav.html",
    "sections/01-hero-image.html",
    "sections/02-hero-navy-features.html",
    "sections/03-service-grid.html",
    "sections/04-caution-compare.html",
    "sections/05-reviews.html",
    "sections/06-consult-form.html",
    "sections/09-kakao-float-button.html",
    "sections/10-diagnostic-popup.html",
    "sections/08-form-label-fix.html",
    "sections/07-animations.html",
]

# (폴더, 제목, 설명)
SUBPAGES = [
    ("team", "팀 에듀솔루션 | 에듀솔루션", "에듀솔루션 팀과 상담 담당자를 소개합니다."),
    ("credit-bank", "학점은행제란? 제도 개요·목표·진행 절차 | 에듀솔루션",
     "학점은행제의 제도 개요, 목표별 활용법, 진행 절차와 자주 묻는 질문을 한눈에 정리했습니다."),
    ("education-info", "학점은행제 교육정보 | 학위·자격증·편입·대학원 | 에듀솔루션",
     "학위 취득, 사회복지사 2급, 보육교사 2급, 기사·산업기사 응시자격, 편입, 대학원까지 목표별 조건과 과정을 정리했습니다."),
    ("reviews", "수강생 후기 | 에듀솔루션",
     "에듀솔루션과 함께 학점은행제 과정을 마친 수강생분들의 후기를 목표별로 확인해 보세요."),
]

# 옛 아임웹 주소 폴더 -> 새 주소
REDIRECTS = {
    "27": "/pages/team/",
    "28": "/pages/credit-bank/",
    "29": "/pages/education-info/",
    "30": "/pages/reviews/",
}

SITEMAP_PATHS = [
    "/", "/pages/team/", "/pages/credit-bank/", "/pages/education-info/", "/pages/reviews/",
]

NAV_LOGO_SRC = "../assets/logo.png"


@dataclass(frozen=True)
class Inline:
    """파일이 아니라 코드에서 만든 HTML 조각."""
    html: str


Part = Union[Path, Inline]


@dataclass(frozen=True)
class ExtraPage:
    """데이터에서 만들어지는 추가 페이지(예: 합격 사례 상세)."""
    rel_dir: str            # 예: "pages/reviews/univ-a"
    title: str
    desc: str
    url_path: str           # 예: "/pages/reviews/univ-a/"
    parts: Sequence[Part]
    logo: str = "/assets/logo.png"


class BuildError(Exception):
    pass


def read_text(path: Path) -> str:
    """항상 LF로 읽는다. Windows의 CRLF 체크아웃과 무관하게 같은 결과가 나오게 하기 위해서다."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def expand(text: str, tokens: Mapping[str, str], where: str = "") -> str:
    """{{이름}} 토큰을 치환한다. 정의되지 않은 토큰은 오류다."""
    def repl(m: re.Match) -> str:
        name = m.group(1)
        if name not in tokens:
            raise BuildError("정의되지 않은 토큰 {{%s}} (%s)" % (name, where))
        return tokens[name]
    return TOKEN_RE.sub(repl, text)


def make_head(title: str, desc: str, url_path: str, head_extra: str) -> str:
    return HEAD.substitute(
        title=html.escape(title, quote=True),
        desc=html.escape(desc, quote=True),
        site=SITE,
        path=url_path,
        og_image=OG_IMAGE,
    ) + head_extra + "</head>\n<body>\n"


def assemble_page(root: Path, tokens: Mapping[str, str], logo: str, title: str, desc: str,
                  url_path: str, parts: Sequence[Part]) -> str:
    out = [make_head(title, desc, url_path, read_text(root / "head-extra.html"))]
    for part in parts:
        if isinstance(part, Inline):
            text, where = part.html, "inline"
        else:
            text, where = read_text(part), part.name
            if part.name == "00-nav.html":
                text = read_text(root / "sections" / "00-nav.html").replace(NAV_LOGO_SRC, logo)
        text = expand(text, tokens, where)
        if not text.strip():    # 데이터가 없어 비어 있는 조각(공백뿐인 것 포함)은 건너뛴다(출력이 바뀌지 않게)
            continue
        out.append(text + "\n\n")
    out.append("</body>\n</html>\n")
    return "".join(out)


def sync_shared_fragments(root: Path, out: Path) -> None:
    """서브페이지 폴더에 공용 조각(nav, 카카오 버튼, 진단 팝업) 사본을 만든다."""
    nav = read_text(root / "sections" / "00-nav.html").replace(NAV_LOGO_SRC, "../../assets/logo.png")
    kakao = read_text(root / "sections" / "09-kakao-float-button.html")
    popup = read_text(root / "sections" / "10-diagnostic-popup.html")
    for folder, _, _ in SUBPAGES:
        base = out / "pages" / folder
        write_text(base / "00-nav.html", nav)
        write_text(base / "03-kakao-float-button.html", kakao)
        write_text(base / "04-diagnostic-popup.html", popup)


def sub_parts(root: Path, folder: str) -> list:
    base = root / "pages" / folder
    return [
        base / "00-nav.html",
        base / "01-main-content.html",
        root / "sections" / "09-kakao-float-button.html",
        root / "sections" / "10-diagnostic-popup.html",
        base / "02-animations.html",
    ]


def build_all(root: Path, out: Path, tokens: Mapping[str, str] | None = None,
              extra_pages: Sequence[ExtraPage] = ()) -> None:
    tokens = tokens or {}
    sync_shared_fragments(root, out)

    write_text(out / "index.html", assemble_page(
        root, tokens, "assets/logo.png", MAIN_TITLE, MAIN_DESC, "/",
        [root / n for n in MAIN_FRAGMENTS]))

    for folder, title, desc in SUBPAGES:
        write_text(out / "pages" / folder / "index.html", assemble_page(
            root, tokens, "../../assets/logo.png", title, desc, "/pages/%s/" % folder,
            sub_parts(root, folder)))

    for page in extra_pages:
        write_text(out / page.rel_dir / "index.html", assemble_page(
            root, tokens, page.logo, page.title, page.desc, page.url_path, page.parts))

    for folder, target in REDIRECTS.items():
        write_text(out / folder / "index.html", REDIRECT.substitute(site=SITE, target=target))

    paths = SITEMAP_PATHS + [p.url_path for p in extra_pages]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += ["  <url><loc>%s%s</loc></url>" % (SITE, p) for p in paths]
    sitemap.append("</urlset>")
    write_text(out / "sitemap.xml", "\n".join(sitemap) + "\n")

    write_text(out / "robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)
```

`site_build/site.py`
```python
"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path


def load_site(root: Path):
    return {}, []
```

`build.py`
```python
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
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
python -m pytest tests/test_golden.py -q
```
Expected: `24 passed` (기준본 완전성 1 + 파일 23)

- [ ] **Step 7: 실제 저장소에서 제자리 빌드해도 아무것도 안 바뀌는지 확인**

```bash
python build.py
git status --short
```
Expected: `build done`, 그리고 `git status --short`에 새 파일(`.gitattributes`, `build.py` 등)만 있고 **기존 생성물에는 `M`이 없다**. `M`이 있으면 `git diff <파일>`로 원인을 보고 해결한 뒤에만 진행한다.

- [ ] **Step 8: build.sh 삭제, README 갱신, 커밋**

```bash
git rm -q build.sh
sed -i 's/bash build\.sh/python build.py/g' README.md
grep -n "build" README.md
```
Expected: README에 `build.sh`가 남아 있지 않다. README의 "빌드와 로컬 미리보기" 문단에 아래 한 줄을 추가한다: `처음 한 번만 \`pip install -r requirements.txt\`로 의존성(Pillow, pytest)을 설치합니다.`

```bash
git add .gitattributes .gitignore requirements.txt pytest.ini site_build build.py tests README.md
git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit -m "$(cat <<'EOF'
Replace build.sh with Python builder, proven byte-identical on existing pages

- site_build/core.py: 조립·토큰 치환·이동 페이지·sitemap, CRLF 체크아웃과 무관하게 LF로 출력
- tests/golden: 기존 생성물 23개를 기준본으로 고정하고 test_golden으로 비교

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: 개인정보 가림 도구

**Files:**
- Create: `tools/__init__.py`, `tools/mask.py`, `tests/test_mask.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `tools.mask.mask_image(src: Path, dst: Path, boxes: list[tuple[int,int,int,int]], max_width: int = 1200) -> tuple[int,int]`, `parse_box(text) -> tuple`, CLI `python tools/mask.py SRC DST --box x,y,w,h ...`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_mask.py`

```python
import statistics

import pytest
from PIL import Image

from tools.mask import FILL, mask_image, parse_box


def noise_image(path, size=(400, 300), fmt="PNG"):
    Image.effect_noise(size, 80).convert("RGB").save(path, fmt)
    return path


def region_pixels(im, box):
    x, y, w, h = box
    return [im.getpixel((px, py)) for px in range(x, x + w) for py in range(y, y + h)]


def test_box_is_filled_with_solid_color(tmp_path):
    src = noise_image(tmp_path / "a.png")
    dst = tmp_path / "out" / "a.jpg"
    mask_image(src, dst, [(40, 60, 120, 50)], max_width=4000)
    with Image.open(dst) as im:
        inner = region_pixels(im, (50, 70, 100, 30))   # JPEG 경계 번짐을 피해 안쪽만 본다
    assert all(abs(p[c] - FILL[c]) <= 8 for p in inner for c in range(3))


def test_outside_box_is_left_alone(tmp_path):
    src = noise_image(tmp_path / "a.png")
    dst = tmp_path / "a.jpg"
    mask_image(src, dst, [(40, 60, 120, 50)], max_width=4000)
    with Image.open(dst) as im:
        outside = [p[0] for p in region_pixels(im, (200, 150, 100, 100))]
    assert statistics.pstdev(outside) > 20   # 노이즈 그대로(가려지지 않음)


def test_wide_image_is_resized_to_max_width(tmp_path):
    src = noise_image(tmp_path / "wide.png", size=(2000, 1000))
    size = mask_image(src, tmp_path / "wide.jpg", [])
    assert size == (1200, 600)


def test_box_outside_image_raises(tmp_path):
    src = noise_image(tmp_path / "a.png")
    with pytest.raises(ValueError, match="밖"):
        mask_image(src, tmp_path / "a.jpg", [(380, 10, 50, 20)])


def test_metadata_is_not_kept(tmp_path):
    src = tmp_path / "meta.jpg"
    im = Image.effect_noise((200, 200), 80).convert("RGB")
    exif = Image.Exif()
    exif[0x010F] = "SomePhoneMaker"
    im.save(src, "JPEG", exif=exif)
    dst = tmp_path / "clean.jpg"
    mask_image(src, dst, [])
    with Image.open(dst) as out:
        assert len(out.getexif()) == 0


def test_non_jpg_destination_is_rejected(tmp_path):
    src = noise_image(tmp_path / "a.png")
    with pytest.raises(ValueError, match="jpg"):
        mask_image(src, tmp_path / "a.png", [])


def test_parse_box_validates_format():
    assert parse_box("1,2,3,4") == (1, 2, 3, 4)
    for bad in ("1,2,3", "a,b,c,d", "1,2,0,4"):
        with pytest.raises(Exception):
            parse_box(bad)
```

- [ ] **Step 2: 실패 확인**

```bash
python -m pytest tests/test_mask.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 3: 구현** — `tools/__init__.py`는 빈 파일, `tools/mask.py`

```python
"""후기·합격 인증 이미지의 개인정보(이름, 연락처, 프로필 사진 등)를 가리는 도구.

사용법:
    python tools/mask.py raw-proof/원본.png assets/proof/결과.jpg --box 40,120,300,60 --box 10,10,80,80

--box x,y,w,h  가릴 사각형(원본 이미지 픽셀 좌표). 여러 번 지정할 수 있다.
결과는 JPEG로만 저장하며 EXIF·위치 정보 같은 메타데이터는 남기지 않는다.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

MAX_WIDTH = 1200
FILL = (46, 62, 90)

Box = tuple[int, int, int, int]


def parse_box(text: str) -> Box:
    try:
        parts = [int(v) for v in text.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--box는 x,y,w,h 형식의 정수여야 합니다: " + text) from exc
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise argparse.ArgumentTypeError("--box는 x,y,w,h 형식(w,h는 양수)이어야 합니다: " + text)
    return (parts[0], parts[1], parts[2], parts[3])


def mask_image(src: Path, dst: Path, boxes: list[Box], max_width: int = MAX_WIDTH) -> tuple[int, int]:
    """boxes 영역을 단색으로 덮고, 가로 max_width 이하로 줄여 dst(JPEG)에 저장한다. 저장한 크기를 돌려준다."""
    if dst.suffix.lower() not in (".jpg", ".jpeg"):
        raise ValueError("결과 파일은 .jpg 로 저장해야 합니다: %s" % dst)
    with Image.open(src) as opened:
        im = ImageOps.exif_transpose(opened).convert("RGB")
    draw = ImageDraw.Draw(im)
    for x, y, w, h in boxes:
        if x < 0 or y < 0 or x + w > im.width or y + h > im.height:
            raise ValueError("가림 영역이 이미지(%dx%d) 밖입니다: %d,%d,%d,%d" % (im.width, im.height, x, y, w, h))
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=FILL)
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "JPEG", quality=85, optimize=True)
    return im.size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="이미지의 개인정보 영역을 가립니다.")
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    parser.add_argument("--box", type=parse_box, action="append", default=[], help="가릴 영역 x,y,w,h")
    args = parser.parse_args(argv)
    size = mask_image(args.src, args.dst, args.box)
    print("저장: %s (%dx%d, 가린 영역 %d곳)" % (args.dst, size[0], size[1], len(args.box)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`.gitignore`에 한 줄 추가(원본 개인정보 이미지 폴더를 git에서 제외):
```
raw-proof/
```

- [ ] **Step 4: 통과 확인**

```bash
python -m pytest tests/test_mask.py -q
```
Expected: `7 passed`

- [ ] **Step 5: 커밋**

```bash
git add tools tests/test_mask.py .gitignore
git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit -m "$(cat <<'EOF'
Add privacy masking tool for review and proof images

가릴 영역을 단색으로 덮고 EXIF를 제거한 JPEG(가로 1200px 이하)로 저장. 원본 폴더 raw-proof/는 git에서 제외

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: 후기 데이터 계층과 후기 페이지·메인 후기 섹션 데이터화

**Files:**
- Create: `site_build/data.py`, `site_build/render.py`, `data/reviews.json`, `tests/test_data.py`, `tests/test_render.py`
- Modify: `site_build/site.py`, `pages/reviews/01-main-content.html`, `sections/05-reviews.html`, `tests/test_golden.py`

**Interfaces:**
- Consumes: Task 1의 `BuildError`, `load_site` 규약
- Produces: `data.load(root, name, default)`, `data.validate_reviews(items, root, team_ids=frozenset())`, `data.DataError`, `render.esc`, `render.reviews_grid(items, root)`, `render.reviews_filters(items)`, `render.reviews_featured(items)`, 토큰 `reviews_grid`·`reviews_filters`·`reviews_featured`, `render.CARD_RENDERERS`, `data.KIND_CHECKS`(종류별 검사/렌더 표 — Task 5가 항목을 추가)

- [ ] **Step 1: 데이터 검증 테스트 작성** — `tests/test_data.py`

```python
import json

import pytest

from site_build import data
from site_build.data import DataError


def text_review(**over):
    item = {"id": "r1", "kind": "text", "goal": ["degree"], "source": "테스트",
            "headline": "제목", "body": "본문", "person": "김○○ 님 (30대)", "meta": "직장인", "badge": "학사"}
    item.update(over)
    return item


@pytest.fixture
def root(tmp_path):
    (tmp_path / "assets").mkdir()
    for name in ("p.jpg", "cap.jpg", "proof.jpg"):
        (tmp_path / "assets" / name).write_bytes(b"x")
    return tmp_path


# ---- 읽기

def test_load_returns_default_when_file_missing(tmp_path):
    assert data.load(tmp_path, "reviews.json", []) == []


def test_load_accepts_utf8_bom_and_korean(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"a": "한글"}, ensure_ascii=False).encode("utf-8"))
    assert data.load(tmp_path, "x.json", None) == {"a": "한글"}


def test_load_reports_broken_json_with_file_name(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.json").write_text("{ 깨진 json", encoding="utf-8")
    with pytest.raises(DataError, match="x.json"):
        data.load(tmp_path, "x.json", None)


# ---- 후기

def test_valid_text_review_passes(root):
    data.validate_reviews([text_review()], root)


@pytest.mark.parametrize("key", ["headline", "body", "person", "meta", "badge", "source", "goal"])
def test_missing_required_field_names_the_item_and_field(root, key):
    item = text_review()
    del item[key]
    with pytest.raises(DataError, match=r"r1.*%s" % key):
        data.validate_reviews([item], root)


def test_duplicate_id_and_unknown_goal_and_unknown_kind(root):
    with pytest.raises(DataError, match="중복"):
        data.validate_reviews([text_review(), text_review()], root)
    with pytest.raises(DataError, match="goal"):
        data.validate_reviews([text_review(goal=["nope"])], root)
    with pytest.raises(DataError, match="kind"):
        data.validate_reviews([text_review(kind="video")], root)


def test_featured_only_for_text_reviews(root):
    data.validate_reviews([text_review(featured=True)], root)
```

- [ ] **Step 2: 렌더 테스트 작성** — `tests/test_render.py`

```python
import re

import pytest

from site_build import render


def text_review(**over):
    item = {"id": "r1", "kind": "text", "goal": ["degree", "license"], "source": "테스트", "featured": True,
            "headline": '"한 줄 <mark>제목</mark>"', "body": "본문 <strong>강조</strong>",
            "person": "김○○ 님 (30대)", "meta": "직장인 / 학사", "badge": "학사 학위"}
    item.update(over)
    return item


@pytest.fixture
def root(tmp_path):
    return tmp_path


# ---- 글 후기

def test_text_card_keeps_authored_html_but_escapes_plain_fields(root):
    html = render.reviews_grid([text_review(person='김"○○ <님> & (30대)', meta="a<b", badge="x&y")], root)
    assert "<mark>제목</mark>" in html and "<strong>강조</strong>" in html      # 제목·본문은 HTML 허용
    assert "김&quot;○○ &lt;님&gt; &amp; (30대)" in html                         # 나머지는 이스케이프
    assert "a&lt;b" in html and "x&amp;y" in html
    assert html.count('class="pr-star"') == 5


def test_text_card_joins_goals_and_uses_first_char_as_avatar(root):
    html = render.reviews_grid([text_review()], root)
    assert 'data-cat="degree license"' in html
    assert '<div class="pr-av">김</div>' in html


def test_empty_data_renders_nothing(root):
    assert render.reviews_grid([], root) == ""
    assert render.reviews_featured([]) == ""


def test_filters_show_only_goals_that_exist_in_fixed_order():
    items = [text_review(goal=["transfer"]), text_review(id="r2", goal=["degree"])]
    html = render.reviews_filters(items)
    assert re.findall(r'data-filter="(\w+)"', html) == ["all", "degree", "transfer"]
    assert "대학원" not in html


def test_featured_uses_main_prefix_and_skips_non_featured(root):
    items = [text_review(), text_review(id="r2", featured=False, person="이○○ 님")]
    html = render.reviews_featured(items)
    assert html.count('class="es5-card"') == 1 and "이○○" not in html and "data-cat" not in html
```

- [ ] **Step 3: 실패 확인**

```bash
python -m pytest tests/test_data.py tests/test_render.py -q
```
Expected: FAIL — `ImportError: cannot import name 'data' from 'site_build'`

- [ ] **Step 4: `site_build/data.py` 구현**

```python
"""data/*.json 읽기와 검증. 규칙에 어긋나면 DataError로 어디가 문제인지 알려준다."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .core import BuildError

GOALS = ("degree", "license", "transfer", "grad")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
AS_OF_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


class DataError(BuildError):
    """데이터 파일의 내용이 규칙에 맞지 않을 때."""


def load(root: Path, name: str, default: Any) -> Any:
    path = root / "data" / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_bytes().decode("utf-8-sig"))   # 메모장이 붙이는 BOM도 허용
    except json.JSONDecodeError as exc:
        raise DataError("%s: JSON 형식 오류 (%s)" % (name, exc)) from exc


def _require(item: Mapping, keys: Sequence[str], where: str) -> None:
    for key in keys:
        value = item.get(key)
        if value is None or (isinstance(value, (str, list, dict)) and not value):
            raise DataError("%s: 필수 항목 '%s'이(가) 없거나 비어 있습니다" % (where, key))


def _exists(root: Path, rel: str, where: str, key: str) -> None:
    if not (root / rel).is_file():
        raise DataError("%s: '%s'에 적힌 파일이 없습니다: %s" % (where, key, rel))


# ---------------------------------------------------------------- 후기 (reviews.json)

def _check_text(item, root, where, team_ids) -> None:
    _require(item, ["headline", "body", "person", "meta", "badge"], where)


KIND_CHECKS = {"text": _check_text}


def validate_reviews(items: Sequence[Mapping], root: Path, team_ids=frozenset()) -> None:
    ids, slugs = set(), set()
    for item in items:
        where = "reviews.json[%s]" % item.get("id", "?")
        _require(item, ["id", "kind", "goal", "source"], where)
        if item["id"] in ids:
            raise DataError("%s: id가 중복됩니다" % where)
        ids.add(item["id"])
        bad = [g for g in item["goal"] if g not in GOALS]
        if bad:
            raise DataError("%s: 알 수 없는 goal %s (허용: %s)" % (where, bad, ", ".join(GOALS)))
        check = KIND_CHECKS.get(item["kind"])
        if check is None:
            raise DataError("%s: 알 수 없는 kind '%s' (허용: %s)" % (where, item["kind"], ", ".join(KIND_CHECKS)))
        if item.get("featured") and item["kind"] != "text":
            raise DataError("%s: featured는 글 후기(text)에만 쓸 수 있습니다" % where)
        check(item, root, where, team_ids)
        if "slug" in item:
            if item["slug"] in slugs:
                raise DataError("%s: slug '%s'이(가) 중복됩니다" % (where, item["slug"]))
            slugs.add(item["slug"])
```

- [ ] **Step 5: `site_build/render.py` 구현 (후기 부분)**

```python
"""데이터(JSON)를 HTML 조각으로 바꾸는 함수들."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Mapping, Sequence

GOAL_ORDER = ["degree", "license", "transfer", "grad"]
GOAL_LABELS = {"degree": "학위 취득", "license": "자격증", "transfer": "편입", "grad": "대학원"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


# =============================================================== 후기·합격 사례

def _text_card(item: Mapping, p: str, with_cat: bool, ind: str) -> str:
    """글 후기 카드. p는 CSS 접두어('pr' 후기 페이지, 'es5' 메인)."""
    cat = ' data-cat="%s"' % esc(" ".join(item["goal"])) if with_cat else ""
    i1, i2 = ind + "  ", ind + "    "
    stars = "".join('<div class="%s-star"></div>' % p for _ in range(5))
    lines = [
        '%s<div class="%s-card"%s>' % (ind, p, cat),
        '%s<div class="%s-quote-bg">"</div>' % (i1, p),
        '%s<div class="%s-stars">%s</div>' % (i1, p, stars),
        '%s<p class="%s-headline">%s</p>' % (i1, p, item["headline"]),
        '%s<p class="%s-text">%s</p>' % (i1, p, item["body"]),
        '%s<div class="%s-div"></div>' % (i1, p),
        '%s<div class="%s-foot">' % (i1, p),
        '%s<div class="%s-av">%s</div>' % (i2, p, esc(item["person"][0])),
        '%s<div><p class="%s-name">%s</p><p class="%s-meta">%s</p></div>' % (
            i2, p, esc(item["person"]), p, esc(item["meta"])),
        '%s<span class="%s-badge">%s</span>' % (i2, p, esc(item["badge"])),
        '%s</div>' % i1,
        '%s</div>' % ind,
    ]
    return "\n".join(lines)


def _text_card_pr(item, root, ind):
    return _text_card(item, "pr", True, ind)


CARD_RENDERERS = {"text": _text_card_pr}


def reviews_grid(items: Sequence[Mapping], root: Path) -> str:
    cards = [CARD_RENDERERS[it["kind"]](it, root, "        ") for it in items]
    if not cards:
        return ""
    return "\n\n" + "\n\n".join(cards) + "\n\n      "


def reviews_filters(items: Sequence[Mapping]) -> str:
    present = {g for it in items for g in it["goal"]}
    chips = ['        <button class="pr-chip on" type="button" data-filter="all">전체</button>']
    for g in GOAL_ORDER:
        if g in present:
            chips.append('        <button class="pr-chip" type="button" data-filter="%s">%s</button>' % (g, GOAL_LABELS[g]))
    return "\n" + "\n".join(chips) + "\n      "


def reviews_featured(items: Sequence[Mapping]) -> str:
    cards = [_text_card(it, "es5", False, "      ") for it in items if it.get("featured")]
    if not cards:
        return ""
    return "\n\n" + "\n\n".join(cards) + "\n\n    "
```

- [ ] **Step 6: 통과 확인**

```bash
python -m pytest tests/test_data.py tests/test_render.py -q
```
Expected: `18 passed`

- [ ] **Step 7: 일회성 이전 스크립트 — 기존 카드 6개를 data/reviews.json으로, 조각을 토큰으로**

`tools/migrate_reviews.py` (이전이 끝나면 **커밋하지 않고 삭제**한다)
```python
"""일회성: 기존 후기 페이지·메인 후기 섹션의 카드 6개를 data/reviews.json으로 옮기고 조각을 토큰으로 바꾼다."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from site_build.core import read_text, write_text  # noqa: E402

SOURCE = "아임웹 사이트에 게시되던 수강생 후기를 정리한 것 (사용자 확인 2026-10-12)"


def replace_div_inner(text: str, open_tag: str, token: str) -> str:
    """open_tag로 시작하는 <div>의 안쪽을 {{token}}으로 바꾼다(div 중첩을 세어 짝을 찾는다)."""
    start = text.index(open_tag)
    pos = start + len(open_tag)
    depth = 1
    for m in re.finditer(r"<div\b|</div>", text[pos:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return text[:pos] + "{{%s}}" % token + text[pos + m.start():]
    raise ValueError("짝이 맞는 </div>를 찾지 못함: " + open_tag)


page = ROOT / "pages/reviews/01-main-content.html"
text = read_text(page)
CARD = re.compile(
    r'<div class="pr-card" data-cat="([^"]*)">.*?<p class="pr-headline">(.*?)</p>\s*'
    r'<p class="pr-text">(.*?)</p>.*?<p class="pr-name">(.*?)</p><p class="pr-meta">(.*?)</p></div>\s*'
    r'<span class="pr-badge">(.*?)</span>', re.S)
reviews = [{"id": "r%02d" % n, "kind": "text", "goal": m.group(1).split(), "featured": True,
            "headline": m.group(2), "body": m.group(3), "person": m.group(4), "meta": m.group(5),
            "badge": m.group(6), "source": SOURCE}
           for n, m in enumerate(CARD.finditer(text), 1)]
assert len(reviews) == 6, "후기 카드 6개를 찾지 못했습니다: %d" % len(reviews)

(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data/reviews.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

text = replace_div_inner(text, '<div class="pr-grid" id="pr-grid">', "reviews_grid")
text = replace_div_inner(text, '<div class="pr-filter" id="pr-filter">', "reviews_filters")
write_text(page, text)

main = ROOT / "sections/05-reviews.html"
write_text(main, replace_div_inner(read_text(main), '<div class="es5-grid">', "reviews_featured"))
print("옮긴 후기:", len(reviews))
```

```bash
python tools/migrate_reviews.py
git diff --stat
```
Expected: `옮긴 후기: 6`, `data/reviews.json` 생성, `pages/reviews/01-main-content.html`·`sections/05-reviews.html`만 수정됨.

- [ ] **Step 8: `site_build/site.py`를 후기 토큰까지 연결하고, golden 비교를 공백 무시로 전환**

`site_build/site.py`
```python
"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path

from . import data, render


def load_site(root: Path):
    reviews = data.load(root, "reviews.json", [])
    data.validate_reviews(reviews, root)
    tokens = {
        "reviews_grid": render.reviews_grid(reviews, root),
        "reviews_filters": render.reviews_filters(reviews),
        "reviews_featured": render.reviews_featured(reviews),
    }
    return tokens, []
```

`tests/test_golden.py`에서 한 줄 수정:
```python
LOOSE = {"index.html", "pages/reviews/index.html"}
```

- [ ] **Step 9: 화면이 이전과 같은지 확인 (이전 전후 동일성)**

```bash
rm tools/migrate_reviews.py
python build.py
python -m pytest -q
git status --short
```
Expected: `build done`, 전체 테스트 통과(`test_golden` 포함). `git status`에서 생성물(`index.html`, `pages/reviews/index.html`)이 `M`이면 **공백만 달라진 것**이어야 한다. 확인: `git diff -w --stat index.html pages/reviews/index.html`에서 변경이 사실상 없음(공백 제외 diff가 비어 있거나 줄바꿈 위치뿐).

- [ ] **Step 10: 커밋**

```bash
git add site_build data tests pages/reviews/01-main-content.html sections/05-reviews.html index.html pages/reviews/index.html build.py
git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit -m "$(cat <<'EOF'
Move existing reviews into data/reviews.json and render cards from data

후기 페이지와 메인 후기 섹션을 {{토큰}}으로 바꾸고 기존 6개 후기를 데이터로 이전. 화면은 이전과 동일

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: 팀 소개 데이터화 (경력 목록 추가 가능)

**Files:**
- Create: `data/team.json`
- Modify: `site_build/data.py`, `site_build/render.py`, `site_build/site.py`, `pages/team/01-main-content.html`, `tests/test_data.py`, `tests/test_render.py`, `tests/test_golden.py`

**Interfaces:**
- Consumes: Task 3의 `data._require`, `data._exists`, `render.esc`
- Produces: `data.validate_team(items, root) -> set[str]`(팀 id 집합), `render.team_cards(team, rel="../../", cases_by_planner=None)`, `render.team_extras(team, cases_by_planner=None)`, 토큰 `team_cards`·`team_extras`

- [ ] **Step 1: 테스트 추가**

`tests/test_data.py` 끝에 추가:
```python
# ---- 팀

def team_member(**over):
    item = {"id": "t1", "name": "홍길동 담당자", "role": "학위 · 편입 전문 플래너", "photo": "assets/p.jpg",
            "bio": "소개", "tags": ["편입"]}
    item.update(over)
    return item


def test_team_valid_returns_ids_and_checks_photo(root):
    assert data.validate_team([team_member()], root) == {"t1"}
    with pytest.raises(DataError, match="photo"):
        data.validate_team([team_member(photo="assets/none.jpg")], root)
    with pytest.raises(DataError, match="career"):
        data.validate_team([team_member(career=["ok", ""])], root)
    with pytest.raises(DataError, match="중복"):
        data.validate_team([team_member(), team_member()], root)
```

`tests/test_render.py` 끝에 추가:
```python
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
    assert "pt-mem-career" not in html and "pt-mem-cases" not in html
    assert render.team_extras([member()]) == ""


def test_team_card_shows_career_and_case_links():
    cases = {"t1": [{"slug": "a-2026", "title": "A대 합격"}, {"slug": "b-2026", "title": "B대 합격"}]}
    html = render.team_cards([member(career=["경력 5년", "사회복지사 2급"])], cases_by_planner=cases)
    assert html.count("<li>") == 2
    assert 'href="/pages/reviews/a-2026/"' in html and "B대 합격" in html
    assert "pt-mem-career" in render.team_extras([member(career=["경력"])])
    assert render.team_extras([member()], cases) != ""
```

```bash
python -m pytest tests/test_data.py tests/test_render.py -q
```
Expected: FAIL — `AttributeError: module 'site_build.data' has no attribute 'validate_team'`

- [ ] **Step 2: `site_build/data.py` 끝에 추가**

```python


# ---------------------------------------------------------------- 팀 (team.json)

def validate_team(items: Sequence[Mapping], root: Path) -> set:
    ids = set()
    for item in items:
        where = "team.json[%s]" % item.get("id", "?")
        _require(item, ["id", "name", "role", "photo", "bio", "tags"], where)
        if item["id"] in ids:
            raise DataError("%s: id가 중복됩니다" % where)
        ids.add(item["id"])
        _exists(root, item["photo"], where, "photo")
        career = item.get("career", [])
        if not isinstance(career, list) or not all(isinstance(c, str) and c for c in career):
            raise DataError("%s: career는 비어 있지 않은 문자열 목록이어야 합니다" % where)
    return ids
```

- [ ] **Step 3: `site_build/render.py` 끝에 추가**

```python


# =============================================================== 팀

TEAM_EXTRAS_CSS = """<style>
.pt-mem-career{list-style:none;margin:0 0 1.25rem;padding:0;}
.pt-mem-career li{font-size:14px;color:#4a5a6a;line-height:1.8;padding-left:14px;position:relative;}
.pt-mem-career li::before{content:'';position:absolute;left:0;top:.8em;width:5px;height:5px;border-radius:50%;background:#4a7fa5;}
.pt-mem-cases{font-size:14px;color:#6b7f93;margin:0 0 1.25rem;line-height:1.8;}
.pt-mem-cases a{color:#4a7fa5;font-weight:700;margin-right:8px;}
</style>"""


def team_cards(team: Sequence[Mapping], rel: str = "../../", cases_by_planner: Mapping = None) -> str:
    cases_by_planner = cases_by_planner or {}
    ind = "        "
    cards = []
    for m in team:
        i1, i2, i3 = ind + "  ", ind + "    ", ind + "      "
        lines = [
            '%s<!-- %s -->' % (ind, esc(m["name"])),
            '%s<div class="pt-mem-card">' % ind,
            '%s<div class="pt-mem-photo">' % i1,
            '%s<img src="%s%s" alt="%s">' % (i2, rel, esc(m["photo"]), esc(m["name"])),
            '%s</div>' % i1,
            '%s<div class="pt-mem-body">' % i1,
            '%s<p class="pt-mem-name">%s</p>' % (i2, esc(m["name"])),
            '%s<p class="pt-mem-role">%s</p>' % (i2, esc(m["role"])),
            '%s<p class="pt-mem-desc">%s</p>' % (i2, m["bio"]),
        ]
        career = m.get("career") or []
        if career:
            lines.append('%s<ul class="pt-mem-career">' % i2)
            lines += ['%s<li>%s</li>' % (i3, esc(c)) for c in career]
            lines.append('%s</ul>' % i2)
        linked = cases_by_planner.get(m["id"]) or []
        if linked:
            links = "".join('<a href="/pages/reviews/%s/">%s</a>' % (esc(c["slug"]), esc(c["title"])) for c in linked[:3])
            lines.append('%s<p class="pt-mem-cases">합격 사례 · %s</p>' % (i2, links))
        lines.append('%s<div class="pt-mem-tags">' % i2)
        lines += ['%s<span class="pt-mem-tag">%s</span>' % (i3 + "  ", esc(t)) for t in m["tags"]]
        lines += ['%s</div>' % i2, '%s</div>' % i1, '%s</div>' % ind]
        cards.append("\n".join(lines))
    if not cards:
        return ""
    return "\n\n" + "\n\n".join(cards) + "\n\n      "


def team_extras(team: Sequence[Mapping], cases_by_planner: Mapping = None) -> str:
    """경력 목록이나 합격 사례 링크가 하나라도 있을 때만 필요한 CSS."""
    if any(m.get("career") for m in team) or any(cases_by_planner or {}):
        return TEAM_EXTRAS_CSS
    return ""
```

```bash
python -m pytest tests/test_data.py tests/test_render.py -q
```
Expected: `21 passed`

- [ ] **Step 4: 일회성 이전 스크립트 — 담당자 4명을 data/team.json으로**

`tools/migrate_team.py` (끝나면 **삭제, 커밋하지 않음**)
```python
"""일회성: 팀 페이지의 담당자 카드 4개를 data/team.json으로 옮기고 조각을 토큰으로 바꾼다."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from site_build.core import read_text, write_text  # noqa: E402


def replace_div_inner(text: str, open_tag: str, token: str) -> str:
    start = text.index(open_tag)
    pos = start + len(open_tag)
    depth = 1
    for m in re.finditer(r"<div\b|</div>", text[pos:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return text[:pos] + "{{%s}}" % token + text[pos + m.start():]
    raise ValueError("짝이 맞는 </div>를 찾지 못함: " + open_tag)


page = ROOT / "pages/team/01-main-content.html"
text = read_text(page)
TEAM = re.compile(
    r'<!-- (.*?) -->\s*<div class="pt-mem-card">.*?<img src="\.\./\.\./(.*?)" alt="(.*?)">.*?'
    r'<p class="pt-mem-name">(.*?)</p>\s*<p class="pt-mem-role">(.*?)</p>\s*<p class="pt-mem-desc">(.*?)</p>\s*'
    r'<div class="pt-mem-tags">(.*?)</div>', re.S)
team = []
for m in TEAM.finditer(text):
    photo = m.group(2)
    team.append({"id": re.search(r"team-(.*?)\.jpg", photo).group(1), "name": m.group(4), "role": m.group(5),
                 "photo": photo, "bio": m.group(6), "tags": re.findall(r'<span class="pt-mem-tag">(.*?)</span>', m.group(7))})
assert len(team) == 4, "담당자 카드 4개를 찾지 못했습니다: %d" % len(team)

(ROOT / "data/team.json").write_text(json.dumps(team, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
text = replace_div_inner(text, '<div class="pt-mem-grid">', "team_cards")
write_text(page, text.rstrip("\n") + "\n\n{{team_extras}}\n")
print("옮긴 담당자:", [t["id"] for t in team])
```

```bash
python tools/migrate_team.py
```
Expected: `옮긴 담당자: ['sanghuigyeong', 'leejeongmin', 'seongseoa', 'hongsihyeon']`

- [ ] **Step 5: `site_build/site.py` 갱신, golden에 팀 페이지 추가**

`site_build/site.py`
```python
"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path

from . import data, render


def load_site(root: Path):
    team = data.load(root, "team.json", [])
    team_ids = data.validate_team(team, root)
    reviews = data.load(root, "reviews.json", [])
    data.validate_reviews(reviews, root, team_ids)
    tokens = {
        "reviews_grid": render.reviews_grid(reviews, root),
        "reviews_filters": render.reviews_filters(reviews),
        "reviews_featured": render.reviews_featured(reviews),
        "team_cards": render.team_cards(team, "../../"),
        "team_extras": render.team_extras(team),
    }
    return tokens, []
```

`tests/test_golden.py`에서:
```python
LOOSE = {"index.html", "pages/reviews/index.html", "pages/team/index.html"}
```

- [ ] **Step 6: 이전 전후 동일성 확인 후 커밋**

```bash
rm tools/migrate_team.py
python build.py
python -m pytest -q
git diff -w --stat pages/team/index.html
```
Expected: 전체 통과. `pages/team/index.html`의 공백 제외 diff가 비어 있다(팀 페이지 화면은 이전과 같다).

```bash
git add site_build data tests pages/team/01-main-content.html pages/team/index.html
git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit -m "$(cat <<'EOF'
Move team members into data/team.json (optional career list)

팀 페이지 담당자 카드를 데이터에서 만들고, 경력 목록·합격 사례 링크를 선택 항목으로 지원. 화면은 이전과 동일

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: 대화 캡처 · 합격 사례 카드, 사례 상세 페이지, 확대 보기

**Files:**
- Create: `site_build/cases.py`, `tests/test_cases.py`
- Modify: `site_build/data.py`, `site_build/render.py`, `site_build/site.py`, `pages/reviews/01-main-content.html`, `tests/test_data.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: Task 3 `CARD_RENDERERS`, `KIND_CHECKS`, `data._require`/`_exists`; Task 4 `validate_team`의 id 집합, `team_cards(..., cases_by_planner)`; Task 1 `ExtraPage`, `Inline`
- Produces: `data.SLUG_RE`, `render.url_path(rel)`, `render.image_size(root, rel)`, `render.reviews_extras(items, root)`(토큰 `reviews_extras`), `cases.case_html(item, planner, root)`, `cases.case_page(item, team_by_id, root) -> ExtraPage`

- [ ] **Step 1: 데이터 테스트 추가** — `tests/test_data.py` 끝에

```python
# ---- 캡처·합격 사례

def case(**over):
    item = {"id": "k1", "kind": "case", "goal": ["transfer"], "source": "테스트", "slug": "univ-a-2026",
            "title": "A대 편입 합격", "school": "A대학교", "track": "일반편입", "duration": "8개월",
            "profile": {"age": "20대", "background": "전문대 졸업", "credits": "80학점"},
            "plan": [{"label": "1학기", "detail": "전공 18학점"}], "result": "합격",
            "planner": "t1", "seoDescription": "설명"}
    item.update(over)
    return item


def test_capture_requires_existing_image(root):
    ok = {"id": "c1", "kind": "capture", "goal": ["license"], "source": "테스트", "image": "assets/cap.jpg",
          "alt": "캡처", "person": "이○○ 님"}
    data.validate_reviews([ok], root)
    with pytest.raises(DataError, match="파일이 없습니다"):
        data.validate_reviews([dict(ok, image="assets/none.jpg")], root)


def test_case_valid_and_planner_must_exist(root):
    data.validate_reviews([case()], root, {"t1"})
    with pytest.raises(DataError, match="planner"):
        data.validate_reviews([case()], root, {"other"})


@pytest.mark.parametrize("slug", ["Univ-A", "univ a", "대학교", "a_b", "-a", "a--b", "index.html"])
def test_bad_slug_is_rejected(root, slug):
    with pytest.raises(DataError, match="slug"):
        data.validate_reviews([case(slug=slug)], root, {"t1"})


def test_duplicate_slug_is_rejected(root):
    with pytest.raises(DataError, match="slug.*중복"):
        data.validate_reviews([case(), case(id="k2")], root, {"t1"})


def test_featured_is_rejected_for_cases(root):
    with pytest.raises(DataError, match="featured"):
        data.validate_reviews([case(featured=True)], root, {"t1"})


def test_case_missing_proof_image_is_rejected(root):
    with pytest.raises(DataError, match="proofImages"):
        data.validate_reviews([case(proofImages=["assets/none.jpg"])], root, {"t1"})
```

- [ ] **Step 2: 렌더 테스트 추가·수정** — `tests/test_render.py`

맨 위 import에 `from PIL import Image`를 추가하고, 기존 `root` fixture를 아래로 **교체**한다.
```python
@pytest.fixture
def root(tmp_path):
    (tmp_path / "assets" / "proof").mkdir(parents=True)
    Image.new("RGB", (600, 900), "white").save(tmp_path / "assets" / "proof" / "한글 파일.jpg")
    Image.new("RGB", (300, 300), "white").save(tmp_path / "assets" / "p.jpg")
    return tmp_path
```
`test_empty_data_renders_nothing`에 두 줄을 추가한다.
```python
    assert render.reviews_extras([], root) == ""
    assert render.reviews_extras([text_review()], root) == ""
```
파일 끝에 추가:
```python
# ---- 캡처·합격 사례

def capture(**over):
    item = {"id": "c1", "kind": "capture", "goal": ["transfer"], "source": "테스트",
            "image": "assets/proof/한글 파일.jpg", "alt": '대화 <캡처> & "인용"', "person": "홍○○ 님", "period": "2026.09"}
    item.update(over)
    return item


def test_capture_card_encodes_path_escapes_alt_and_lazy_loads(root):
    html = render.reviews_grid([capture()], root)
    assert 'src="/assets/proof/%ED%95%9C%EA%B8%80%20%ED%8C%8C%EC%9D%BC.jpg"' in html     # 한글·공백 인코딩
    assert 'alt="대화 &lt;캡처&gt; &amp; &quot;인용&quot;"' in html
    assert 'width="600" height="900"' in html and 'loading="lazy"' in html
    assert "홍○○ 님 · 2026.09" in html and "편입" in html


def test_capture_without_period_shows_only_name(root):
    html = render.reviews_grid([capture(period=None)], root)
    assert "홍○○ 님" in html and "None" not in html


def case(**over):
    item = {"id": "k1", "kind": "case", "goal": ["transfer"], "source": "테스트", "slug": "univ-a-2026",
            "title": "A대 <편입> 합격", "school": "A대학교", "track": "일반편입", "duration": "8개월",
            "profile": {"age": "20대", "background": "전문대 졸업", "credits": "80학점"},
            "plan": [{"label": "1학기", "detail": "전공 18학점"}], "result": "최종 합격",
            "planner": "t1", "seoDescription": "설명"}
    item.update(over)
    return item


def test_case_card_links_to_detail_page_and_escapes(root):
    html = render.reviews_grid([case()], root)
    assert 'href="/pages/reviews/univ-a-2026/"' in html
    assert "A대 &lt;편입&gt; 합격" in html and "A대학교 · 일반편입" in html
    assert "20대 · 전문대 졸업 · 8개월" in html


def test_extras_appear_only_when_needed(root):
    assert "pr-lb" in render.reviews_extras([capture()], root)
    assert "pr-case-badge" in render.reviews_extras([case()], root)


def test_url_path_quotes_unicode_and_spaces():
    assert render.url_path("assets/한 글.jpg") == "/assets/%ED%95%9C%20%EA%B8%80.jpg"
    assert render.url_path("/assets/a.jpg") == "/assets/a.jpg"
```

- [ ] **Step 3: 사례 페이지 테스트 작성** — `tests/test_cases.py`

```python
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
```

```bash
python -m pytest tests/test_data.py tests/test_render.py tests/test_cases.py -q
```
Expected: FAIL — `AttributeError ... 'reviews_extras'` 등

- [ ] **Step 4: `site_build/data.py` — 캡처·사례 검사 추가**

`KIND_CHECKS = {"text": _check_text}` 줄을 아래 블록으로 **교체**한다.
```python
def _check_capture(item, root, where, team_ids) -> None:
    _require(item, ["image", "alt", "person"], where)
    _exists(root, item["image"], where, "image")


def _check_case(item, root, where, team_ids) -> None:
    _require(item, ["slug", "title", "school", "track", "profile", "plan", "duration", "result",
                    "planner", "seoDescription"], where)
    if not SLUG_RE.match(item["slug"]):
        raise DataError("%s: slug '%s'은(는) 영문 소문자·숫자·하이픈만 쓸 수 있습니다 (예: konkuk-transfer-2026)" % (where, item["slug"]))
    _require(item["profile"], ["age", "background", "credits"], where + ".profile")
    for row in item["plan"]:
        _require(row, ["label", "detail"], where + ".plan")
    if item["planner"] not in team_ids:
        raise DataError("%s: planner '%s'이(가) team.json에 없습니다" % (where, item["planner"]))
    for rel in item.get("proofImages", []):
        _exists(root, rel, where, "proofImages")


KIND_CHECKS = {"text": _check_text, "capture": _check_capture, "case": _check_case}
```

- [ ] **Step 5: `site_build/render.py` — 캡처·사례 카드, 확대 보기, 경로 도우미**

파일 맨 위 import 블록을 아래로 **교체**한다.
```python
import html
import urllib.parse
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image
```
`esc` 함수 바로 아래에 추가:
```python
def url_path(rel: str) -> str:
    """저장소 안의 파일 경로를 사이트 주소(/로 시작, 한글·공백은 퍼센트 인코딩)로 바꾼다."""
    return "/" + urllib.parse.quote(rel.lstrip("/"))


def image_size(root: Path, rel: str) -> tuple:
    with Image.open(root / rel) as im:
        return im.size
```
`CARD_RENDERERS = {"text": _text_card_pr}` 줄을 아래로 **교체**한다.
```python
def _capture_card(item, root, ind):
    i1, i2 = ind + "  ", ind + "    "
    w, h = image_size(root, item["image"])
    src = url_path(item["image"])
    who = "%s · %s" % (item["person"], item["period"]) if item.get("period") else item["person"]
    lines = [
        '%s<figure class="pr-card pr-cap" data-cat="%s">' % (ind, esc(" ".join(item["goal"]))),
        '%s<button class="pr-cap-btn" type="button" data-full="%s" aria-label="%s 크게 보기">' % (i1, src, esc(item["alt"])),
        '%s<img src="%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async">' % (i2, src, esc(item["alt"]), w, h),
        '%s</button>' % i1,
        '%s<figcaption class="pr-cap-info"><span class="pr-cap-tag">%s</span><span class="pr-cap-who">%s</span></figcaption>' % (
            i1, esc(GOAL_LABELS[item["goal"][0]]), esc(who)),
        '%s</figure>' % ind,
    ]
    return "\n".join(lines)


def _case_card(item, root, ind):
    i1 = ind + "  "
    meta = " · ".join(esc(v) for v in (item["profile"]["age"], item["profile"]["background"], item["duration"]))
    lines = [
        '%s<a class="pr-card pr-case" data-cat="%s" href="/pages/reviews/%s/">' % (ind, esc(" ".join(item["goal"])), esc(item["slug"])),
        '%s<span class="pr-case-badge">합격 사례</span>' % i1,
        '%s<p class="pr-case-title">%s</p>' % (i1, esc(item["title"])),
        '%s<p class="pr-case-sub">%s · %s</p>' % (i1, esc(item["school"]), esc(item["track"])),
        '%s<p class="pr-case-result">%s</p>' % (i1, esc(item["result"])),
        '%s<p class="pr-case-meta">%s</p>' % (i1, meta),
        '%s<span class="pr-case-more">사례 자세히 보기 →</span>' % i1,
        '%s</a>' % ind,
    ]
    return "\n".join(lines)


CARD_RENDERERS = {"text": _text_card_pr, "capture": _capture_card, "case": _case_card}
```
`reviews_featured` 함수 아래에 추가:
```python
REVIEWS_EXTRAS_CSS = """<style>
.pr-cap{padding:0;margin:0;overflow:hidden;border-radius:22px;background:#fff;border:1px solid rgba(74,127,165,.1);display:flex;flex-direction:column;}
.pr-cap-btn{display:block;width:100%;padding:0;border:0;background:#eef3f8;cursor:zoom-in;}
.pr-cap-btn img{display:block;width:100%;height:auto;}
.pr-cap-info{display:flex;align-items:center;gap:10px;padding:14px 18px;}
.pr-cap-tag{background:#1a2d4a;color:#a0cde0;font-size:12px;font-weight:700;padding:5px 11px;border-radius:7px;white-space:nowrap;}
.pr-cap-who{font-size:13px;color:#8a9ab0;}
.pr-case,.pr-case:hover{text-decoration:none;color:inherit;}
.pr-case-badge{align-self:flex-start;background:#4a7fa5;color:#fff;font-size:12px;font-weight:700;padding:5px 12px;border-radius:7px;margin-bottom:1.1rem;position:relative;z-index:1;}
.pr-case-title{font-size:clamp(18px,2vw,22px);font-weight:900;color:#1a2d4a;line-height:1.4;margin:0 0 .5rem;letter-spacing:-.02em;position:relative;z-index:1;}
.pr-case-sub{font-size:14px;color:#4a7fa5;font-weight:700;margin:0 0 1rem;position:relative;z-index:1;}
.pr-case-result{font-size:15px;line-height:1.9;color:#4a5a6a;margin:0 0 auto;padding-bottom:1.25rem;position:relative;z-index:1;}
.pr-case-meta{font-size:13px;color:#8a9ab0;margin:0 0 1rem;position:relative;z-index:1;}
.pr-case-more{font-size:14px;font-weight:700;color:#4a7fa5;position:relative;z-index:1;}
.pr-lb{position:fixed;inset:0;z-index:10000;background:rgba(10,20,40,.88);display:none;align-items:center;justify-content:center;padding:4vh 4vw;}
.pr-lb.open{display:flex;}
.pr-lb img{max-width:100%;max-height:92vh;border-radius:10px;background:#fff;}
.pr-lb-x{position:absolute;top:14px;right:18px;background:none;border:0;color:#fff;font-size:36px;line-height:1;cursor:pointer;}
</style>
<div class="pr-lb" id="pr-lb" role="dialog" aria-modal="true" aria-label="이미지 크게 보기"><button class="pr-lb-x" type="button" aria-label="닫기">&times;</button><img alt=""></div>
<script>
(function(){
  var lb=document.getElementById('pr-lb'); if(!lb) return;
  var img=lb.querySelector('img');
  function close(){ lb.classList.remove('open'); img.removeAttribute('src'); }
  document.addEventListener('click',function(e){
    var b=e.target.closest('.pr-cap-btn');
    if(b){ img.src=b.getAttribute('data-full'); img.alt=b.getAttribute('aria-label')||''; lb.classList.add('open'); return; }
    if(e.target===lb || e.target.closest('.pr-lb-x')) close();
  });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') close(); });
})();
</script>"""


def reviews_extras(items: Sequence[Mapping], root: Path) -> str:
    """캡처·합격 사례 카드가 있을 때만 필요한 CSS와 확대 보기(라이트박스)."""
    if all(it["kind"] == "text" for it in items):
        return ""
    return REVIEWS_EXTRAS_CSS
```

- [ ] **Step 6: `site_build/cases.py` 작성**

```python
"""합격 사례 상세 페이지."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .core import ExtraPage, Inline
from .render import esc, image_size, url_path

CASE_CSS = """<style>
.pc{width:100%;background:#fff;font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;}
.pc-hero{background:#1a2d4a;padding:80px 6% 70px;text-align:center;}
.pc-back{display:inline-block;color:#afd0e8;font-size:14px;margin-bottom:1.6rem;}
.pc-badge{display:inline-block;background:rgba(107,157,189,.18);border:1px solid rgba(107,157,189,.35);color:#afd0e8;padding:8px 18px;border-radius:100px;font-size:14px;font-weight:500;margin:0 0 1.4rem;}
.pc-hero h1{font-size:clamp(2.6rem,4.6vw,4rem);font-weight:900;letter-spacing:-.04em;line-height:1.25;color:#fff;margin:0 0 1rem;}
.pc-sub{font-size:clamp(15px,1.8vw,19px);color:rgba(255,255,255,.65);margin:0;}
.pc-sec{padding:70px 6%;}
.pc-sec.alt{background:#f7f9fb;}
.pc-in{max-width:860px;margin:0 auto;}
.pc-h2{font-size:clamp(2rem,2.8vw,2.6rem);font-weight:900;letter-spacing:-.03em;color:#1a2d4a;margin:0 0 1.5rem;}
.pc-table{width:100%;border-collapse:collapse;background:#fff;border:1px solid rgba(74,127,165,.15);border-radius:12px;overflow:hidden;}
.pc-table th,.pc-table td{padding:16px 20px;text-align:left;font-size:15px;line-height:1.8;border-bottom:1px solid rgba(74,127,165,.1);vertical-align:top;}
.pc-table th{width:30%;background:#eef3f8;color:#1a2d4a;font-weight:700;}
.pc-table tr:last-child th,.pc-table tr:last-child td{border-bottom:0;}
.pc-result{font-size:clamp(17px,2vw,20px);line-height:2;color:#1a2d4a;font-weight:700;margin:0;}
.pc-proof{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1.25rem;margin:0;padding:0;}
.pc-proof figure{margin:0;border:1px solid rgba(74,127,165,.15);border-radius:14px;overflow:hidden;background:#fff;}
.pc-proof img{display:block;width:100%;height:auto;}
.pc-planner{display:flex;gap:20px;align-items:center;background:#fff;border:1px solid rgba(74,127,165,.15);border-radius:16px;padding:20px;color:inherit;}
.pc-planner img{width:84px;height:84px;border-radius:50%;object-fit:cover;object-position:center top;flex-shrink:0;}
.pc-planner b{display:block;font-size:18px;color:#1a2d4a;}
.pc-planner span{font-size:14px;color:#4a7fa5;font-weight:600;}
.pc-cta{background:#1a2d4a;padding:80px 6%;text-align:center;}
.pc-cta p{color:rgba(255,255,255,.6);font-size:17px;margin:0 0 2rem;}
.pc-cta .pc-cta-t{font-size:clamp(2.2rem,3.6vw,3rem);font-weight:900;color:#fff;letter-spacing:-.04em;margin:0 0 1rem;}
.pc-cta a{display:inline-block;background:#4a7fa5;color:#fff;font-weight:700;font-size:17px;padding:18px 44px;border-radius:10px;}
.pc-cta a:hover{background:#6b9dbd;}
@media(max-width:560px){.pc-hero{padding:60px 5% 50px;}.pc-sec{padding:50px 5%;}.pc-table th,.pc-table td{display:block;width:100%;padding:12px 16px;}.pc-table th{border-bottom:0;padding-bottom:4px;}}
</style>"""


def case_html(item: Mapping, planner: Mapping, root: Path) -> str:
    profile = item["profile"]
    prof_rows = [("연령대", profile["age"]), ("전적 학력", profile["background"]),
                 ("보유 학점", profile["credits"]), ("소요 기간", item["duration"])]
    prof = "\n".join("<tr><th>%s</th><td>%s</td></tr>" % (esc(k), esc(v)) for k, v in prof_rows)
    plan = "\n".join("<tr><th>%s</th><td>%s</td></tr>" % (esc(r["label"]), esc(r["detail"])) for r in item["plan"])
    proof = ""
    if item.get("proofImages"):
        figs = []
        for rel in item["proofImages"]:
            w, h = image_size(root, rel)
            figs.append('<figure><img src="%s" alt="%s 인증 자료" width="%d" height="%d" loading="lazy" decoding="async"></figure>'
                        % (url_path(rel), esc(item["title"]), w, h))
        proof = ('<div class="pc-sec"><div class="pc-in"><h2 class="pc-h2">인증 자료</h2>'
                 '<div class="pc-proof">%s</div></div></div>' % "".join(figs))
    return (
        CASE_CSS + '\n<div class="pc">\n'
        '<div class="pc-hero"><a class="pc-back" href="/pages/reviews/">← 후기·합격 사례 전체 보기</a><br>'
        '<span class="pc-badge">합격 사례</span><h1>%s</h1><p class="pc-sub">%s · %s</p></div>\n'
        '<div class="pc-sec alt"><div class="pc-in"><h2 class="pc-h2">수강생 프로필</h2><table class="pc-table">%s</table></div></div>\n'
        '<div class="pc-sec"><div class="pc-in"><h2 class="pc-h2">설계한 학점 계획</h2><table class="pc-table">%s</table></div></div>\n'
        '<div class="pc-sec alt"><div class="pc-in"><h2 class="pc-h2">결과</h2><p class="pc-result">%s</p></div></div>\n'
        '%s\n'
        '<div class="pc-sec"><div class="pc-in"><h2 class="pc-h2">담당 플래너</h2>'
        '<a class="pc-planner" href="/pages/team/"><img src="%s" alt="%s"><div><b>%s</b><span>%s</span></div></a></div></div>\n'
        '<div class="pc-cta"><p class="pc-cta-t">나도 이런 결과를 만들고 싶다면</p><p>내 상황에 맞는 학점 계획을 1:1로 설계해 드립니다.</p>'
        '<a href="/#es-form">1:1 무료 상담 신청 →</a></div>\n</div>'
        % (esc(item["title"]), esc(item["school"]), esc(item["track"]), prof, plan, esc(item["result"]), proof,
           url_path(planner["photo"]), esc(planner["name"]), esc(planner["name"]), esc(planner["role"])))


def case_page(item: Mapping, team_by_id: Mapping, root: Path) -> ExtraPage:
    slug = item["slug"]
    return ExtraPage(
        rel_dir="pages/reviews/%s" % slug,
        title=item.get("seoTitle") or "%s | 에듀솔루션" % item["title"],
        desc=item["seoDescription"],
        url_path="/pages/reviews/%s/" % slug,
        parts=[root / "sections" / "00-nav.html",
               Inline(case_html(item, team_by_id[item["planner"]], root)),
               root / "sections" / "09-kakao-float-button.html",
               root / "sections" / "10-diagnostic-popup.html"],
    )
```

- [ ] **Step 7: `site_build/site.py` 갱신, 후기 페이지 조각에 토큰 추가**

`site_build/site.py`
```python
"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path

from . import data, render
from .cases import case_page


def load_site(root: Path):
    team = data.load(root, "team.json", [])
    team_ids = data.validate_team(team, root)
    reviews = data.load(root, "reviews.json", [])
    data.validate_reviews(reviews, root, team_ids)

    cases = [r for r in reviews if r["kind"] == "case"]
    cases_by_planner = {}
    for c in cases:
        cases_by_planner.setdefault(c["planner"], []).append(c)

    tokens = {
        "reviews_grid": render.reviews_grid(reviews, root),
        "reviews_filters": render.reviews_filters(reviews),
        "reviews_featured": render.reviews_featured(reviews),
        "reviews_extras": render.reviews_extras(reviews, root),
        "team_cards": render.team_cards(team, "../../", cases_by_planner),
        "team_extras": render.team_extras(team, cases_by_planner),
    }
    team_by_id = {m["id"]: m for m in team}
    return tokens, [case_page(c, team_by_id, root) for c in cases]
```

`pages/reviews/01-main-content.html` 맨 끝(마지막 `</div>` 다음 줄)에 한 줄 추가:
```
{{reviews_extras}}
```
(앞에 빈 줄 하나. 출력에서 토큰이 빈 문자열이 되어 화면이 바뀌지 않는다.)

- [ ] **Step 8: 통과 확인, 필터 JS 호환 확인**

```bash
python -m pytest -q
python build.py
git diff -w --stat pages/reviews/index.html
```
Expected: 전체 통과, `pages/reviews/index.html` 공백 제외 diff 없음. 후기 페이지의 필터 스크립트(`pages/reviews/02-animations.html`)는 `#pr-grid .pr-card`의 `data-cat`만 보므로 캡처·사례 카드(`pr-card` 클래스 + `data-cat`)와 그대로 호환된다. 이 호환성은 Task 9의 브라우저 확인에서 한 번 더 본다.

- [ ] **Step 9: 커밋**

```bash
git add site_build tests pages/reviews/01-main-content.html pages/reviews/index.html
git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit -m "$(cat <<'EOF'
Add capture and case review kinds with case detail pages

- 대화 캡처 카드(확대 보기, lazy 로딩, 한글 파일명 인코딩)와 합격 사례 카드
- /pages/reviews/<slug>/ 상세 페이지 자동 생성, sitemap 자동 반영
- slug 형식·중복, planner 참조, 이미지 존재 검증

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: 메인 실적 수치 띠와 사업자 정보 푸터

**Files:**
- Create: `sections/11-stats-strip.html`, `sections/12-footer.html`
- Modify: `site_build/data.py`, `site_build/render.py`, `site_build/site.py`, `site_build/core.py`, `tests/test_data.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: Task 5 `render.esc`
- Produces: `data.validate_stats(items)`, `data.validate_business(biz)`, `render.stats_strip(stats)`, `render.site_footer(business)`, 토큰 `stats_strip`·`site_footer`

- [ ] **Step 1: 테스트 추가**

`tests/test_data.py` 끝에:
```python
# ---- 수치

def stat(**over):
    item = {"value": 1200, "label": "누적 수강생", "asOf": "2026-10", "source": "자체 집계"}
    item.update(over)
    return item


def test_stats_require_source_and_as_of(root):
    data.validate_stats([stat(), stat(asOf="2026-10-12", value=4.9)])
    for key in ("source", "asOf", "label", "value"):
        item = stat()
        del item[key]
        with pytest.raises(DataError, match=key):
            data.validate_stats([item])
    with pytest.raises(DataError, match="asOf"):
        data.validate_stats([stat(asOf="올해")])
    with pytest.raises(DataError, match="value"):
        data.validate_stats([stat(value="천이백")])
    with pytest.raises(DataError, match="value"):
        data.validate_stats([stat(value=True)])
    with pytest.raises(DataError, match="최대 6개"):
        data.validate_stats([stat() for _ in range(7)])


# ---- 사업자 정보

def test_business_optional_but_checked_when_present():
    data.validate_business({})
    data.validate_business({"company": "에듀", "ceo": "홍", "regno": "000-00-00000", "address": "서울"})
    with pytest.raises(DataError, match="regno"):
        data.validate_business({"company": "에듀", "ceo": "홍", "address": "서울"})
    with pytest.raises(DataError, match="label"):
        data.validate_business({"company": "에듀", "ceo": "홍", "regno": "1", "address": "서울", "reports": [{"value": "x"}]})
```

`tests/test_render.py` 끝에:
```python
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
```

```bash
python -m pytest tests/test_data.py tests/test_render.py -q
```
Expected: FAIL — `AttributeError: ... 'validate_stats'`

- [ ] **Step 2: `site_build/data.py` 끝에 추가**

```python


# ---------------------------------------------------------------- 실적 수치 (stats.json)

def validate_stats(items: Sequence[Mapping]) -> None:
    if len(items) > 6:
        raise DataError("stats.json: 수치는 최대 6개까지 쓸 수 있습니다 (현재 %d개)" % len(items))
    for n, item in enumerate(items, 1):
        where = "stats.json[%d]" % n
        _require(item, ["value", "label", "asOf", "source"], where)
        value = item["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise DataError("%s: value는 0 이상의 숫자여야 합니다" % where)
        if not AS_OF_RE.match(item["asOf"]):
            raise DataError("%s: asOf는 '2026-10' 또는 '2026-10-12' 형식이어야 합니다" % where)


# ---------------------------------------------------------------- 사업자 정보 (business.json)

def validate_business(biz: Mapping) -> None:
    if not biz:
        return
    _require(biz, ["company", "ceo", "regno", "address"], "business.json")
    for rep in biz.get("reports", []):
        _require(rep, ["label", "value"], "business.json.reports")
```

- [ ] **Step 3: `site_build/render.py` 끝에 추가**

```python


# =============================================================== 메인: 실적 수치 띠, 푸터

STATS_CSS = """<style>
.est{width:100%;background:#fff;border-bottom:1px solid rgba(14,31,61,.09);font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;}
.est-in{max-width:1100px;margin:0 auto;padding:44px 6%;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:2rem;text-align:center;}
.est-main{margin:0 0 6px;font-size:clamp(2.4rem,4vw,3.4rem);font-weight:900;letter-spacing:-.03em;color:#1a2d4a;line-height:1.2;}
.est-s{font-size:.55em;color:#4a7fa5;margin-left:3px;}
.est-label{margin:0 0 4px;font-size:16px;font-weight:700;color:#1a2d4a;}
.est-note{margin:0;font-size:12px;color:#8a9ab0;line-height:1.6;}
</style>"""

STATS_JS = """<script>
(function(){
  var els=document.querySelectorAll('.est-n[data-count]'); if(!els.length||!('IntersectionObserver' in window)) return;
  if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  function fmt(v,dec){ return dec?v.toFixed(1):Math.floor(v).toLocaleString(); }
  var io=new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if(!e.isIntersecting) return; io.unobserve(e.target);
      var el=e.target, target=parseFloat(el.getAttribute('data-count')), dec=String(target).indexOf('.')!==-1, t0=null;
      function step(ts){ if(!t0) t0=ts; var p=Math.min((ts-t0)/1600,1), ease=1-Math.pow(1-p,4);
        el.textContent=p<1?fmt(ease*target,dec):fmt(target,dec); if(p<1) requestAnimationFrame(step); }
      requestAnimationFrame(step);
    });
  },{threshold:.5});
  els.forEach(function(el){ io.observe(el); });
})();
</script>"""


def _fmt_number(value) -> str:
    if isinstance(value, float) and not value.is_integer():
        return "%.1f" % value
    return "{:,}".format(int(value))


def stats_strip(stats: Sequence[Mapping]) -> str:
    if not stats:
        return ""
    items = []
    for s in stats:
        suffix = '<span class="est-s">%s</span>' % esc(s["suffix"]) if s.get("suffix") else ""
        items.append(
            '    <div class="est-item">\n'
            '      <p class="est-main"><span class="est-n" data-count="%s">%s</span>%s</p>\n'
            '      <p class="est-label">%s</p>\n'
            '      <p class="est-note">%s 기준 · %s</p>\n'
            '    </div>' % (s["value"], _fmt_number(s["value"]), suffix, esc(s["label"]),
                            esc(s["asOf"].replace("-", ".")), esc(s["source"])))
    return (STATS_CSS + '\n<div class="est">\n  <div class="est-in">\n' + "\n".join(items) +
            "\n  </div>\n</div>\n" + STATS_JS)


FOOTER_CSS = """<style>
.esf{width:100%;background:#13213a;font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;}
.esf-in{max-width:1100px;margin:0 auto;padding:44px 6% 120px;}
.esf-name{margin:0 0 14px;font-size:17px;font-weight:900;color:#fff;}
.esf-list{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px 22px;}
.esf-list li{font-size:13px;line-height:1.8;color:rgba(255,255,255,.55);}
.esf-list b{color:rgba(255,255,255,.8);font-weight:700;margin-right:6px;}
.esf-copy{margin:18px 0 0;font-size:12px;color:rgba(255,255,255,.35);}
</style>"""


def site_footer(business: Mapping) -> str:
    if not business:
        return ""
    rows = [("대표자", business["ceo"]), ("사업자등록번호", business["regno"])]
    for rep in business.get("reports", []):
        rows.append((rep["label"], rep["value"]))
    for key, label in (("phone", "연락처"), ("email", "이메일")):
        if business.get(key):
            rows.append((label, business[key]))
    rows.append(("주소", business["address"]))
    lis = "\n".join('      <li><b>%s</b>%s</li>' % (esc(k), esc(v)) for k, v in rows)
    return (FOOTER_CSS + '\n<footer class="esf">\n  <div class="esf-in">\n    <p class="esf-name">%s</p>\n'
            '    <ul class="esf-list">\n%s\n    </ul>\n    <p class="esf-copy">&copy; %s. All rights reserved.</p>\n'
            '  </div>\n</footer>' % (esc(business["company"]), lis, esc(business["company"])))
```

- [ ] **Step 4: 조각 파일 두 개 만들기, core 조각 순서에 연결**

`sections/11-stats-strip.html` — 내용은 이 한 줄 (끝 개행 없음):
```
{{stats_strip}}
```
`sections/12-footer.html` — 내용은 이 한 줄 (끝 개행 없음):
```
{{site_footer}}
```

`site_build/core.py`에서 `MAIN_FRAGMENTS`를 아래로 **교체**한다(수치 띠는 히어로 바로 아래, 푸터는 상담폼 다음).
```python
MAIN_FRAGMENTS = [
    "sections/00-nav.html",
    "sections/01-hero-image.html",
    "sections/11-stats-strip.html",
    "sections/02-hero-navy-features.html",
    "sections/03-service-grid.html",
    "sections/04-caution-compare.html",
    "sections/05-reviews.html",
    "sections/06-consult-form.html",
    "sections/12-footer.html",
    "sections/09-kakao-float-button.html",
    "sections/10-diagnostic-popup.html",
    "sections/08-form-label-fix.html",
    "sections/07-animations.html",
]
```
같은 파일의 `sub_parts` 반환 목록을 아래로 **교체**한다(본문 다음에 푸터).
```python
    return [
        base / "00-nav.html",
        base / "01-main-content.html",
        root / "sections" / "12-footer.html",
        root / "sections" / "09-kakao-float-button.html",
        root / "sections" / "10-diagnostic-popup.html",
        base / "02-animations.html",
    ]
```
`site_build/cases.py`의 `case_page`에서 `parts` 목록을 아래로 **교체**한다(사례 상세에도 푸터).
```python
        parts=[root / "sections" / "00-nav.html",
               Inline(case_html(item, team_by_id[item["planner"]], root)),
               root / "sections" / "12-footer.html",
               root / "sections" / "09-kakao-float-button.html",
               root / "sections" / "10-diagnostic-popup.html"],
```

- [ ] **Step 5: `site_build/site.py` 갱신**

```python
"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path

from . import data, render
from .cases import case_page


def load_site(root: Path):
    team = data.load(root, "team.json", [])
    team_ids = data.validate_team(team, root)
    reviews = data.load(root, "reviews.json", [])
    data.validate_reviews(reviews, root, team_ids)
    stats = data.load(root, "stats.json", [])
    data.validate_stats(stats)
    business = data.load(root, "business.json", {})
    data.validate_business(business)

    cases = [r for r in reviews if r["kind"] == "case"]
    cases_by_planner = {}
    for c in cases:
        cases_by_planner.setdefault(c["planner"], []).append(c)

    tokens = {
        "reviews_grid": render.reviews_grid(reviews, root),
        "reviews_filters": render.reviews_filters(reviews),
        "reviews_featured": render.reviews_featured(reviews),
        "reviews_extras": render.reviews_extras(reviews, root),
        "team_cards": render.team_cards(team, "../../", cases_by_planner),
        "team_extras": render.team_extras(team, cases_by_planner),
        "stats_strip": render.stats_strip(stats),
        "site_footer": render.site_footer(business),
    }
    team_by_id = {m["id"]: m for m in team}
    return tokens, [case_page(c, team_by_id, root) for c in cases]
```

- [ ] **Step 6: 통과 확인 — 데이터가 없는 지금은 모든 페이지가 이전과 같아야 한다**

```bash
python -m pytest -q
python build.py
git diff -w --stat -- index.html pages sitemap.xml
```
Expected: 전체 통과(`test_golden` 포함 — `stats.json`·`business.json`이 없으므로 수치 띠·푸터가 빈 조각이라 출력에서 사라진다). 생성물의 공백 제외 diff가 없다.

- [ ] **Step 7: 커밋**

```bash
git add site_build sections/11-stats-strip.html sections/12-footer.html tests
git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit -m "$(cat <<'EOF'
Add stats strip and business-info footer (empty until data is provided)

수치는 source·asOf 필수, 사업자 정보는 필수 항목 검증. 데이터가 없으면 조각이 출력에서 사라져 기존 페이지는 그대로

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: 링크 검사기, README, 스펙 정리

**Files:**
- Create: `tools/check_links.py`, `tests/test_links.py`, `tests/test_site_links.py`
- Modify: `README.md`, `docs/superpowers/specs/2026-10-12-trust-content-design.md`

**Interfaces:**
- Produces: `tools.check_links.check(site_root: Path, extra_roots=()) -> list[str]`, CLI `python tools/check_links.py`

- [ ] **Step 1: 검사기 테스트 작성** — `tests/test_links.py`

```python
from tools.check_links import check


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_reports_missing_file_and_missing_anchor_but_not_good_links(tmp_path):
    write(tmp_path / "index.html", '<div id="top"></div><a href="/pages/a/">ok</a><a href="#top">ok</a>'
          '<a href="/pages/a/#sec">ok</a><a href="/pages/none/">깨짐</a><a href="#nope">깨짐</a>'
          '<img src="/assets/x.png"><a href="https://example.com/">외부</a><a href="mailto:a@b.c">메일</a>')
    write(tmp_path / "pages/a/index.html", '<div id="sec"></div>')
    write(tmp_path / "assets/x.png", "x")
    problems = check(tmp_path)
    assert len(problems) == 2
    assert any("/pages/none/" in p for p in problems) and any("#nope" in p for p in problems)


def test_percent_encoded_paths_are_resolved_and_extra_roots_are_searched(tmp_path):
    site, repo = tmp_path / "site", tmp_path / "repo"
    write(site / "index.html", '<img src="/assets/한글%20파일.jpg"><a href="/pages/x/#sec">link</a>')
    write(repo / "assets/한글 파일.jpg", "x")
    write(repo / "pages/x/index.html", '<div id="sec"></div>')
    assert check(site, extra_roots=[repo]) == []
    assert len(check(site)) == 2


def test_relative_links_resolve_from_the_page_folder(tmp_path):
    write(tmp_path / "pages/a/index.html", '<img src="../../assets/logo.png"><a href="../b/">b</a>')
    write(tmp_path / "pages/b/index.html", "")
    write(tmp_path / "assets/logo.png", "x")
    assert check(tmp_path) == []
```

```bash
python -m pytest tests/test_links.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.check_links'`

- [ ] **Step 2: 검사기 구현** — `tools/check_links.py`

```python
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
    pages = [p for p in site_root.rglob("*.html") if p.name in ("index.html", "404.html")]
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
```

```bash
python -m pytest tests/test_links.py -q
```
Expected: `3 passed`

- [ ] **Step 3: 실제 사이트 전체를 매번 검사하는 테스트** — `tests/test_site_links.py`

```python
from pathlib import Path

from site_build.core import build_all
from site_build.site import load_site
from tools.check_links import check

ROOT = Path(__file__).resolve().parent.parent


def test_built_site_has_no_broken_internal_links(tmp_path):
    tokens, extra = load_site(ROOT)
    build_all(ROOT, tmp_path, tokens, extra)
    assert check(tmp_path, extra_roots=[ROOT]) == []
```

```bash
python -m pytest -q
```
Expected: 전체 통과

- [ ] **Step 4: README에 운영 방법 추가** — `README.md` 끝에 아래 섹션을 추가한다.

```markdown
## 후기·합격 사례·수치·사업자 정보 관리 (data/)

내용은 `data/*.json`에 적고 `python build.py`를 실행하면 페이지와 sitemap이 함께 만들어집니다. 규칙에 어긋나면 어디가 문제인지 알려 주며 빌드가 멈춥니다.

| 파일 | 내용 |
|---|---|
| `data/reviews.json` | 후기·합격 사례. `kind`: `text`(글 후기) / `capture`(대화 캡처) / `case`(합격 사례, 상세 페이지 자동 생성) |
| `data/stats.json` | 메인 실적 수치 띠(최대 6개). `value`, `label`, `asOf`(기준 시점), `source`(근거)가 모두 필수 |
| `data/team.json` | 담당자 정보. `career`(경력·자격 목록)는 선택 |
| `data/business.json` | 하단 사업자 정보. 없으면 푸터가 나오지 않습니다 |

**대화 캡처·인증 이미지 올리는 순서**
1. 원본을 `raw-proof/`에 둡니다(git에 올라가지 않습니다).
2. 이름·연락처·프로필 사진 위치를 확인하고 `python tools/mask.py raw-proof/원본.png assets/proof/결과.jpg --box x,y,w,h` 로 가립니다(여러 곳은 `--box`를 반복).
3. 결과 이미지를 직접 열어 개인정보가 가려졌는지 확인한 뒤에만 `reviews.json`에 추가합니다.

**확인 명령**: `python -m pytest -q` (테스트), `python tools/check_links.py` (링크·이미지 검사)
```

- [ ] **Step 5: 스펙을 구현에 맞게 정리** — `docs/superpowers/specs/2026-10-12-trust-content-design.md`

아래 세 곳을 고친다.
1. `stats.json 항목` 줄: `` `value`, `label`, `asOf`(기준 시점), `source`(근거). 둘 중 하나라도 비면 빌드 실패. `` → `` `value`(숫자), `suffix`(선택, 예: `명+`), `label`, `asOf`(기준 시점), `source`(근거). `label`·`asOf`·`source` 중 하나라도 비면 빌드 실패. ``
2. `team.json 항목` 줄: `` `id`, `name`, `role`, `photo`, `bio`(기존 소개 문구 그대로), `tags`, `career`(경력·자격), `field`(담당 분야). `` → `` `id`, `name`, `role`, `photo`, `bio`(기존 소개 문구 그대로), `tags`, `career`(선택, 경력·자격 목록). 담당 분야는 기존 `role`과 `tags`로 표현한다. ``
3. 메인 화면 항목의 `` (4칸, 기준 시점·근거를 작은 글씨로 표기, 기존 카운트업 애니메이션 재사용) `` → `` (최대 6칸, 기준 시점·근거를 작은 글씨로 표기. 기존 카운트업 함수는 대상 섹션(`.es2`)이 사라져 쓰이지 않으므로 수치 띠 전용 카운트업 스크립트를 함께 출력) ``

- [ ] **Step 6: 커밋**

```bash
python -m pytest -q
git add tools/check_links.py tests/test_links.py tests/test_site_links.py README.md docs/superpowers/specs
git -c user.name="MYCOM" -c user.email="gr9665@gmail.com" commit -m "$(cat <<'EOF'
Add link checker, document data workflow, sync spec with implementation

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: 콘텐츠 투입 (사용자 자료가 필요한 단계)

> 이 Task는 **사용자가 주는 실제 자료**로만 진행한다. 값을 추측하거나 지어내지 않는다. 필요한 자료가 아직 없으면 해당 항목을 건너뛰고 Task 9로 가도 사이트는 정상이다(빈 데이터는 화면에 나오지 않는다).

**Files:**
- Modify: `data/business.json`(생성), `data/stats.json`(생성), `data/team.json`, `data/reviews.json`, `tests/golden/**`
- Create: `assets/proof/*.jpg`

각 항목은 "자료 받기 → 파일 작성 → 빌드·테스트 → 화면 확인 → 커밋" 순서이며, **항목마다 따로 커밋**한다.

- [ ] **Step 1: 사업자 정보** — 사용자에게 상호, 대표자, 사업자등록번호, 신고번호(있는 것), 연락처, 주소를 받아 `data/business.json`을 만든다. 형식:
```json
{
  "company": "(상호)",
  "ceo": "(대표자)",
  "regno": "(사업자등록번호)",
  "reports": [{"label": "(신고 종류)", "value": "(신고번호)"}],
  "phone": "(연락처)",
  "address": "(주소)"
}
```
`reports`·`phone`·`email`은 없으면 항목째 뺀다. 필요한 표기 항목은 사업 형태에 따라 다르므로 사용자와 확인한다. 이 중괄호 안의 `(…)`는 형식 설명이며 값으로 커밋하면 안 된다.

- [ ] **Step 2: 실적 수치** — 수치마다 값, 단위, 기준 시점, 근거를 받아 `data/stats.json`을 만든다. 형식:
```json
[
  {"value": 0, "suffix": "(단위)", "label": "(항목 이름)", "asOf": "YYYY-MM", "source": "(근거)"}
]
```
근거가 없다고 하면 그 수치는 넣지 않는다.

- [ ] **Step 3: 담당자 이력** — 담당자별 경력·자격을 받아 `data/team.json`의 해당 항목에 `"career": ["…", "…"]`을 추가한다.

- [ ] **Step 4: 후기·인증 이미지 가림** — 이미지마다 다음을 반복한다.
  1. 원본을 `raw-proof/`에 둔다.
  2. 이미지를 열어 이름·연락처·프로필 사진·계정명 위치를 찾아 좌표(`x,y,w,h`, 원본 픽셀)를 정한다.
  3. `python tools/mask.py raw-proof/<원본> assets/proof/<결과>.jpg --box x,y,w,h ...`
  4. 결과 이미지를 열어 **가려진 것을 눈으로 확인**한다. 사용자에게도 결과를 보여 주고 승인받은 것만 사용한다.

- [ ] **Step 5: 후기·사례 항목 추가** — 승인된 이미지와 자료로 `data/reviews.json`에 항목을 추가한다. `source`에는 자료의 출처(예: 수강생 동의 받은 카카오톡 대화, 날짜)를 적는다. 형식:
```json
{"id": "(고유 id)", "kind": "capture", "goal": ["transfer"], "period": "YYYY.MM", "person": "김○○ 님",
 "image": "assets/proof/(파일).jpg", "alt": "(이미지 설명)", "source": "(출처)"}
```
```json
{"id": "(고유 id)", "kind": "case", "goal": ["transfer"], "slug": "(영문-소문자-하이픈)",
 "title": "(제목)", "school": "(학교)", "track": "(전형)", "duration": "(기간)",
 "profile": {"age": "(연령대)", "background": "(전적 학력)", "credits": "(보유 학점)"},
 "plan": [{"label": "(학기 등)", "detail": "(내용)"}],
 "result": "(결과 한 줄)", "planner": "(team.json의 id)", "seoDescription": "(검색 결과 설명 문장)",
 "proofImages": ["assets/proof/(파일).jpg"], "source": "(출처)"}
```

- [ ] **Step 6: 빌드·검증·기준본 갱신** — 항목을 추가할 때마다:
```bash
python build.py
python -m pytest -q
python tools/check_links.py
```
Expected: `build done`, 모든 테스트 통과, `링크 문제 0건`. 데이터를 넣어 화면이 바뀌므로 `test_golden`이 실패하면 **변경이 의도한 것인지 화면으로 확인**한 뒤에만 `python tests/snapshot_golden.py`로 기준본을 갱신하고 `pytest`를 다시 돌린다.

- [ ] **Step 7: 항목별 커밋** — 예: `git add data/business.json sections tests/golden && git commit -m "Add business info footer data"`

---

### Task 9: 최종 점검과 반영 (사용자 승인 후)

**Files:** (코드 변경 없음, 점검과 배포)

- [ ] **Step 1: 전체 검증**

```bash
python build.py
python -m pytest -q
python tools/check_links.py
git status --short
```
Expected: `build done`, 전체 통과, `링크 문제 0건`, 작업 폴더 깨끗함.

- [ ] **Step 2: 로컬에서 PC·태블릿·모바일 확인** — `python -m http.server 8777`로 띄우고 브라우저에서 `/`, `/pages/reviews/`, 사례 상세 한 곳, `/pages/team/`을 폭 1280·768·375로 연다. 확인할 것: 가로 스크롤 없음, 필터 버튼이 캡처·사례 카드에도 동작, 캡처 클릭 시 확대/Esc·바깥 클릭으로 닫힘, 수치 띠 카운트업, 푸터가 우측 하단 카카오·진단 버튼에 가리지 않음, 상담 버튼이 메인 폼으로 이동. 확인이 끝나면 서버를 끈다.

- [ ] **Step 3: 사용자 승인** — 스크린샷과 변경 요약을 보여 주고, master에 합쳐도 되는지 **명시적으로 승인**을 받는다. 승인 전에는 다음 단계로 가지 않는다.

- [ ] **Step 4: 반영**

```bash
git checkout master
git merge --ff-only site-trust
git push origin master
```
`--ff-only`가 실패하면(master가 앞서 있으면) 중단하고 상황을 보고한다.

- [ ] **Step 5: 배포 확인**

```bash
gh api repos/gr9665-spec/edusolution-landing/pages/builds/latest --jq .status
```
`built`가 되면 `https://edu-solution.co.kr/`, `/pages/reviews/`, 사례 상세, `/sitemap.xml`을 `curl -s -o /dev/null -w "%{http_code}"`로 확인한다. Expected: 모두 200.

- [ ] **Step 6: 사용자에게 안내할 후속 작업** — (1) Cloudflare 대시보드의 Caching → Purge Everything, (2) 네이버 서치어드바이저·구글 서치콘솔에 새 sitemap 제출과 새 사례 페이지 색인 요청.

---

## 자체 검토 결과

- **스펙 대응**: 데이터 구조(3.1) → Task 3·4·5·6, 빌드(3.2) → Task 1, 화면(3.3) → Task 3·4·5·6, 가림 도구(4) → Task 2, 작업 순서·검증(5) → Task 1~9, 사용자 자료(6) → Task 8, 범위 밖(7) → Global Constraints.
- **스펙과 다르게 한 곳**(Task 7에서 스펙을 고침): 카운트업은 기존 함수가 대상 섹션을 잃어 쓰이지 않으므로 수치 띠 전용으로 새로 만듦, `team.json`의 `field`는 기존 `role`·`tags`로 대체.
- **타입·이름 일관성**: `validate_reviews(items, root, team_ids)`, `reviews_grid(items, root)`, `team_cards(team, rel, cases_by_planner)`, `team_extras(team, cases_by_planner)`, `ExtraPage/Inline`, 토큰 8종(`reviews_grid`, `reviews_filters`, `reviews_featured`, `reviews_extras`, `team_cards`, `team_extras`, `stats_strip`, `site_footer`)이 Task 간에 같다.
