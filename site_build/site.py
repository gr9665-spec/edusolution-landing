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
    channel = data.load(root, "youtube.json", {})
    data.validate_youtube(channel)

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
        "team_extras": render.team_extras(team, cases_by_planner, channel),
        "team_channel": render.team_channel(channel),
        "stats_strip": render.stats_strip(stats),
        "site_footer": render.site_footer(business),
    }
    team_by_id = {m["id"]: m for m in team}
    return tokens, [case_page(c, team_by_id, root) for c in cases]
