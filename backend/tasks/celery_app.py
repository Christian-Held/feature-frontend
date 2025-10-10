"""Celery application configuration for the unified backend."""

from __future__ import annotations

from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "feature_backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend or settings.redis_url,
)

celery_app.conf.task_routes = {
    "backend.tasks.workers.job_worker.execute_job": {"queue": "jobs"},
    "app.workers.job_worker.execute_job": {"queue": "jobs"},
}
celery_app.conf.task_default_queue = "jobs"
celery_app.conf.task_default_exchange = "jobs"
celery_app.conf.task_default_routing_key = "jobs"

celery_app.autodiscover_tasks(["backend.tasks", "app.workers"])

__all__ = ["celery_app"]
