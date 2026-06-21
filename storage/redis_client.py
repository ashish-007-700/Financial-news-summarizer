"""Redis helper used for deduplication and Celery broker configuration."""

import os

import redis


def get_redis_client() -> redis.Redis:
    """Create a Redis client from REDIS_URL."""

    return redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def redis_url() -> str:
    """Expose one source of truth for Celery and app code."""

    return os.getenv("REDIS_URL", "redis://localhost:6379/0")
