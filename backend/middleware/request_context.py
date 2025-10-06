"""Request-scoped context helpers for logging."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
admin_user_id_var: ContextVar[str | None] = ContextVar("admin_user_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def bind_request_id(request_id: str | None) -> None:
    request_id_var.set(request_id)


def bind_admin_user_id(user_id: str | None) -> None:
    admin_user_id_var.set(user_id)


def get_admin_user_id() -> str | None:
    return admin_user_id_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that seeds structlog context with request metadata."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        incoming_id = request.headers.get("X-Request-ID")
        request_id = incoming_id or str(uuid.uuid4())
        request_token = request_id_var.set(request_id)
        admin_token = admin_user_id_var.set(None)
        try:
            response = await call_next(request)
        finally:
            admin_user_id_var.reset(admin_token)
            request_id_var.reset(request_token)
        response.headers.setdefault("X-Request-ID", request_id)
        return response


__all__ = [
    "RequestContextMiddleware",
    "bind_admin_user_id",
    "bind_request_id",
    "get_admin_user_id",
    "get_request_id",
]
