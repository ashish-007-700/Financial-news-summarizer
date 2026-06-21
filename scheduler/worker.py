"""Celery worker and beat schedule.

Run worker:
    celery -A scheduler.worker.celery_app worker --loglevel=info

Run beat:
    celery -A scheduler.worker.celery_app beat --loglevel=info
"""

from __future__ import annotations

import asyncio
import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

from ingestion.feed_configs import RSS_FEEDS, SEC_EDGAR_POLL_MINUTES
from ingestion.rss_poller import poll_rss_feed
from ingestion.sec_edgar import fetch_company_filings
from processing.pipeline import process_ingested_article
from storage.redis_client import redis_url


celery_app = Celery(
    "financial_news_aggregator",
    broker=redis_url(),
    backend=redis_url(),
)


@celery_app.task(name="poll_rss_source")
def poll_rss_source(feed_name: str) -> int:
    """Poll one RSS source and process new articles."""

    feed = next(feed for feed in RSS_FEEDS if feed.name == feed_name)
    articles = asyncio.run(poll_rss_feed(feed))
    processed_count = 0

    for article in articles:
        if process_ingested_article(article) is not None:
            processed_count += 1

    return processed_count


@celery_app.task(name="poll_sec_edgar")
def poll_sec_edgar() -> int:
    """Poll configured SEC CIKs and process new filings."""

    cik_values = [cik.strip() for cik in os.getenv("SEC_TRACKED_CIKS", "").split(",") if cik.strip()]
    processed_count = 0

    for cik in cik_values:
        articles = asyncio.run(fetch_company_filings(cik))
        for article in articles:
            if process_ingested_article(article) is not None:
                processed_count += 1

    return processed_count


beat_schedule = {
    f"poll-{feed.name.lower().replace(' ', '-')}-every-{feed.poll_minutes}-minutes": {
        "task": "poll_rss_source",
        "schedule": feed.poll_minutes * 60,
        "args": (feed.name,),
    }
    for feed in RSS_FEEDS
}

beat_schedule["poll-sec-edgar-every-15-minutes"] = {
    "task": "poll_sec_edgar",
    "schedule": SEC_EDGAR_POLL_MINUTES * 60,
}

celery_app.conf.beat_schedule = beat_schedule
celery_app.conf.timezone = "UTC"
