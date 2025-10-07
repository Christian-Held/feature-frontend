"""Observability utilities for the auth service."""

from .metrics import (
    AUTH_CAPTCHA_CHALLENGES,
    AUTH_LOCKOUTS,
    AUTH_LOGIN_FAILURE,
    AUTH_LOGIN_SUCCESS,
    AUTH_REFRESH_SUCCESS,
    AUTH_TOTP_FAILURE,
    CAP_REACHED,
    EMAIL_ENQUEUED,
    EMAIL_FAILED,
    EMAIL_SEND_LATENCY,
    PrometheusRequestMiddleware,
    RATE_LIMIT_BLOCK,
    metrics_router,
)
from .otel import setup_tracing

__all__ = [
    "AUTH_CAPTCHA_CHALLENGES",
    "AUTH_LOCKOUTS",
    "AUTH_LOGIN_FAILURE",
    "AUTH_LOGIN_SUCCESS",
    "AUTH_REFRESH_SUCCESS",
    "AUTH_TOTP_FAILURE",
    "CAP_REACHED",
    "EMAIL_ENQUEUED",
    "EMAIL_FAILED",
    "EMAIL_SEND_LATENCY",
    "PrometheusRequestMiddleware",
    "RATE_LIMIT_BLOCK",
    "metrics_router",
    "setup_tracing",
]
