"""RSS feed configuration.

This file is intentionally just data.  The rest of the ingestion code reads
these settings and does the actual network work. Keeping source metadata here
makes it easy to add, remove, or change feeds without touching pipeline logic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedConfig:
    """One trusted financial-news source.

    poll_minutes controls how often Celery Beat should schedule the source.
    credibility_score is stored with articles so the UI can explain source
    quality to users later.
    """

    name: str
    url: str
    category: str
    poll_minutes: int
    credibility_score: float


RSS_FEEDS: list[FeedConfig] = [
    FeedConfig(
        name="Reuters",
        url="https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
        category="wire",
        poll_minutes=5,
        credibility_score=0.95,
    ),
    FeedConfig(
        name="Yahoo Finance",
        url="https://finance.yahoo.com/news/rssindex",
        category="market_news",
        poll_minutes=5,
        credibility_score=0.85,
    ),
    FeedConfig(
        name="PR Newswire",
        url="https://www.prnewswire.com/rss/news-releases-list.rss",
        category="press_release",
        poll_minutes=10,
        credibility_score=0.70,
    ),
    FeedConfig(
        name="Business Wire",
        url="https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFpQWw==",
        category="press_release",
        poll_minutes=10,
        credibility_score=0.70,
    ),
]


SEC_EDGAR_POLL_MINUTES = 15
SEC_EDGAR_CREDIBILITY_SCORE = 1.0

