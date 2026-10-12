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
