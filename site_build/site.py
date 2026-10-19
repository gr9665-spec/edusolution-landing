"""data/*.json을 읽어 검증하고, 빌드에 넘길 토큰과 추가 페이지를 만든다."""
from __future__ import annotations

from pathlib import Path

from . import data, render
from .analytics import analytics_head
from .articles import article_page, articles_section, sort_articles
from .posts import post_page


def load_site(root: Path, data_root: Path = None):
    """root는 조각·이미지가 있는 저장소, data_root는 data/*.json이 있는 곳(기본은 root). 테스트가 고정 데이터를 쓰려고 나눈다."""
    data_root = data_root or root
    team = data.load(data_root, "team.json", [])
    data.validate_team(team, root)
    reviews = data.load(data_root, "reviews.json", []) + data.load(data_root, "reviews.notion.json", [])
    data.validate_reviews(reviews, root)
    reviews = render.sort_posts(reviews)
    articles = data.load(data_root, "articles.json", [])
    data.validate_articles(articles, root)
    articles = sort_articles(articles)
    stats = data.load(data_root, "stats.json", [])
    data.validate_stats(stats)
    business = data.load(data_root, "business.json", {})
    data.validate_business(business)
    channel = data.load(data_root, "youtube.json", {})
    data.validate_youtube(channel)
    analytics = data.load(data_root, "analytics.json", {})
    data.validate_analytics(analytics)

    tokens = {
        "reviews_grid": render.reviews_grid(reviews),
        "reviews_filters": render.reviews_filters(reviews),
        "reviews_marquee": render.reviews_marquee(reviews),
        "education_articles": articles_section(articles),
        "team_cards": render.team_cards(team, "../../"),
        "team_extras": render.team_extras(team, channel),
        "team_channel": render.team_channel(channel),
        "stats_strip": render.stats_strip(stats),
        "site_footer": render.site_footer(business),
        "org_jsonld": render.org_jsonld(business, channel),
        "analytics_head": analytics_head(analytics),
    }
    return tokens, [post_page(r, root) for r in reviews] + [article_page(a, articles, root) for a in articles]
