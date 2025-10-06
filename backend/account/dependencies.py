"""FastAPI dependency helpers for account APIs."""

from __future__ import annotations

from fastapi import Depends
from redis.asyncio import Redis

from backend.auth.api.deps import require_current_user
from backend.core.config import get_settings
from backend.db.session import get_db
from backend.redis.client import get_redis_client


def CurrentUser() -> Depends:  # type: ignore[override]
    return Depends(require_current_user)


def DbSession() -> Depends:  # type: ignore[override]
    return Depends(get_db)


def AppSettings() -> Depends:  # type: ignore[override]
    return Depends(get_settings)


async def get_redis() -> Redis:
    return get_redis_client()


def RedisClient() -> Depends:  # type: ignore[override]
    return Depends(get_redis)


__all__ = ["CurrentUser", "DbSession", "AppSettings", "RedisClient", "require_current_user", "get_redis"]
