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
