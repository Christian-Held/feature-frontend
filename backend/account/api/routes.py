"""FastAPI routes for account plan management and spend limits."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request, Response
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from backend.account import schemas
from backend.account.dependencies import get_redis
from backend.account.schemas import PlanResponse, PlanUpdateRequest, SpendLimitResponse, SpendLimitUpdateRequest
from backend.account.services import (
    LIMITS_CHANGED_EVENT,
    PLAN_CHANGED_EVENT,
    WARNING_HEADER_VALUE,
    PlanService,
    SpendAccountingService,
    SpendLimitService,
)
from backend.auth.api.deps import require_current_user
from backend.auth.service.rate_limit import enforce_rate_limit
from backend.core.config import AppConfig, get_settings
from backend.db.models.user import User
from backend.db.session import get_db

router = APIRouter(prefix="/v1/account", tags=["account"])
logger = structlog.get_logger(__name__)

PLAN_RATE_LIMIT = 5
LIMIT_RATE_LIMIT = 10
WINDOW_SECONDS = 3600


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.get("/plan", response_model=PlanResponse)
async def get_plan(
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> PlanResponse:
    plan_service = PlanService(session)
    plan = plan_service.get_active_plan(current_user.id)
    session.commit()
    return PlanResponse(plan=schemas.PlanCode(plan.code), name=plan.name, monthly_price_usd=plan.monthly_price_usd)


@router.post("/plan", response_model=PlanResponse)
async def update_plan(
    payload: PlanUpdateRequest,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> PlanResponse:
    await enforce_rate_limit(
        redis,
        settings=settings,
        scope="account:plan",
        identifier=str(current_user.id),
        limit=PLAN_RATE_LIMIT,
        window_seconds=WINDOW_SECONDS,
    )

    plan_service = PlanService(session)
    plan = plan_service.set_plan(
        user_id=current_user.id,
        plan_code=payload.plan,
        actor_user_id=current_user.id,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    session.commit()
    logger.info(PLAN_CHANGED_EVENT, user_id=str(current_user.id), plan=plan.code)
    return PlanResponse(plan=schemas.PlanCode(plan.code), name=plan.name, monthly_price_usd=plan.monthly_price_usd)


@router.get("/limits", response_model=SpendLimitResponse)
async def get_limits(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> SpendLimitResponse:
    limit_service = SpendLimitService(session)
    limit = limit_service.get_or_create(current_user.id)
    accounting = SpendAccountingService(session)
    totals = accounting.get_month_totals(current_user.id)
    session.commit()

    if totals.cap_reached and not totals.hard_stop:
        response.headers["X-Spend-Warning"] = WARNING_HEADER_VALUE

    return SpendLimitResponse(
        monthly_cap_usd=limit.monthly_cap_usd,
        hard_stop=limit.hard_stop,
        usage_usd=totals.usage_usd,
        remaining_usd=totals.remaining_usd,
        cap_reached=totals.cap_reached,
    )


@router.post("/limits", response_model=SpendLimitResponse)
async def update_limits(
    payload: SpendLimitUpdateRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> SpendLimitResponse:
    await enforce_rate_limit(
        redis,
        settings=settings,
        scope="account:limits",
        identifier=str(current_user.id),
        limit=LIMIT_RATE_LIMIT,
        window_seconds=WINDOW_SECONDS,
    )

    limit_service = SpendLimitService(session)
    limit = limit_service.update_limits(
        user_id=current_user.id,
        monthly_cap_usd=payload.monthly_cap_usd,
        hard_stop=payload.hard_stop,
        actor_user_id=current_user.id,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    accounting = SpendAccountingService(session)
    totals = accounting.get_month_totals(current_user.id)
    session.commit()

    if totals.cap_reached and not totals.hard_stop:
        response.headers["X-Spend-Warning"] = WARNING_HEADER_VALUE

    logger.info(
        LIMITS_CHANGED_EVENT,
        user_id=str(current_user.id),
        monthly_cap_usd=str(limit.monthly_cap_usd),
        hard_stop=limit.hard_stop,
    )

    return SpendLimitResponse(
        monthly_cap_usd=limit.monthly_cap_usd,
        hard_stop=limit.hard_stop,
        usage_usd=totals.usage_usd,
        remaining_usd=totals.remaining_usd,
        cap_reached=totals.cap_reached,
    )


__all__ = ["router", "CAP_BLOCK_MESSAGE"]
