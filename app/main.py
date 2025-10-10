from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.engine import get_engine
from app.db.models import Base
from app.agents.prompts import parse_agents_file

from .routers import context_api, events, files, health, jobs, memory, settings, tasks

from dotenv import load_dotenv
load_dotenv()


logger = get_logger(__name__)


def create_application() -> FastAPI:
    app_settings = get_settings()
    configure_logging(app_settings.log_level)
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
    app.include_router(context_api.router)
    app.include_router(memory.router)
    app.include_router(settings.router)
    app.include_router(files.router)
    app.include_router(events.router)

    static_dir = Path(__file__).parent / "static"
    static_files_app = StaticFiles(directory=static_dir, check_dir=False)
    app.mount("/static", static_files_app, name="static")

    @app.get("/{static_file_path:path}", include_in_schema=False)
    async def serve_public_static(static_file_path: str):
        if not static_file_path:
            raise HTTPException(status_code=404)

        requested_path = (static_dir / static_file_path).resolve()
        try:
            requested_path.relative_to(static_dir.resolve())
        except ValueError as exc:  # pragma: no cover - safety guard
            raise HTTPException(status_code=404) from exc

        if not requested_path.is_file():
            raise HTTPException(status_code=404)

        return FileResponse(requested_path)

    return app


app = create_application()
