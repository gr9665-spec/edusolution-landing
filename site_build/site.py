"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path

from . import data, render


def load_site(root: Path):
    team = data.load(root, "team.json", [])
    team_ids = data.validate_team(team, root)
    reviews = data.load(root, "reviews.json", [])
    data.validate_reviews(reviews, root, team_ids)
    tokens = {
        "reviews_grid": render.reviews_grid(reviews, root),
        "reviews_filters": render.reviews_filters(reviews),
        "reviews_featured": render.reviews_featured(reviews),
        "team_cards": render.team_cards(team, "../../"),
        "team_extras": render.team_extras(team),
    }
    return tokens, []
