"""Middleware enforcing strict security headers."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

_CSP_VALUE = (
    "default-src 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "img-src 'self' data:; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "font-src 'self' data:"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set HSTS, XFO, CSP, and related headers on all responses."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", _CSP_VALUE)

        path = request.url.path
        if path.startswith("/widget") or path.startswith("/v1/rag/chat"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "X-Embed-Token, Content-Type"
            response.headers["X-Frame-Options"] = "ALLOWALL"
            response.headers["Content-Security-Policy"] = "frame-ancestors *;"
        return response


__all__ = ["SecurityHeadersMiddleware", "_CSP_VALUE"]
