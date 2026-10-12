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
               root / "sections" / "12-footer.html",
               root / "sections" / "09-kakao-float-button.html",
               root / "sections" / "10-diagnostic-popup.html"],
    )
