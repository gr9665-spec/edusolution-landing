"""데이터(JSON)를 HTML 조각으로 바꾸는 함수들."""
from __future__ import annotations

import html
import json
import urllib.parse
from pathlib import Path
from typing import Mapping, Sequence

from .core import SITE as SITE_URL

GOAL_ORDER = ["degree", "license", "transfer", "grad"]
GOAL_LABELS = {"degree": "학위 취득", "license": "자격증", "transfer": "편입", "grad": "대학원"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def url_path(rel: str) -> str:
    """저장소 안의 파일 경로를 사이트 주소(/로 시작, 한글·공백은 퍼센트 인코딩)로 바꾼다."""
    return "/" + urllib.parse.quote(rel.lstrip("/"))


# =============================================================== 후기

DEFAULT_IMAGE = "assets/review-default.jpg"
MARQUEE_MIN = 4         # 이보다 적으면 흐르지 않고 나란히 둔다
MARQUEE_MAX = 8
SECONDS_PER_CARD = 7.5  # 카드 8장이 한 바퀴 도는 데 약 60초


def sort_posts(items: Sequence[Mapping]) -> list:
    """최신 날짜순, 같은 날짜는 제목순. 날짜가 없는 후기는 맨 뒤. 날짜는 정렬에만 쓰고 화면에는 보여주지 않는다."""
    stable = sorted(items, key=lambda it: (it["title"], it["id"]))          # 날짜·제목이 같으면 id순(실행마다 순서가 달라지지 않게)
    return sorted(stable, key=lambda it: it.get("date") or "", reverse=True)


def _card(item: Mapping, p: str, ind: str, extra_cls: str = "", with_cat: bool = False, clone: bool = False) -> str:
    """후기 카드 하나. p는 CSS 접두어('pr' 후기 목록, 'es5' 메인)."""
    i1, i2 = ind + "  ", ind + "    "
    cat = ' data-cat="%s"' % esc(item["category"]) if with_cat else ""
    hide = ' tabindex="-1"' if clone else ""
    src = url_path(item.get("image") or DEFAULT_IMAGE)
    lines = [
        '%s<a class="%s-card%s"%s href="/pages/reviews/%s/"%s>' % (ind, p, extra_cls, cat, esc(item["slug"]), hide),
        '%s<span class="%s-img"><img src="%s" alt="%s" width="1200" height="750" loading="lazy" decoding="async"></span>' % (
            i1, p, src, esc(item["title"])),
        '%s<span class="%s-body">' % (i1, p),
        '%s<span class="%s-ttl">%s</span>' % (i2, p, esc(item["title"])),
        '%s<span class="%s-sub">%s</span>' % (i2, p, esc(item["subtitle"])),
        '%s<span class="%s-meta"><span class="%s-cat">%s</span></span>' % (i2, p, p, esc(GOAL_LABELS[item["category"]])),
        '%s</span>' % i1,
        '%s</a>' % ind,
    ]
    return "\n".join(lines)


def reviews_grid(items: Sequence[Mapping]) -> str:
    cards = [_card(it, "pr", "        ", " pr-post", with_cat=True) for it in items]
    if not cards:
        return ""
    return "\n\n" + "\n\n".join(cards) + "\n\n      "


def reviews_filters(items: Sequence[Mapping]) -> str:
    present = {it["category"] for it in items}
    chips = ['        <button class="pr-chip on" type="button" data-filter="all">전체</button>']
    for g in GOAL_ORDER:
        if g in present:
            chips.append('        <button class="pr-chip" type="button" data-filter="%s">%s</button>' % (g, GOAL_LABELS[g]))
    return "\n" + "\n".join(chips) + "\n      "


def reviews_marquee(items: Sequence[Mapping]) -> str:
    """메인 페이지의 흐르는 후기. 4개 이상이면 한 번 더 복제해 끊김 없이 돌고, 그보다 적으면 가만히 둔다."""
    latest = list(items)[:MARQUEE_MAX]        # 호출자가 sort_posts로 정렬해서 넘긴다
    if not latest:
        return ""
    ind = "          "
    cards = "\n".join(_card(it, "es5", ind) for it in latest)
    if len(latest) < MARQUEE_MIN:
        return ('\n    <div class="es5-marq is-static">\n      <div class="es5-set">\n%s\n      </div>\n    </div>\n  ' % cards)
    clones = "\n".join(_card(it, "es5", ind, clone=True) for it in latest)
    dur = "%gs" % (SECONDS_PER_CARD * len(latest))
    return ('\n    <div class="es5-marq is-flow" style="--dur:%s">\n      <div class="es5-track">\n'
            '        <div class="es5-set">\n%s\n        </div>\n'
            '        <div class="es5-set" data-clone aria-hidden="true">\n%s\n        </div>\n'
            '      </div>\n    </div>\n  ' % (dur, cards, clones))


# =============================================================== 팀

TEAM_EXTRAS_CSS = """<style>
.pt-mem-career{list-style:none;margin:0 0 1.25rem;padding:0;}
.pt-mem-career li{font-size:14px;color:#4a5a6a;line-height:1.8;padding-left:14px;position:relative;}
.pt-mem-career li::before{content:'';position:absolute;left:0;top:.8em;width:5px;height:5px;border-radius:50%;background:#4a7fa5;}
</style>"""


def team_cards(team: Sequence[Mapping], rel: str = "../../") -> str:
    ind = "        "
    cards = []
    for m in team:
        i1, i2, i3 = ind + "  ", ind + "    ", ind + "      "
        lines = [
            '%s<!-- %s -->' % (ind, esc(m["name"])),
            '%s<article class="pt-mem-card">' % ind,
            '%s<div class="pt-mem-photo">' % i1,
            '%s<img src="%s%s" alt="%s" loading="lazy" decoding="async">' % (i2, rel, esc(m["photo"]), esc(m["name"])),
            '%s</div>' % i1,
            '%s<div class="pt-mem-body">' % i1,
            '%s<p class="pt-mem-role">%s</p>' % (i2, esc(m["role"])),
            '%s<h3 class="pt-mem-name">%s</h3>' % (i2, esc(m["name"])),
        ]
        if m.get("slogan"):
            lines.append('%s<p class="pt-mem-slogan">%s</p>' % (i2, esc(m["slogan"])))
        lines.append('%s<p class="pt-mem-desc">%s</p>' % (i2, m["bio"]))
        career = m.get("career") or []
        if career:
            lines.append('%s<ul class="pt-mem-career">' % i2)
            lines += ['%s<li>%s</li>' % (i3, esc(c)) for c in career]
            lines.append('%s</ul>' % i2)
        lines.append('%s<p class="pt-mem-tags-label">전문 분야</p>' % i2)
        lines.append('%s<div class="pt-mem-tags">' % i2)
        lines += ['%s<span class="pt-mem-tag">%s</span>' % (i3 + "  ", esc(t)) for t in m["tags"]]
        lines.append('%s</div>' % i2)
        if m.get("kakao") or m.get("phone"):
            lines.append('%s<p class="pt-mem-tags-label">상담 문의</p>' % i2)
            lines.append('%s<ul class="pt-mem-contact">' % i2)
            if m.get("kakao"):
                lines.append('%s<li><span class="pt-mem-ck">카카오톡</span><span class="pt-mem-cv">%s</span></li>' % (i3, esc(m["kakao"])))
            if m.get("phone"):
                digits = "".join(ch for ch in m["phone"] if ch.isdigit())
                lines.append('%s<li><span class="pt-mem-ck">전화</span><a class="pt-mem-cv" href="tel:%s">%s</a></li>'
                             % (i3, digits, esc(m["phone"])))
            lines.append('%s</ul>' % i2)
        actions = ['%s<a class="pt-mem-cta" href="/#es-form">무료 상담 신청</a>' % i3]
        if m.get("youtube"):
            actions.append('%s<a class="pt-mem-yt" href="%s" target="_blank" rel="noopener noreferrer">%s유튜브 채널</a>'
                           % (i3, esc(m["youtube"]), YT_ICON_SMALL))
        lines.append('%s<div class="pt-mem-actions">' % i2)
        lines += actions
        lines.append('%s</div>' % i2)
        lines += ['%s</div>' % i1, '%s</article>' % ind]
        cards.append("\n".join(lines))
    if not cards:
        return ""
    return "\n\n" + "\n\n".join(cards) + "\n\n      "


def team_extras(team: Sequence[Mapping], channel: Mapping = None) -> str:
    """경력 목록·유튜브 링크가 있을 때만 필요한 CSS."""
    css = []
    if any(m.get("career") for m in team):
        css.append(TEAM_EXTRAS_CSS)
    if channel or any(m.get("youtube") for m in team):
        css.append(TEAM_YT_CSS)
    return "\n".join(css)


YT_ICON_SMALL = ('<svg class="pt-yt-ico" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">'
                 '<rect x="1" y="4.5" width="22" height="15" rx="4.5" fill="#ff0000"/><path d="M10 8.7v6.6l5.6-3.3z" fill="#fff"/></svg>')
YT_ICON_BIG = YT_ICON_SMALL.replace('width="18" height="18"', 'width="56" height="56"')

TEAM_YT_CSS = """<style>
.pt-yt-team{display:flex;align-items:center;gap:24px;margin-top:2.5rem;padding:28px 32px;border-radius:20px;background:#1a2d4a;}
.pt-yt-team .pt-yt-ico{flex-shrink:0;}
.pt-yt-body{flex:1;min-width:0;}
.pt-yt-name{margin:0 0 6px;font-size:clamp(20px,2.4vw,26px);font-weight:900;color:#fff;letter-spacing:-.02em;}
.pt-yt-desc{margin:0;font-size:15px;color:rgba(255,255,255,.65);line-height:1.8;}
.pt-yt-btn{flex-shrink:0;background:#ff0000;color:#fff !important;font-weight:700;font-size:15px;padding:14px 26px;border-radius:10px;text-decoration:none;white-space:nowrap;}
.pt-yt-btn:hover{background:#d90000;}
.pt-mem-yt{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:700;color:#4a7fa5 !important;text-decoration:none;}
.pt-mem-yt:hover{color:#1a2d4a !important;}
@media(max-width:700px){.pt-yt-team{flex-direction:column;align-items:flex-start;padding:24px;}.pt-yt-btn{width:100%;text-align:center;}}
</style>"""


def team_channel(channel: Mapping) -> str:
    """담당자 카드 위에 크게 보이는 팀 유튜브 채널 안내."""
    if not channel:
        return ""
    desc = '\n    <p class="pt-yt-desc">%s</p>' % esc(channel["description"]) if channel.get("description") else ""
    return ('<div class="pt-yt-team">\n  %s\n  <div class="pt-yt-body">\n    <p class="pt-yt-name">%s</p>%s\n  </div>\n'
            '  <a class="pt-yt-btn" href="%s" target="_blank" rel="noopener noreferrer">유튜브 채널 바로가기 →</a>\n</div>'
            % (YT_ICON_BIG, esc(channel["name"]), desc, esc(channel["url"])))


# =============================================================== 메인: 실적 수치 띠, 푸터

STATS_CSS = """<style>
.est{width:100%;background:#1a2d4a;font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;}
.est-in{max-width:1100px;margin:0 auto;padding:36px 6% 44px;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:2rem;text-align:center;}
.est-item+.est-item{border-left:1px solid rgba(255,255,255,.1);}
.est-main{margin:0 0 6px;font-size:clamp(2.4rem,4vw,3.4rem);font-weight:900;letter-spacing:-.03em;color:#fff;line-height:1.2;}
.est-s{font-size:.55em;color:#7ab8d8;margin-left:3px;}
.est-label{margin:0 0 4px;font-size:16px;font-weight:700;color:rgba(255,255,255,.88);}
.est-note{margin:0;font-size:12px;color:rgba(255,255,255,.4);line-height:1.6;}
@media(max-width:560px){.est-item+.est-item{border-left:0;border-top:1px solid rgba(255,255,255,.1);padding-top:1.5rem;}}
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


def org_jsonld(business: Mapping, channel: Mapping) -> str:
    """메인 페이지에 넣는 회사 구조화 정보(검색엔진용). 개인 연락처는 넣지 않고, 사업자 정보·유튜브 채널만 쓴다."""
    if not business:
        return ""
    doc = {"@context": "https://schema.org", "@type": "EducationalOrganization", "name": business["company"],
           "url": SITE_URL + "/", "logo": SITE_URL + "/assets/logo.png",
           "address": {"@type": "PostalAddress", "addressCountry": "KR", "streetAddress": business["address"]}}
    if channel and channel.get("url"):
        doc["sameAs"] = [channel["url"]]
    site = {"@context": "https://schema.org", "@type": "WebSite", "name": business["company"],
            "url": SITE_URL + "/", "inLanguage": "ko-KR"}
    return "\n".join('<script type="application/ld+json">%s</script>' % json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
                     for d in (doc, site))


FOOTER_CSS ="""<style>
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
