"""Legacy compatibility wrapper for the Celery application."""

from backend.tasks.celery_app import celery_app  # re-export

__all__ = ["celery_app"]
