"""후기 상세 페이지."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .core import SITE, ExtraPage, Inline
from .render import DEFAULT_IMAGE, GOAL_LABELS, esc, url_path

POST_CSS = """<style>
.pp{width:100%;background:#fff;font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;}
.pp-head{background:#1a2d4a;padding:80px 6% 60px;text-align:center;}
.pp-back{display:inline-block;color:#afd0e8;font-size:14px;margin-bottom:1.6rem;}
.pp-badge{display:inline-block;background:rgba(107,157,189,.18);border:1px solid rgba(107,157,189,.35);color:#afd0e8;padding:8px 18px;border-radius:100px;font-size:14px;font-weight:500;margin:0 0 1.4rem;}
.pp-head h1{font-size:clamp(2.4rem,4.2vw,3.8rem);font-weight:900;letter-spacing:-.04em;line-height:1.3;color:#fff;margin:0 auto 1rem;max-width:860px;word-break:keep-all;}
.pp-sub{font-size:clamp(15px,1.8vw,19px);color:rgba(255,255,255,.7);margin:0;}
.pp-main{padding:60px 6% 70px;}
.pp-in{max-width:760px;margin:0 auto;}
.pp-cover{margin:0 0 2.4rem;border-radius:16px;overflow:hidden;background:#eef3f8;}
.pp-cover img{display:block;width:100%;height:auto;}
.pp-body{font-size:17px;line-height:2;color:#33445a;word-break:keep-all;}
.pp-body p{margin:0 0 1.4rem;}
.pp-body h2{font-size:clamp(2rem,2.6vw,2.4rem);font-weight:900;color:#1a2d4a;margin:2.6rem 0 1rem;letter-spacing:-.03em;line-height:1.4;}
.pp-body h3{font-size:clamp(1.7rem,2.2vw,2rem);font-weight:700;color:#1a2d4a;margin:2rem 0 .8rem;line-height:1.4;}
.pp-body strong{color:#1a2d4a;}
.pp-body a{color:#4a7fa5;text-decoration:underline;}
.pp-body ul,.pp-body ol{margin:0 0 1.4rem;padding-left:1.4em;}
.pp-body li{margin:0 0 .4rem;}
.pp-body blockquote{margin:0 0 1.4rem;padding:.4rem 0 .4rem 1.2rem;border-left:4px solid #4a7fa5;color:#4a5a6a;}
.pp-body hr{border:0;border-top:1px solid rgba(74,127,165,.2);margin:2.4rem 0;}
.pp-body figure{margin:0 0 1.6rem;}
.pp-body img{display:block;max-width:100%;height:auto;border-radius:12px;}
.pp-body figcaption{font-size:14px;color:#8a9ab0;margin-top:.5rem;text-align:center;}
.pp-cta{background:#1a2d4a;padding:70px 6%;text-align:center;}
.pp-cta p{color:rgba(255,255,255,.6);font-size:17px;margin:0 0 2rem;}
.pp-cta .pp-cta-t{font-size:clamp(2.2rem,3.4vw,2.8rem);font-weight:900;color:#fff;letter-spacing:-.04em;margin:0 0 1rem;}
.pp-cta-row{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;}
.pp-cta a{display:inline-block;font-weight:700;font-size:17px;padding:16px 40px;border-radius:10px;}
.pp-cta .pp-go{background:#4a7fa5;color:#fff;}
.pp-cta .pp-go:hover{background:#6b9dbd;}
.pp-cta .pp-more{background:transparent;color:#afd0e8;border:2px solid rgba(175,208,232,.5);padding:14px 38px;}
.pp-cta .pp-more:hover{background:rgba(255,255,255,.08);}
@media(max-width:560px){.pp-head{padding:60px 5% 44px;}.pp-main{padding:40px 5% 50px;}.pp-body{font-size:16px;}}
</style>"""


def post_html(item: Mapping) -> str:
    image = item.get("image")
    cover = ""
    if image and image != DEFAULT_IMAGE:
        cover = '<figure class="pp-cover"><img src="%s" alt="%s" loading="eager" decoding="async"></figure>' % (
            url_path(image), esc(item["title"]))
    return (
        POST_CSS + '\n<div class="pp">\n'
        '<div class="pp-head"><a class="pp-back" href="/pages/reviews/">← 수강생 후기 전체 보기</a><br>'
        '<span class="pp-badge">%s</span><h1>%s</h1><p class="pp-sub">%s</p></div>\n'
        '<div class="pp-main"><div class="pp-in">%s<div class="pp-body">%s</div></div></div>\n'
        '<div class="pp-cta"><p class="pp-cta-t">나도 이런 후기의 주인공이 되고 싶다면</p>'
        '<p>내 상황에 맞는 학점 계획을 1:1로 설계해 드립니다.</p>'
        '<div class="pp-cta-row"><a class="pp-go" href="/#es-form">1:1 무료 상담 신청 →</a>'
        '<a class="pp-more" href="/pages/reviews/">후기 더보기</a></div></div>\n</div>'
        % (esc(GOAL_LABELS[item["category"]]), esc(item["title"]), esc(item["subtitle"]), cover, item["body"]))


def post_page(item: Mapping, root: Path) -> ExtraPage:
    slug = item["slug"]
    image = item.get("image")
    return ExtraPage(
        rel_dir="pages/reviews/%s" % slug,
        title="%s | 에듀솔루션" % item["title"],
        desc=item["subtitle"],
        url_path="/pages/reviews/%s/" % slug,
        parts=[root / "sections" / "00-nav.html",
               Inline(post_html(item)),
               root / "sections" / "12-footer.html",
               root / "sections" / "09-kakao-float-button.html",
               root / "sections" / "10-diagnostic-popup.html"],
        og_image=SITE + url_path(image) if image else "",
    )
