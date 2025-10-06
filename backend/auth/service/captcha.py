"""Cloudflare Turnstile CAPTCHA verification service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import structlog
from fastapi import HTTPException, status

from backend.core.config import AppConfig

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def _get_client(provided: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    if provided is not None:
        yield provided
        return
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        yield client


async def verify_turnstile(
    *,
    captcha_token: str,
    settings: AppConfig,
    remote_ip: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Validate the CAPTCHA token with Cloudflare Turnstile."""

    if not captcha_token:
        logger.info("captcha.turnstile.missing")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha-Verifizierung fehlgeschlagen.")

    data = {"secret": settings.turnstile_secret_key, "response": captcha_token}
    if remote_ip:
        data["remoteip"] = remote_ip

    async with _get_client(http_client) as client:
        try:
            response = await client.post(settings.turnstile_verify_url, data=data)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            logger.error("captcha.turnstile.http_error", error=str(exc))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Captcha-Verifizierung fehlgeschlagen.") from exc

    payload = response.json()
    if not payload.get("success", False):
        logger.info("captcha.turnstile.failed", errors=payload.get("error-codes", []))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha-Verifizierung fehlgeschlagen.")

    logger.info("captcha.turnstile.verified", action="register", remote_ip=remote_ip)


__all__ = ["verify_turnstile"]
