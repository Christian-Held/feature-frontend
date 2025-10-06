"""Redis client factory for the authentication platform."""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from backend.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


__all__ = ["get_redis_client"]

