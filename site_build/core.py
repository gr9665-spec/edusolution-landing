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
    """데이터에서 만들어지는 추가 페이지(예: 후기 상세)."""
    rel_dir: str            # 예: "pages/reviews/univ-a"
    title: str
    desc: str
    url_path: str           # 예: "/pages/reviews/univ-a/"
    parts: Sequence[Part]
    logo: str = "/assets/logo.png"
    og_image: str = ""      # 공유 미리보기 이미지(전체 주소). 비어 있으면 사이트 기본 이미지


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


def make_head(title: str, desc: str, url_path: str, head_extra: str, og_image: str = "") -> str:
    return HEAD.substitute(
        title=html.escape(title, quote=True),
        desc=html.escape(desc, quote=True),
        site=SITE,
        path=url_path,
        og_image=html.escape(og_image or OG_IMAGE, quote=True),
    ) + head_extra + "</head>\n<body>\n"


def assemble_page(root: Path, tokens: Mapping[str, str], logo: str, title: str, desc: str,
                  url_path: str, parts: Sequence[Part], og_image: str = "") -> str:
    out = [make_head(title, desc, url_path, read_text(root / "head-extra.html"), og_image)]
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
        root / "sections" / "12-footer.html",
        root / "sections" / "09-kakao-float-button.html",
        root / "sections" / "10-diagnostic-popup.html",
        base / "02-animations.html",
    ]


PRUNED_SECTIONS = ("reviews", "education-info")      # 데이터로 상세 페이지가 만들어지는 폴더(후기, 교육정보 글)


def prune_stale_post_pages(out: Path, extra_pages: Sequence[ExtraPage]) -> None:
    """데이터에서 지운 후기·교육정보 글의 상세 페이지가 공개 폴더에 남지 않게 지운다."""
    keep = {page.rel_dir for page in extra_pages}
    for section in PRUNED_SECTIONS:
        base = out / "pages" / section
        if not base.is_dir():
            continue
        for folder in base.iterdir():
            index = folder / "index.html"
            if folder.is_dir() and index.is_file() and ("pages/%s/%s" % (section, folder.name)) not in keep:
                index.unlink()
                try:
                    folder.rmdir()      # 다른 파일이 들어 있으면 폴더는 남긴다
                except OSError:
                    pass


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
            root, tokens, page.logo, page.title, page.desc, page.url_path, page.parts, page.og_image))

    prune_stale_post_pages(out, extra_pages)

    for folder, target in REDIRECTS.items():
        write_text(out / folder / "index.html", REDIRECT.substitute(site=SITE, target=target))

    paths = SITEMAP_PATHS + [p.url_path for p in extra_pages]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += ["  <url><loc>%s%s</loc></url>" % (SITE, p) for p in paths]
    sitemap.append("</urlset>")
    write_text(out / "sitemap.xml", "\n".join(sitemap) + "\n")

    write_text(out / "robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)
