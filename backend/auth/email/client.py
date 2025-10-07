"""Simple SMTP client helpers for health checks."""

from __future__ import annotations

import asyncio
import smtplib

from backend.core.config import AppConfig


async def smtp_ping(settings: AppConfig) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _ping_sync, settings)


def _ping_sync(settings: AppConfig) -> bool:
    try:
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as client:
                client.starttls()
                client.noop()
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as client:
                client.noop()
        return True
    except Exception:
        return False


__all__ = ["smtp_ping"]
