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
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="48x48" href="/assets/icon-48.png">
<link rel="icon" type="image/png" sizes="96x96" href="/assets/icon-96.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/icon-192.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">
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
    "sections/13-org-schema.html",
    "sections/09-kakao-float-button.html",
    "sections/10-diagnostic-popup.html",
    "sections/08-form-label-fix.html",
    "sections/07-animations.html",
]

# (폴더, 제목, 설명)
SUBPAGES = [
    ("team", "학점은행제 전문 플래너 팀 소개 | 에듀솔루션",
     "학점은행제 학위·편입·대학원·자격증을 1:1로 설계하는 에듀솔루션 전문 플래너 팀을 소개합니다. 담당자별 전문 분야와 카카오톡·전화 상담 방법을 확인하세요."),
    ("credit-bank", "학점은행제란? 제도 개요·목표·진행 절차 | 에듀솔루션",
     "학점은행제란 무엇인지 쉽게 설명합니다. 전문학사 80학점·학사 140학점 학위 조건, 진행 절차 4단계, 자주 묻는 질문을 한눈에 정리했습니다."),
    ("education-info", "학점은행제 교육정보 | 학위·자격증·편입·대학원 | 에듀솔루션",
     "학위 취득, 사회복지사 2급, 보육교사 2급, 기사·산업기사 응시자격, 편입, 대학원까지 목표별 조건과 과정, 학위 신청 일정 등 학점은행제 정보 글을 모았습니다."),
    ("reviews", "학점은행제 수강생 후기 | 에듀솔루션",
     "학위 취득, 자격증, 편입 등 목표별로 학점은행제 에듀솔루션 수강생의 실제 후기를 모았습니다. 과정과 담당자 관리 경험을 확인해 보세요."),
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
    lastmod: str = ""       # 사이트맵에 적을 수정일(YYYY-MM-DD). 비어 있으면 적지 않는다


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
    head_extra = expand(read_text(root / "head-extra.html"), {"analytics_head": "", **tokens}, "head-extra.html")
    out = [make_head(title, desc, url_path, head_extra, og_image)]
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


def sitemap_entries(extra_pages: Sequence[ExtraPage]) -> list:
    """(주소, 수정일) 목록. 수정일은 데이터에 날짜가 있는 글·후기만 적고, 그 글들을 모아 보여 주는 목록 페이지는 가장 최근 날짜를 쓴다."""
    def latest(prefix: str) -> str:
        return max((p.lastmod for p in extra_pages if p.lastmod and p.url_path.startswith(prefix)), default="")
    index_mod = {"/": latest("/pages/"), "/pages/education-info/": latest("/pages/education-info/"),
                 "/pages/reviews/": latest("/pages/reviews/")}
    return [(path, index_mod.get(path, "")) for path in SITEMAP_PATHS] + [(p.url_path, p.lastmod) for p in extra_pages]


def llms_txt(extra_pages: Sequence[ExtraPage]) -> str:
    """AI 에이전트용 사이트 안내(llms.txt). 페이지 목록은 빌드 데이터에서 만들어 글을 더해도 어긋나지 않는다."""
    def clean(title: str) -> str:
        return title.replace(" | 에듀솔루션", "").strip()

    lines = ["# 에듀솔루션", "",
             "> 학점은행제 전문 플래너 팀 에듀솔루션의 공식 사이트입니다. 학위 취득, 자격증, 편입, 대학원 진학 목표에 맞는 수강 플랜을 1:1로 설계해 드리고, 상담은 무료입니다.", "",
             "## 주요 페이지", "",
             "- [%s](%s/): %s" % (clean(MAIN_TITLE), SITE, MAIN_DESC)]
    lines += ["- [%s](%s/pages/%s/): %s" % (clean(title), SITE, folder, desc) for folder, title, desc in SUBPAGES]
    articles = [p for p in extra_pages if p.url_path.startswith("/pages/education-info/")]
    if articles:
        lines += ["", "## 교육정보 글", ""]
        lines += ["- [%s](%s%s): %s" % (clean(p.title), SITE, p.url_path, p.desc) for p in articles]
    lines += ["", "## 기타", "", "- [사이트맵](%s/sitemap.xml)" % SITE, "",
              "## 이용 조건", "", "상업적 이용과 연구 목적 이용을 허용합니다. 학점은행제 규정·일정은 개정될 수 있으니 각 글의 출처와 기준 시점을 함께 확인해 주세요.", ""]
    return "\n".join(lines)


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

    entries = sitemap_entries(extra_pages)
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += ["  <url><loc>%s%s</loc>%s</url>" % (SITE, path, "<lastmod>%s</lastmod>" % mod if mod else "")
                for path, mod in entries]
    sitemap.append("</urlset>")
    write_text(out / "sitemap.xml", "\n".join(sitemap) + "\n")

    write_text(out / "llms.txt", llms_txt(extra_pages))
    write_text(out / "robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)
