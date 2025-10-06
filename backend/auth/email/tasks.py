"""Celery tasks for authentication-related emails."""

from __future__ import annotations

import structlog

from backend.auth.email.celery_app import get_celery_app
from backend.auth.email.templates import render_verification_email

logger = structlog.get_logger(__name__)

celery_app = get_celery_app()


@celery_app.task(name="backend.auth.email.send_verification_email", bind=True)
def send_verification_email_task(self, *, to_email: str, verification_url: str) -> None:
    """Send the verification email to the provided address.

    In production this task would integrate with the transactional email provider.
    For now we log the rendered content so the worker remains side-effect free
    in tests.
    """

    content = render_verification_email(verification_url)
    logger.info(
        "email.verification.dispatched",
        to_email=to_email,
        subject=content.subject,
        verification_url=verification_url,
    )


def enqueue_verification_email(to_email: str, verification_url: str) -> None:
    """Enqueue the verification email to be sent asynchronously."""

    send_verification_email_task.delay(to_email=to_email, verification_url=verification_url)


__all__ = ["enqueue_verification_email", "send_verification_email_task"]
