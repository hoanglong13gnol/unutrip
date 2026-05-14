"""Shared synchronous Redis client for rate limiting and response cache."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_client: Any = None


def init_redis(url: str | None) -> Any:
    """Create a connection pool from REDIS_URL. Returns None if URL missing, redis not installed, or unreachable."""
    global _client
    _client = None

    if not url or not str(url).strip():
        logger.info("Redis disabled (REDIS_URL unset); using in-memory rate limit + local Gemini cache.")
        return None

    try:
        import redis
    except ImportError as exc:
        logger.warning(
            "Redis URL is set but the 'redis' package is not installed (%s). "
            "Run: pip install -r requirements.txt",
            exc,
        )
        return None

    try:
        client = redis.Redis.from_url(
            str(url).strip(),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        client.ping()
        _client = client
        logger.info("Redis connected for rate limit + Gemini cache.")
        return client
    except Exception as exc:
        logger.warning(
            "Redis unavailable (%s); falling back to in-memory rate limit + local Gemini cache.",
            exc,
        )
        _client = None
        return None


def get_redis() -> Any:
    return _client


def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception as exc:
            logger.warning("Redis close: %s", exc)
        _client = None
