"""FastAPI application factory for the auth service."""

from __future__ import annotations

from fastapi import FastAPI

from backend.account.api import router as account_router
from backend.admin.api import router as admin_router
from backend.auth.api import router as auth_router
from backend.billing.api.routes import router as billing_router
from backend.billing.api.webhooks import router as webhook_router
from backend.core.config import get_settings
from backend.health import router as health_router
from backend.rag.api import router as rag_router
from backend.subscription.api.routes import router as subscription_router
from backend.logging import configure_logging
from backend.middleware import (
    RateLimiterMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from backend.observability import PrometheusRequestMiddleware, metrics_router, setup_tracing
from backend.redis.client import get_redis_client


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title="Feature Auth API", version=settings.service_version)
    setup_tracing(app, settings)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    redis_client = get_redis_client()
    high_risk_paths = {"/v1/auth/login", "/v1/auth/2fa/verify", "/v1/auth/recovery-login"}
    app.add_middleware(
        RateLimiterMiddleware,
        redis=redis_client,
        requests=settings.rate_limit_default_requests,
        window_seconds=settings.rate_limit_default_window_seconds,
        prefix=settings.redis_rate_limit_prefix,
        allowlist=settings.rate_limit_allowlist,
        denylist=settings.rate_limit_denylist,
        high_risk_paths=high_risk_paths,
    )
    app.add_middleware(PrometheusRequestMiddleware, excluded_paths={"/metrics"})

    app.include_router(metrics_router())
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(subscription_router)
    app.include_router(billing_router)
    app.include_router(webhook_router)
    app.include_router(account_router)
    app.include_router(admin_router)
    app.include_router(rag_router)

    return app


app = create_app()


__all__ = ["app", "create_app"]
