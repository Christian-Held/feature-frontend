from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "auto_dev_orchestrator",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.task_routes = {
    "app.workers.job_worker.execute_job": {"queue": "jobs"},
}

celery_app.autodiscover_tasks(["app.workers"])
