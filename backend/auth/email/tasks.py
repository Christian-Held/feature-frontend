"""Celery tasks for authentication-related emails."""

from __future__ import annotations

import time

import structlog

from backend.auth.email.celery_app import get_celery_app
from backend.auth.email.smtp import send_email
from backend.auth.email.templates import render_verification_email, render_password_reset_email
from backend.observability import EMAIL_ENQUEUED, EMAIL_FAILED, EMAIL_SEND_LATENCY

logger = structlog.get_logger(__name__)

celery_app = get_celery_app()


@celery_app.task(name="backend.auth.email.send_verification_email", bind=True)
def send_verification_email_task(self, *, to_email: str, verification_url: str) -> None:
    """Send the verification email to the provided address via SMTP."""
    start = time.perf_counter()
    try:
        content = render_verification_email(verification_url)

        # Send email via SMTP
        send_email(
            to_email=to_email,
            subject=content.subject,
            html_body=content.html_body,
            text_body=content.text_body,
        )

        logger.info(
            "email.verification.sent",
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


@celery_app.task(name="backend.auth.email.send_password_reset_email", bind=True)
def send_password_reset_email_task(self, *, to_email: str, reset_url: str) -> None:
    """Send the password reset email to the provided address via SMTP."""
    start = time.perf_counter()
    try:
        content = render_password_reset_email(reset_url)

        # Send email via SMTP
        send_email(
            to_email=to_email,
            subject=content.subject,
            html_body=content.html_body,
            text_body=content.text_body,
        )

        logger.info(
            "email.password_reset.sent",
            to_email=to_email,
            subject=content.subject,
            reset_url=reset_url,
        )
    except Exception as exc:  # pragma: no cover - rendering failures rare
        EMAIL_FAILED.inc()
        logger.error("email.password_reset.failed", error=str(exc), to_email=to_email)
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


def enqueue_password_reset_email(to_email: str, reset_url: str) -> None:
    """Enqueue the password reset email to be sent asynchronously."""

    EMAIL_ENQUEUED.inc()
    send_password_reset_email_task.delay(
        to_email=to_email, reset_url=reset_url
    )


__all__ = ["enqueue_verification_email", "enqueue_password_reset_email", "send_verification_email_task", "send_password_reset_email_task"]
