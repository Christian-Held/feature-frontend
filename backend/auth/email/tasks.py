"""Celery tasks for authentication-related emails."""

from __future__ import annotations

import time

import structlog

from backend.auth.email.celery_app import get_celery_app
from backend.auth.email.templates import render_verification_email
from backend.observability import EMAIL_ENQUEUED, EMAIL_FAILED, EMAIL_SEND_LATENCY

logger = structlog.get_logger(__name__)

celery_app = get_celery_app()


@celery_app.task(name="backend.auth.email.send_verification_email", bind=True)
def send_verification_email_task(self, *, to_email: str, verification_url: str) -> None:
    """Send the verification email to the provided address.

    In production this task would integrate with the transactional email provider.
    For now we log the rendered content so the worker remains side-effect free
    in tests.
    """
    start = time.perf_counter()
    try:
        content = render_verification_email(verification_url)
        logger.info(
            "email.verification.dispatched",
            to_email=to_email,
            subject=content.subject,
            verification_url=verification_url,
        )
    except Exception as exc:  # pragma: no cover - rendering failures rare
        EMAIL_FAILED.inc()
        logger.error("email.verification.failed", error=str(exc), to_email=to_email)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        EMAIL_SEND_LATENCY.observe(duration_ms)


def enqueue_verification_email(to_email: str, verification_url: str) -> None:
    """Enqueue the verification email to be sent asynchronously."""

    EMAIL_ENQUEUED.inc()
    send_verification_email_task.delay(
        to_email=to_email, verification_url=verification_url
    )


__all__ = ["enqueue_verification_email", "send_verification_email_task"]
