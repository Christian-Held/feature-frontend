"""Celery application setup for RAG crawling tasks."""

from __future__ import annotations

from functools import lru_cache

from celery import Celery

from backend.core.config import get_settings


@lru_cache(maxsize=1)
def get_celery_app() -> Celery:
    settings = get_settings()
    celery_app = Celery(
        "backend.rag",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    celery_app.conf.task_default_queue = "rag-crawl"
    celery_app.conf.task_default_exchange = "rag-crawl"
    celery_app.conf.task_default_routing_key = "rag-crawl"
    return celery_app


__all__ = ["get_celery_app"]
