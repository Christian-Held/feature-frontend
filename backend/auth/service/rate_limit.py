"""Rate limit helpers for authentication flows."""

from __future__ import annotations

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis

from backend.core.config import AppConfig

logger = structlog.get_logger(__name__)


async def enforce_rate_limit(
    redis: Redis,
    *,
    settings: AppConfig,
    scope: str,
    identifier: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Increment the rate limit counter and raise if the limit is exceeded."""

    if not identifier:
        return

    key = f"{settings.redis_rate_limit_prefix}:{scope}:{identifier}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)

    if current > limit:
        ttl = await redis.ttl(key)
        logger.info(
            "rate_limit.exceeded",
            scope=scope,
            identifier=identifier,
            limit=limit,
            ttl=ttl,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    logger.info(
        "rate_limit.hit",
        scope=scope,
        identifier=identifier,
        current=current,
        limit=limit,
        window_seconds=window_seconds,
    )


__all__ = ["enforce_rate_limit"]
