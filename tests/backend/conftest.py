from __future__ import annotations

from pathlib import Path

import pytest
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments
    serialization = None  # type: ignore[assignment]
    ec = None  # type: ignore[assignment]


STATIC_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgYzvF5QGOObz7qJmd
5Aq71+v+P6lZ2dWr4RVjuBTBBPGhRANCAASkDRF24Iyxn8ddchArm8KTW9nW1wdO
6Xd7wOpEtVCNrECD8/TvQypVeeLh5aHTmurroCuVNz3nEncB3Gm/y4pe4A4
-----END PRIVATE KEY-----
"""

STATIC_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEpA0RduCMsZ/HXXIQK5vCk1vZ1tcHTul3
e8DqRLVQjaxAg/P070MqVXni4eWh05rq6ArlTc95xJ3Adxpv8uKXuA==
-----END PUBLIC KEY-----
"""

from backend.core import config


@pytest.fixture
def settings_env(monkeypatch, tmp_path: Path):
    private_dir = tmp_path / "jwt"
    public_dir = private_dir / "public"
    private_dir.mkdir()
    public_dir.mkdir()

    for kid in ("current", "rotated"):
        if serialization and ec:
            private_key = ec.generate_private_key(ec.SECP256R1())
            private_pem = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            public_pem = private_key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        else:
            private_pem = STATIC_PRIVATE_KEY.encode("utf-8")
            public_pem = STATIC_PUBLIC_KEY.encode("utf-8")

        (private_dir / f"{kid}.pem").write_bytes(private_pem)
        (public_dir / f"{kid}.pem").write_bytes(public_pem)

    env_vars = {
        "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/testdb",
        "REDIS_URL": "redis://localhost:6379/0",
        "JWT_ACTIVE_KID": "current",
        "JWT_PRIVATE_KEYS_DIR": str(private_dir),
        "JWT_PUBLIC_KEYS_DIR": str(public_dir),
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
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    config.get_settings.cache_clear()
    settings = config.get_settings()
    yield settings
    config.get_settings.cache_clear()

    for key in env_vars:
        monkeypatch.delenv(key, raising=False)
