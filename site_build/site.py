"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path

from . import data, render


def load_site(root: Path):
    reviews = data.load(root, "reviews.json", [])
    data.validate_reviews(reviews, root)
    tokens = {
        "reviews_grid": render.reviews_grid(reviews, root),
        "reviews_filters": render.reviews_filters(reviews),
        "reviews_featured": render.reviews_featured(reviews),
    }
    return tokens, []
