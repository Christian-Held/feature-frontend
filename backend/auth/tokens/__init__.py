"""Token utilities for authentication flows."""

from __future__ import annotations

import hashlib
import secrets

REFRESH_TOKEN_BYTES = 32


def generate_refresh_token() -> str:
    """Return a URL-safe refresh token string."""

    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_token(value: str) -> str:
    """Hash a token using SHA-256 for persistence."""

    if not value:
        raise ValueError("Token value must be provided")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = ["generate_refresh_token", "hash_token", "REFRESH_TOKEN_BYTES"]
