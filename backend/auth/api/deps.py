"""Shared dependencies for auth-protected routes."""

from __future__ import annotations

import uuid

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.db.models.user import User, UserStatus
from backend.db.session import get_db
from backend.middleware.request_context import bind_user_id
from backend.security.jwt_service import get_jwt_service

logger = structlog.get_logger(__name__)
_http_bearer = HTTPBearer(auto_error=False)


async def require_current_user(
    request: Request, session: Session = Depends(get_db)
) -> User:
    credentials: HTTPAuthorizationCredentials | None = await _http_bearer(request)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don’t have permission to perform this action.",
        )

    token = credentials.credentials
    jwt_service = get_jwt_service()
    try:
        payload = jwt_service.decode(token)
    except Exception as exc:  # pragma: no cover - invalid token paths
        logger.info("api.auth.invalid_token", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don’t have permission to perform this action.",
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don’t have permission to perform this action.",
        )

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except Exception as exc:  # pragma: no cover - malformed sub
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don’t have permission to perform this action.",
        ) from exc

    user = session.get(User, user_id)
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don’t have permission to perform this action.",
        )
    bind_user_id(str(user.id))
    return user


__all__ = ["require_current_user", "_http_bearer"]
