from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from backend.core import config


@pytest.fixture
def settings_env(monkeypatch, tmp_path: Path):
    private_dir = tmp_path / "jwt"
    public_dir = private_dir / "public"
    private_dir.mkdir()
    public_dir.mkdir()

    for kid in ("current", "rotated"):
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
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    config.get_settings.cache_clear()
    settings = config.get_settings()
    yield settings
    config.get_settings.cache_clear()

    for key in env_vars:
        monkeypatch.delenv(key, raising=False)
