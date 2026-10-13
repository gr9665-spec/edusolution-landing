"""데이터(JSON)를 HTML 조각으로 바꾸는 함수들."""
from __future__ import annotations

import html
import urllib.parse
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image

GOAL_ORDER = ["degree", "license", "transfer", "grad"]
GOAL_LABELS = {"degree": "학위 취득", "license": "자격증", "transfer": "편입", "grad": "대학원"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def url_path(rel: str) -> str:
    """저장소 안의 파일 경로를 사이트 주소(/로 시작, 한글·공백은 퍼센트 인코딩)로 바꾼다."""
    return "/" + urllib.parse.quote(rel.lstrip("/"))


def image_size(root: Path, rel: str) -> tuple:
    with Image.open(root / rel) as im:
        return im.size


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
        note = "%s 기준" % esc(s["asOf"].replace("-", "."))
        if s.get("source"):
            note += " · %s" % esc(s["source"])
        items.append(
            '    <div class="est-item">\n'
            '      <p class="est-main"><span class="est-n" data-count="%s">%s</span>%s</p>\n'
            '      <p class="est-label">%s</p>\n'
            '      <p class="est-note">%s</p>\n'
            '    </div>' % (s["value"], _fmt_number(s["value"]), suffix, esc(s["label"]), note))
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
    rows = [("대표자", business["ceo"])] if business.get("ceo") else []
    rows.append(("사업자등록번호", business["regno"]))
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
