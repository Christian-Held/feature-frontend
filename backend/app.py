"""Unified FastAPI application for the Feature platform."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.account.api import router as account_router
from backend.admin.api import router as admin_router
from backend.auth.api import router as auth_router
from backend.billing.api.routes import router as billing_router
from backend.billing.api.webhooks import router as webhook_router
from backend.core.config import get_settings
from backend.health import router as health_router
from backend.logging import configure_logging
from backend.middleware import (
    RateLimiterMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from backend.observability import (
    PrometheusRequestMiddleware,
    metrics_router,
    setup_tracing,
)
from backend.rag.api import router as rag_router
from backend.redis.client import get_redis_client
from backend.subscription.api.routes import router as subscription_router

# Legacy orchestrator imports (will be migrated fully into backend namespace).
from app.agents.prompts import parse_agents_file
from app.core.config import get_settings as get_orchestrator_settings
from app.core.logging import configure_logging as configure_orchestrator_logging
from app.core.logging import get_logger as get_orchestrator_logger
from app.db.engine import get_engine as get_orchestrator_engine
from app.db.models import Base as OrchestratorBase
from app.routers import context_api, events, files, jobs, memory, settings, tasks
from app.routers.health import router as orchestrator_health_router


def _load_environment_files() -> None:
    """Load environment variables from both root and backend .env files."""

    project_root = Path(__file__).resolve().parent.parent
    root_env = project_root / ".env"
    backend_env = project_root / "backend" / ".env"

    load_dotenv(root_env, override=False)
    load_dotenv(backend_env, override=False)


def _configure_cors(app: FastAPI, origins: Iterable[str]) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    _load_environment_files()

    settings = get_settings()
    configure_logging(settings)

    orchestrator_settings = get_orchestrator_settings()
    configure_orchestrator_logging(orchestrator_settings.log_level)
    orchestrator_logger = get_orchestrator_logger(__name__)

    app = FastAPI(title="Feature Platform API", version=settings.service_version)
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

    _configure_cors(
        app,
        origins={
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        },
    )

    # Shared routers
    app.include_router(metrics_router())
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(subscription_router)
    app.include_router(billing_router)
    app.include_router(webhook_router)
    app.include_router(account_router)
    app.include_router(admin_router)
    app.include_router(rag_router)

    # Legacy orchestrator routers
    app.include_router(orchestrator_health_router)
    app.include_router(tasks.router)
    app.include_router(jobs.router)
    app.include_router(context_api.router)
    app.include_router(memory.router)
    app.include_router(settings.router)
    app.include_router(files.router)
    app.include_router(events.router)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir, check_dir=False), name="static")

    widget_path = static_dir / "widget.js"

    @app.get("/widget.js", include_in_schema=False)
    async def widget_bundle() -> FileResponse:
        return FileResponse(widget_path)

    @app.on_event("startup")
    async def startup_event() -> None:
        orchestrator_logger.info("startup")
        engine = get_orchestrator_engine()
        OrchestratorBase.metadata.create_all(bind=engine)
        app.state.agents_spec = parse_agents_file()

    return app


app = create_app()


__all__ = ["app", "create_app"]
