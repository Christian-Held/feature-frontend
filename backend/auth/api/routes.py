"""FastAPI routes for registration and email verification flows."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.auth.schemas.registration import (
    RegistrationRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
)
from backend.auth.service.registration_service import (
    complete_email_verification,
    register_user,
    resend_verification,
)
from backend.core.config import AppConfig, get_settings
from backend.db.session import get_db
from backend.redis.client import get_redis_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return None


@router.post("/register", response_model=RegistrationResponse)
async def register_endpoint(
    payload: RegistrationRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    """Register a new user and send the verification email."""

    redis = get_redis_client()
    message = await register_user(
        session=session,
        request=payload,
        settings=settings,
        remote_ip=_client_ip(request),
        redis=redis,
    )
    logger.info("api.register.completed", email=payload.email)
    return RegistrationResponse(message=message)


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification_endpoint(
    payload: ResendVerificationRequest,
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    """Resend verification email for an unverified user."""

    redis = get_redis_client()
    message = await resend_verification(session=session, request=payload, settings=settings, redis=redis)
    logger.info("api.resend.completed", email=payload.email)
    return ResendVerificationResponse(message=message)


@router.get("/verify-email")
async def verify_email_endpoint(
    token: str,
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    """Verify the email using the provided token and redirect to the login page."""

    await complete_email_verification(session=session, token=token, settings=settings)
    redirect_url = f"{settings.frontend_base_url}/login?verified=1"
    logger.info("api.verify.redirect", redirect_url=redirect_url)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


__all__ = ["router"]
