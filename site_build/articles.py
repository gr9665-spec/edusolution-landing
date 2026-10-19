"""교육정보 글: 목록 섹션(교육정보 페이지 아래)과 글마다의 상세 페이지(검색 노출용 제목·설명·구조화 정보 포함)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from .core import SITE, ExtraPage, Inline
from .render import GOAL_LABELS, esc

BASE = "/pages/education-info/"


def sort_articles(items: Sequence[Mapping]) -> list:
    """최신 날짜순, 같은 날짜는 제목순(그 뒤는 id순)."""
    stable = sorted(items, key=lambda it: (it["title"], it["id"]))
    return sorted(stable, key=lambda it: it["date"], reverse=True)


def _dots(date: str) -> str:
    return date.replace("-", ".")


PER_PAGE = 6
CATEGORY_ICONS = {"degree": "🎓", "license": "📜", "transfer": "🏫", "grad": "📚"}

# 글이 쌓여도 목록이 끝없이 길어지지 않도록 브라우저에서 PER_PAGE 개씩 나눠 보여준다.
# 모든 글 링크는 HTML에 그대로 두어(검색엔진·자바스크립트 꺼짐 대응) 숨기기만 하고, 보던 페이지는 ?p= 로 주소에 남긴다.
PAGER_SCRIPT = r"""<script>
(function(){
  var list = document.querySelector('.pe-art-list');
  var nav = document.getElementById('pe-pager');
  if (!list || !nav) return;
  var cards = [].slice.call(list.querySelectorAll('.pe-art'));
  var per = parseInt(list.getAttribute('data-per-page'), 10) || 6;
  var pages = Math.ceil(cards.length / per);
  if (pages < 2) return;
  var cur = 1;
  var m = /[?&]p=(\d+)/.exec(location.search);
  if (m) cur = Math.min(Math.max(parseInt(m[1], 10) || 1, 1), pages);

  function btn(label, page, extra, aria) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'pe-pg' + (extra ? ' ' + extra : '');
    b.textContent = label;
    if (aria) b.setAttribute('aria-label', aria);
    if (page) b.addEventListener('click', function(){ go(page, true); });
    else b.disabled = true;
    return b;
  }
  function render() {
    cards.forEach(function(c, i){ c.hidden = Math.floor(i / per) + 1 !== cur; });
    nav.textContent = '';
    nav.appendChild(btn('‹ 이전', cur > 1 ? cur - 1 : 0, 'pe-pg-side', '이전 페이지'));
    for (var p = 1; p <= pages; p++) {
      var b = btn(String(p), p === cur ? 0 : p, p === cur ? 'on' : '', p + '페이지');
      if (p === cur) { b.disabled = false; b.setAttribute('aria-current', 'page'); }
      nav.appendChild(b);
    }
    nav.appendChild(btn('다음 ›', cur < pages ? cur + 1 : 0, 'pe-pg-side', '다음 페이지'));
  }
  function go(p, scroll) {
    cur = p;
    render();
    var url = location.pathname + (p > 1 ? '?p=' + p : '') + location.hash;
    history.replaceState(null, '', url);
    if (scroll) {
      var top = document.getElementById('articles');
      if (top) top.scrollIntoView({behavior: 'smooth', block: 'start'});
    }
  }
  render();
})();
</script>"""


def articles_section(items: Sequence[Mapping]) -> str:
    """교육정보 페이지의 '교육정보 글' 목록 구역(글이 많아지면 페이지로 나눠 보여준다). 글이 없으면 빈 문자열."""
    if not items:
        return ""
    cards = []
    for it in items:
        cards.append(
            '        <a class="pe-art" href="%s%s/">\n'
            '          <span class="pe-art-top"><span class="pe-art-ic" aria-hidden="true">%s</span>'
            '<span class="pe-art-cat">%s</span></span>\n'
            '          <span class="pe-art-t">%s</span>\n'
            '          <span class="pe-art-d">%s</span>\n'
            '          <span class="pe-art-m"><span>%s</span><span class="pe-art-go">글 읽기 →</span></span>\n'
            '        </a>' % (BASE, esc(it["slug"]), CATEGORY_ICONS[it["category"]], esc(GOAL_LABELS[it["category"]]),
                              esc(it["title"]), esc(it["description"]), esc(_dots(it.get("updated") or it["date"]))))
    return ('\n  <div class="pe-sec pe-articles" id="articles">\n    <div class="pe-in">\n'
            '      <h2 class="pe-h2">교육정보 글</h2>\n'
            '      <p class="pe-lead">자주 묻는 학점은행제 규정과 일정을 글로 정리했어요. 카드를 눌러 전체 내용을 읽어 보세요.</p>\n'
            '      <div class="pe-art-list" data-per-page="%d">\n' % PER_PAGE + "\n".join(cards) + '\n      </div>\n'
            '      <nav class="pe-pager" id="pe-pager" aria-label="교육정보 글 페이지"></nav>\n'
            '    </div>\n  </div>\n' + PAGER_SCRIPT + '\n')


ARTICLE_CSS = """<style>
.pa{width:100%;background:#fff;font-family:'Noto Sans KR',sans-serif;color:#2b3a4f;word-break:keep-all;}
.pa *,.pa *::before,.pa *::after{box-sizing:border-box;}
.pa-head{background:linear-gradient(rgba(10,18,35,.78),rgba(10,18,35,.78)),url('/assets/hero-education-info.jpg') center/cover no-repeat #1a2d4a;padding:96px 6% 70px;text-align:center;}
.pa-back{display:inline-block;color:#afd0e8;font-size:14px;margin-bottom:1.5rem;text-decoration:none;}
.pa-badge{display:inline-block;background:rgba(107,157,189,.2);border:1px solid rgba(107,157,189,.4);color:#c4dff0;padding:7px 16px;border-radius:100px;font-size:14px;font-weight:500;margin:0 0 1.3rem;}
.pa-head h1{font-size:clamp(2.6rem,4.2vw,3.9rem);font-weight:800;letter-spacing:-.03em;line-height:1.32;color:#fff;margin:0 auto;max-width:860px;text-shadow:0 2px 24px rgba(0,0,0,.4);}
.pa-desc{font-size:clamp(15px,1.8vw,18px);color:rgba(255,255,255,.8);line-height:1.8;margin:1.2rem auto 0;max-width:720px;}
.pa-date{font-size:14px;color:rgba(255,255,255,.55);margin:1.1rem 0 0;}
.pa-main{padding:60px 6% 40px;}
.pa-in{max-width:780px;margin:0 auto;}
.pa-body{font-size:17px;line-height:1.95;color:#33445a;}
.pa-body p{margin:0 0 1.3rem;}
.pa-body h2{font-size:clamp(2.1rem,2.6vw,2.5rem);font-weight:800;color:#1a2d4a;margin:2.8rem 0 1rem;letter-spacing:-.03em;line-height:1.4;}
.pa-body h3{font-size:clamp(1.8rem,2.2vw,2.1rem);font-weight:700;color:#1a2d4a;margin:2rem 0 .8rem;line-height:1.4;}
.pa-body strong{color:#1a2d4a;}
.pa-body a{color:#2f6b97;text-decoration:underline;}
.pa-body ul,.pa-body ol{margin:0 0 1.4rem;padding-left:1.4em;}
.pa-body li{margin:0 0 .45rem;}
.pa-body blockquote{margin:0 0 1.4rem;padding:.5rem 0 .5rem 1.2rem;border-left:4px solid #4a7fa5;color:#4a5a6a;}
.pa-body hr{border:0;border-top:1px solid rgba(74,127,165,.2);margin:2.4rem 0;}
.pa-body table{width:100%;border-collapse:collapse;margin:0 0 1.6rem;font-size:15.5px;line-height:1.7;}
.pa-body th,.pa-body td{padding:12px 14px;text-align:left;border-bottom:1px solid #d6e3ee;vertical-align:top;}
.pa-body th{background:#f2f7fb;color:#1a2d4a;font-weight:700;border-top:1px solid #d6e3ee;}
.pa-source{font-size:14px;line-height:1.8;color:#6b7f93;margin:2rem 0 0;padding-top:1.2rem;border-top:1px solid #e1eaf2;}
.pa-notice{margin:1.4rem 0 0;padding:16px 20px;background:#fff4e8;border-left:4px solid #e8892b;border-radius:0 12px 12px 0;font-size:15px;line-height:1.8;color:#4a3a22;}
.pa-related{margin-top:2.6rem;}
.pa-related h2{font-size:19px;font-weight:800;color:#1a2d4a;margin:0 0 .9rem;}
.pa-related a{display:block;padding:14px 4px;border-top:1px solid #d6e3ee;font-size:16px;font-weight:700;color:#1a2d4a;text-decoration:none;}
.pa-related a:last-child{border-bottom:1px solid #d6e3ee;}
.pa-related a:hover{color:#2f6b97;}
.pa-cta{background:#1a2d4a;padding:72px 6%;text-align:center;margin-top:40px;}
.pa-cta h2{font-size:clamp(2.2rem,3.4vw,2.9rem);font-weight:800;color:#fff;letter-spacing:-.03em;line-height:1.4;margin:0 0 .9rem;}
.pa-cta p{color:rgba(255,255,255,.72);font-size:17px;margin:0 0 1.8rem;}
.pa-cta a{display:inline-block;background:#4a7fa5;color:#fff;font-weight:700;font-size:17px;padding:16px 38px;border-radius:10px;text-decoration:none;margin:4px 6px;}
.pa-cta a:hover{background:#6b9dbd;}
.pa-cta a.ghost{background:transparent;border:2px solid rgba(175,208,232,.5);color:#afd0e8;padding:14px 36px;}
@media(max-width:560px){.pa-head{padding:80px 5% 52px;}.pa-main{padding:40px 5% 30px;}.pa-body{font-size:16px;}.pa-body table{font-size:14px;}.pa-body th,.pa-body td{padding:10px 8px;}}
</style>"""


def _json_ld(item: Mapping) -> str:
    url = SITE + BASE + item["slug"] + "/"
    doc = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": item["title"], "description": item["description"],
        "datePublished": item["date"], "dateModified": item.get("updated") or item["date"],
        "author": {"@type": "Organization", "name": "에듀솔루션"},
        "publisher": {"@type": "Organization", "name": "에듀솔루션",
                      "logo": {"@type": "ImageObject", "url": SITE + "/assets/logo.png"}},
        "mainEntityOfPage": url,
    }
    text = json.dumps(doc, ensure_ascii=False).replace("</", "<\\/")       # 본문 안 '</script>' 로 구조가 깨지지 않게
    return '<script type="application/ld+json">%s</script>' % text


def article_html(item: Mapping, all_items: Sequence[Mapping]) -> str:
    by_slug = {a["slug"]: a for a in all_items}
    meta = "게시 %s" % _dots(item["date"])
    if item.get("updated") and item["updated"] != item["date"]:
        meta += " · 수정 %s" % _dots(item["updated"])
    related = [by_slug[s] for s in item.get("related", []) if s in by_slug and s != item["slug"]]
    related_html = ""
    if related:
        links = "".join('<a href="%s%s/">%s</a>' % (BASE, esc(r["slug"]), esc(r["title"])) for r in related)
        related_html = '<div class="pa-related"><h2>함께 보면 좋은 글</h2>%s</div>' % links
    return (
        ARTICLE_CSS + '\n<div class="pa">\n'
        '<div class="pa-head"><a class="pa-back" href="%s">← 교육정보</a><br>'
        '<span class="pa-badge">%s</span><h1>%s</h1><p class="pa-desc">%s</p><p class="pa-date">%s</p></div>\n'
        '<div class="pa-main"><div class="pa-in"><div class="pa-body">%s</div>\n'
        '<p class="pa-source">출처·기준: %s</p>\n'
        '<p class="pa-notice">학점은행제 규정과 일정은 개정될 수 있어요. 신청 전에 국가평생교육진흥원 학점은행제의 최신 안내를 확인하거나 상담으로 현재 기준을 확인해 주세요.</p>\n'
        '%s</div></div>\n'
        '<div class="pa-cta"><h2>내 상황에 맞는 계획이 궁금하다면</h2><p>보유 학점과 목표를 알려 주시면 가장 빠른 경로를 1:1로 설계해 드립니다.</p>'
        '<a href="/#es-form">1:1 무료 상담 신청 →</a><a class="ghost" href="%s">교육정보 더 보기</a></div>\n</div>\n%s'
        % (BASE, esc(GOAL_LABELS[item["category"]]), esc(item["title"]), esc(item["description"]), esc(meta),
           item["body"], esc(item["source"]), related_html, BASE, _json_ld(item)))


def article_page(item: Mapping, all_items: Sequence[Mapping], root: Path) -> ExtraPage:
    slug = item["slug"]
    return ExtraPage(
        rel_dir="pages/education-info/%s" % slug,
        title="%s | 에듀솔루션" % item["title"],
        desc=item["description"],
        url_path="%s%s/" % (BASE, slug),
        lastmod=item.get("updated") or item["date"],
        parts=[root / "sections" / "00-nav.html",
               Inline(article_html(item, all_items)),
               root / "sections" / "12-footer.html",
               root / "sections" / "09-kakao-float-button.html",
               root / "sections" / "10-diagnostic-popup.html"],
    )
