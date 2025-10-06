"""FastAPI routes for authentication, sessions, and 2FA flows."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RecoveryLoginRequest,
    RecoveryLoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegistrationRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    TwoFAEnableCompleteRequest,
    TwoFAEnableCompleteResponse,
    TwoFAEnableInitResponse,
    TwoFADisableRequest,
    TwoFADisableResponse,
    TwoFAVerifyRequest,
    TwoFAVerifyResponse,
)
from backend.auth.api.deps import require_current_user
from backend.auth.service.auth_service import (
    complete_two_factor,
    disable_two_factor,
    init_two_factor,
    login_user,
    logout_session,
    recovery_login,
    refresh_tokens,
    verify_two_factor,
)
from backend.auth.service.registration_service import (
    complete_email_verification,
    register_user,
    resend_verification,
)
from backend.core.config import AppConfig, get_settings
from backend.db.models.user import User
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


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


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


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(
    payload: LoginRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    redis = get_redis_client()
    response = await login_user(
        db=session,
        settings=settings,
        request=payload,
        redis=redis,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    logger.info("api.login.completed", email=payload.email, requires_2fa=response.requires_2fa)
    return response


@router.post("/2fa/verify", response_model=TwoFAVerifyResponse)
async def verify_two_factor_endpoint(
    payload: TwoFAVerifyRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    redis = get_redis_client()
    response = await verify_two_factor(
        db=session,
        settings=settings,
        request=payload,
        redis=redis,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    logger.info("api.2fa.verified", challenge_id=payload.challenge_id)
    return response


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_endpoint(
    payload: RefreshRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    response = await refresh_tokens(
        db=session,
        settings=settings,
        request=payload,
        redis=get_redis_client(),
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    logger.info("api.refresh.rotated")
    return response


@router.post("/logout", response_model=LogoutResponse)
async def logout_endpoint(
    payload: RefreshRequest,
    request: Request,
    session: Session = Depends(get_db),
):
    response = await logout_session(
        db=session,
        token=payload.refresh_token,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    logger.info("api.logout.completed")
    return response


@router.post("/2fa/enable-init", response_model=TwoFAEnableInitResponse)
async def enable_two_factor_init_endpoint(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    response = await init_two_factor(db=session, settings=settings, user=current_user, redis=get_redis_client())
    logger.info("api.2fa.enable_init", user_id=str(current_user.id))
    return response


@router.post("/2fa/enable-complete", response_model=TwoFAEnableCompleteResponse)
async def enable_two_factor_complete_endpoint(
    payload: TwoFAEnableCompleteRequest,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    response = await complete_two_factor(db=session, request=payload, user=current_user, redis=get_redis_client())
    logger.info("api.2fa.enabled", user_id=str(current_user.id))
    return response


@router.post("/2fa/disable", response_model=TwoFADisableResponse)
async def disable_two_factor_endpoint(
    payload: TwoFADisableRequest,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    response = await disable_two_factor(db=session, user=current_user, request=payload)
    logger.info("api.2fa.disabled", user_id=str(current_user.id))
    return response


@router.post("/recovery-login", response_model=RecoveryLoginResponse)
async def recovery_login_endpoint(
    payload: RecoveryLoginRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: AppConfig = Depends(get_settings),
):
    redis = get_redis_client()
    response = await recovery_login(
        db=session,
        settings=settings,
        request=payload,
        redis=redis,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    logger.info("api.recovery_login.completed", email=payload.email)
    return response


__all__ = ["router"]
