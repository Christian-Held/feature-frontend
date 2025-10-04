from __future__ import annotations

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.engine import get_engine
from app.db.models import Base
from app.agents.prompts import parse_agents_file

from .routers import health, jobs, tasks

logger = get_logger(__name__)


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="Auto Dev Orchestrator", version="0.1.0")

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("startup")
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        app.state.agents_spec = parse_agents_file()

    app.include_router(health.router)
    app.include_router(tasks.router)
    app.include_router(jobs.router)

    return app


app = create_application()
