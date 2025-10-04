from __future__ import annotations

from fastapi import APIRouter

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
    try:
        conn = engine.connect()
        conn.close()
        db_status = "ok"
    except Exception as exc:
        logger.error("health_db_error", error=str(exc))
        db_status = "error"
    return {
        "status": "ok",
        "version": "0.1.0",
        "redis": settings.redis_url,
        "db": db_status,
        "budgetGuard": limits.model_dump(),
    }
