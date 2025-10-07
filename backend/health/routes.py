"""Health and readiness endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, status
from sqlalchemy import text
from starlette.responses import JSONResponse

from backend.auth.email.client import smtp_ping
from backend.core.config import get_settings
from backend.db.session import engine
from backend.redis.client import get_redis_client

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> JSONResponse:
    settings = get_settings()
    checks: Dict[str, Any] = {}
    overall_ok = True

    # Database
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:  # pragma: no cover - real DB outage hard to simulate
        checks["database"] = False
        checks["database_error"] = str(exc)
        overall_ok = False

    # Redis
    redis = get_redis_client()
    try:
        await redis.ping()
        checks["redis"] = True
    except Exception as exc:
        checks["redis"] = False
        checks["redis_error"] = str(exc)
        overall_ok = False

    # SMTP
    try:
        smtp_ok = await smtp_ping(settings)
    except Exception as exc:  # pragma: no cover - network errors
        smtp_ok = False
        checks["smtp_error"] = str(exc)
    checks["smtp"] = smtp_ok
    overall_ok = overall_ok and smtp_ok

    status_code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    payload = {"status": "ok" if overall_ok else "degraded", **checks}
    return JSONResponse(status_code=status_code, content=payload)


__all__ = ["router"]
