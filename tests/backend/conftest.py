from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import pytest

from backend.core import config
from backend.scripts.jwk_generate import create_jwk


_DEFAULT_CURRENT_JWK = create_jwk(kid="test-current")
_DEFAULT_NEXT_JWK = create_jwk(kid="test-next")
_DEFAULT_PREVIOUS_JWK = create_jwk(kid="test-previous")
_DEFAULT_ENCRYPTION_KEYS = {
    "v1": base64.b64encode(b"a" * 32).decode("utf-8"),
    "v0": base64.b64encode(b"b" * 32).decode("utf-8"),
}

os.environ.setdefault("JWT_JWK_CURRENT", json.dumps(_DEFAULT_CURRENT_JWK))
os.environ.setdefault("JWT_JWK_NEXT", json.dumps(_DEFAULT_NEXT_JWK))
os.environ.setdefault("JWT_JWK_PREVIOUS", json.dumps(_DEFAULT_PREVIOUS_JWK))
os.environ.setdefault("ENCRYPTION_KEYS", json.dumps(_DEFAULT_ENCRYPTION_KEYS))
os.environ.setdefault("ENCRYPTION_KEY_ACTIVE", "v1")


@pytest.fixture
def settings_env(monkeypatch, tmp_path: Path):
    current_jwk = create_jwk(kid="current")
    next_jwk = create_jwk(kid="next")
    previous_jwk = create_jwk(kid="previous")

    encryption_keys = {
        "v1": base64.b64encode(b"a" * 32).decode("utf-8"),
        "v0": base64.b64encode(b"b" * 32).decode("utf-8"),
    }

    env_vars = {
        "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/testdb",
        "REDIS_URL": "redis://localhost:6379/0",
        "JWT_JWK_CURRENT": json.dumps(current_jwk),
        "JWT_JWK_NEXT": json.dumps(next_jwk),
        "JWT_JWK_PREVIOUS": json.dumps(previous_jwk),
        "JWT_PREVIOUS_GRACE_SECONDS": "86400",
        "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_PASSWORD": "ChangeMe123!",
        "RATE_LIMIT_DEFAULT_REQUESTS": "5",
        "RATE_LIMIT_DEFAULT_WINDOW_SECONDS": "60",
        "ARGON2_TIME_COST": "2",
        "ARGON2_MEMORY_COST": "32768",
        "ARGON2_PARALLELISM": "2",
        "TURNSTILE_SECRET_KEY": "test-turnstile-secret",
        "CELERY_BROKER_URL": "memory://",
        "CELERY_RESULT_BACKEND": "rpc://",
        "EMAIL_FROM_ADDRESS": "no-reply@example.com",
        "EMAIL_FROM_NAME": "Feature Auth",
        "FRONTEND_BASE_URL": "https://app.example.com",
        "API_BASE_URL": "https://api.example.com",
        "EMAIL_VERIFICATION_SECRET": "verification-secret",
        "ENCRYPTION_KEYS": json.dumps(encryption_keys),
        "ENCRYPTION_KEY_ACTIVE": "v1",
        "SMTP_HOST": "localhost",
        "SMTP_PORT": "1025",
        "SMTP_USE_TLS": "false",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    config.get_settings.cache_clear()
    settings = config.get_settings()
    yield settings
    config.get_settings.cache_clear()

    for key in env_vars:
        monkeypatch.delenv(key, raising=False)
