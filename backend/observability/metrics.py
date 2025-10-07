"""Prometheus metrics setup for the authentication service."""

from __future__ import annotations

import time
from typing import Iterable

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from starlette.responses import Response

REGISTRY = CollectorRegistry(auto_describe=True)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Histogram of HTTP request durations in seconds.",
    labelnames=("method", "path", "status"),
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        1.5,
        2.0,
        3.0,
        5.0,
    ),
    registry=REGISTRY,
)

AUTH_LOGIN_SUCCESS = Counter(
    "auth_login_success_total",
    "Number of successful password-based logins.",
    registry=REGISTRY,
)
AUTH_LOGIN_FAILURE = Counter(
    "auth_login_failure_total",
    "Number of failed password-based logins.",
    registry=REGISTRY,
)
AUTH_TOTP_FAILURE = Counter(
    "auth_totp_failure_total",
    "Number of failed TOTP verification attempts.",
    registry=REGISTRY,
)
AUTH_CAPTCHA_CHALLENGES = Counter(
    "auth_captcha_challenges_total",
    "Number of CAPTCHA challenges enforced across login and MFA flows.",
    registry=REGISTRY,
)
AUTH_REFRESH_SUCCESS = Counter(
    "auth_refresh_success_total",
    "Number of successful refresh token rotations.",
    registry=REGISTRY,
)
AUTH_LOCKOUTS = Counter(
    "auth_lockouts_total",
    "Number of temporary account lockouts due to repeated failures.",
    registry=REGISTRY,
)
EMAIL_ENQUEUED = Counter(
    "email_enqueued_total",
    "Number of emails enqueued for delivery.",
    registry=REGISTRY,
)
EMAIL_FAILED = Counter(
    "email_failed_total",
    "Number of email delivery failures.",
    registry=REGISTRY,
)
EMAIL_SEND_LATENCY = Histogram(
    "email_send_latency_ms",
    "Latency of email send operations in milliseconds.",
    buckets=(
        5,
        10,
        20,
        50,
        100,
        250,
        500,
        1000,
        2000,
        5000,
        10000,
    ),
    registry=REGISTRY,
)
RATE_LIMIT_BLOCK = Counter(
    "rate_limit_block_total",
    "Number of requests blocked by rate limiting or deny lists.",
    registry=REGISTRY,
)
CAP_REACHED = Counter(
    "cap_reached_total",
    "Number of times a user hit their configured spend cap.",
    registry=REGISTRY,
)


class PrometheusRequestMiddleware:
    """Simple ASGI middleware that records request durations."""

    def __init__(self, app, excluded_paths: Iterable[str] | None = None) -> None:
        self._app = app
        self._excluded = set(excluded_paths or [])

    async def __call__(self, scope, receive, send):  # type: ignore[override]
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self._excluded:
            await self._app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        start = time.perf_counter()
        status_holder = {"status": "500"}

        async def _send(message):
            if message.get("type") == "http.response.start":
                status_holder["status"] = str(message.get("status", 500))
            await send(message)

        try:
            await self._app(scope, receive, _send)
        finally:
            duration = time.perf_counter() - start
            template = scope.get("route") and getattr(scope["route"], "path", path)
            labels = {
                "method": method,
                "path": template or path,
                "status": status_holder["status"],
            }
            REQUEST_DURATION.labels(**labels).observe(duration)


def metrics_router() -> APIRouter:
    router = APIRouter()

    @router.get("/metrics")
    async def handle_metrics() -> Response:  # pragma: no cover - thin wrapper
        payload = generate_latest(REGISTRY)
        return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

    return router


__all__ = [
    "REQUEST_DURATION",
    "AUTH_LOGIN_SUCCESS",
    "AUTH_LOGIN_FAILURE",
    "AUTH_TOTP_FAILURE",
    "AUTH_CAPTCHA_CHALLENGES",
    "AUTH_REFRESH_SUCCESS",
    "AUTH_LOCKOUTS",
    "EMAIL_ENQUEUED",
    "EMAIL_FAILED",
    "EMAIL_SEND_LATENCY",
    "RATE_LIMIT_BLOCK",
    "CAP_REACHED",
    "PrometheusRequestMiddleware",
    "metrics_router",
    "REGISTRY",
]
