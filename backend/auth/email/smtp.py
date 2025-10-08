"""SMTP email sending utility."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from backend.core.config import get_settings

logger = structlog.get_logger(__name__)


def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> None:
    """Send an email via SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML version of the email body
        text_body: Plain text version (optional, falls back to stripped HTML)
    """
    settings = get_settings()

    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{settings.email_from_name} <{settings.email_from_address}>"
    msg['To'] = to_email

    # Attach text and HTML versions
    if text_body:
        part1 = MIMEText(text_body, 'plain')
        msg.attach(part1)

    part2 = MIMEText(html_body, 'html')
    msg.attach(part2)

    # Send via SMTP
    try:
        logger.info(
            "smtp.connecting",
            host=settings.smtp_host,
            port=settings.smtp_port,
            use_tls=settings.smtp_use_tls,
        )

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()

            # Authenticate if credentials provided
            smtp_user = getattr(settings, 'smtp_user', None)
            smtp_pass = getattr(settings, 'smtp_pass', None)
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)

            server.send_message(msg)

        logger.info(
            "email.sent",
            to_email=to_email,
            subject=subject,
        )
    except Exception as exc:
        logger.error(
            "email.send_failed",
            to_email=to_email,
            subject=subject,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


__all__ = ["send_email"]
