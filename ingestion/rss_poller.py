"""RSS polling helpers.

The job of this module is deliberately narrow: download RSS XML and turn it
into normal Python dictionaries. It does not deduplicate, classify, summarize,
or store anything. Those steps belong to other layers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

from ingestion.article_fetcher import fetch_article_text
from ingestion.feed_configs import FeedConfig


def _entry_published_at(entry: Any) -> datetime:
    """Return a timezone-aware timestamp, falling back to now if missing."""

    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


async def poll_rss_feed(feed: FeedConfig) -> list[dict[str, Any]]:
    """Fetch one RSS feed and normalize its entries.

    The returned dictionaries use the same shape as SEC EDGAR ingestion so the
    downstream pipeline does not care where an article came from.
    """

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(feed.url)
        response.raise_for_status()

    parsed = feedparser.parse(response.text)
    articles: list[dict[str, Any]] = []

    for entry in parsed.entries:
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        url = getattr(entry, "link", "")
        full_text = await fetch_article_text(url)
        articles.append(
            {
                "title": getattr(entry, "title", "Untitled financial article"),
                "url": url,
                "published_at": _entry_published_at(entry),
                "source": feed.name,
                "source_category": feed.category,
                "credibility_score": feed.credibility_score,
                # Prefer full article text, but keep RSS summary fallback for
                # publishers that block article-page fetching.
                "body": full_text or summary,
            }
        )

    return articles


async def poll_all_rss_feeds(feeds: list[FeedConfig]) -> list[dict[str, Any]]:
    """Poll several feeds one after another.

    Sequential polling is easier to understand for a student project. If feed
    volume grows, this can be changed to asyncio.gather without touching the
    pipeline interface.
    """

    collected: list[dict[str, Any]] = []
    for feed in feeds:
        collected.extend(await poll_rss_feed(feed))
    return collected
