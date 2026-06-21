"""URL-based deduplication.

This is intentionally the cheapest step in the pipeline. If we have seen a URL
already, we skip the article before spending any LLM tokens.
"""

from __future__ import annotations

import hashlib

from storage.redis_client import get_redis_client


DEDUP_TTL_SECONDS = 60 * 60 * 24 * 14


def fingerprint_url(url: str) -> str:
    """Create a stable Redis key from a URL."""

    digest = hashlib.md5(url.strip().lower().encode("utf-8")).hexdigest()
    return f"seen_article:{digest}"


def has_seen_url(url: str) -> bool:
    """Return True when Redis already contains this article fingerprint."""

    return bool(get_redis_client().exists(fingerprint_url(url)))


def mark_url_seen(url: str) -> None:
    """Store the article fingerprint with a TTL."""

    get_redis_client().setex(fingerprint_url(url), DEDUP_TTL_SECONDS, "1")

