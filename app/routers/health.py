from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text

from app.core.config import get_budget_limits, get_settings
from app.core.logging import get_logger
from app.db.engine import get_engine

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)


@router.get("/")
def healthcheck():
    settings = get_settings()
    limits = get_budget_limits()
    engine = get_engine()
    errors: List[Dict[str, Any]] = []

    db_ok = True
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok = False
        logger.error("health_db_error", error=str(exc))
        errors.append({"service": "db", "message": str(exc)})

    redis_ok = True
    redis_client: Redis | None = None
    try:
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        redis_client.ping()
    except RedisError as exc:
        redis_ok = False
        logger.error("health_redis_error", error=str(exc))
        errors.append({"service": "redis", "message": str(exc)})
    finally:
        if redis_client is not None:
            redis_client.close()

    payload = {
        "ok": db_ok and redis_ok,
        "db": db_ok,
        "redis": redis_ok,
        "version": "0.1.0",
        "budgetGuard": limits.model_dump(),
    }
    if errors:
        payload["errors"] = errors

    if not payload["ok"]:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)

    return payload
