"""Application configuration module for the authentication platform foundations."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
        env_prefix="",
    )

    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    database_url: str = Field(validation_alias="DATABASE_URL")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    redis_url: str = Field(validation_alias="REDIS_URL")
    redis_rate_limit_prefix: str = Field(
        default="rate_limit", validation_alias="REDIS_RATE_LIMIT_PREFIX"
    )

    rate_limit_default_requests: int = Field(
        default=60, validation_alias="RATE_LIMIT_DEFAULT_REQUESTS"
    )
    rate_limit_default_window_seconds: int = Field(
        default=60, validation_alias="RATE_LIMIT_DEFAULT_WINDOW_SECONDS"
    )
    rate_limit_allowlist: List[str] = Field(
        default_factory=list, validation_alias="RATE_LIMIT_ALLOWLIST"
    )
    rate_limit_denylist: List[str] = Field(
        default_factory=list, validation_alias="RATE_LIMIT_DENYLIST"
    )

    jwt_jwk_current: str = Field(validation_alias="JWT_JWK_CURRENT")
    jwt_jwk_next: str | None = Field(default=None, validation_alias="JWT_JWK_NEXT")
    jwt_jwk_previous: str | None = Field(
        default=None, validation_alias="JWT_JWK_PREVIOUS"
    )
    jwt_previous_grace_seconds: int = Field(
        default=24 * 3600, validation_alias="JWT_PREVIOUS_GRACE_SECONDS"
    )
    jwt_access_ttl_seconds: int = Field(
        default=420, validation_alias="JWT_ACCESS_TTL_SECONDS"
    )
    jwt_refresh_ttl_seconds: int = Field(
        default=30 * 24 * 3600, validation_alias="JWT_REFRESH_TTL_SECONDS"
    )
    jwt_issuer: str = Field(default="feature-auth", validation_alias="JWT_ISSUER")
    jwt_audience: str = Field(
        default="feature-auth-clients", validation_alias="JWT_AUDIENCE"
    )

    argon2_time_cost: int = Field(default=3, validation_alias="ARGON2_TIME_COST")
    argon2_memory_cost: int = Field(
        default=64 * 1024, validation_alias="ARGON2_MEMORY_COST"
    )
    argon2_parallelism: int = Field(default=4, validation_alias="ARGON2_PARALLELISM")
    argon2_hash_len: int = Field(default=32, validation_alias="ARGON2_HASH_LEN")

    turnstile_secret_key: str = Field(validation_alias="TURNSTILE_SECRET_KEY")
    turnstile_verify_url: str = Field(
        default="https://challenges.cloudflare.com/turnstile/v0/siteverify",
        validation_alias="TURNSTILE_VERIFY_URL",
    )

    celery_broker_url: str = Field(validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(
        default=None, validation_alias="CELERY_RESULT_BACKEND"
    )

    email_from_address: str = Field(validation_alias="EMAIL_FROM_ADDRESS")
    email_from_name: str = Field(
        default="Feature Auth", validation_alias="EMAIL_FROM_NAME"
    )
    frontend_base_url: str = Field(validation_alias="FRONTEND_BASE_URL")
    api_base_url: str = Field(validation_alias="API_BASE_URL")
    email_verification_secret: str = Field(validation_alias="EMAIL_VERIFICATION_SECRET")

    service_name: str = Field(default="auth", validation_alias="SERVICE_NAME")
    service_version: str = Field(default="0.1.0", validation_alias="SERVICE_VERSION")
    service_region: str = Field(default="us-east-1", validation_alias="SERVICE_REGION")
    otel_exporter_endpoint: str | None = Field(
        default=None, validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_exporter_insecure: bool = Field(
        default=True, validation_alias="OTEL_EXPORTER_OTLP_INSECURE"
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_redact_fields: List[str] = Field(
        default_factory=lambda: ["password", "token", "secret"],
        validation_alias="LOG_REDACT_FIELDS",
    )

    admin_email: str = Field(validation_alias="ADMIN_EMAIL")
    admin_password: str = Field(validation_alias="ADMIN_PASSWORD")

    encryption_keys: Dict[str, str] = Field(
        default_factory=dict, validation_alias="ENCRYPTION_KEYS"
    )
    encryption_active_key: str = Field(validation_alias="ENCRYPTION_KEY_ACTIVE")

    smtp_host: str = Field(default="localhost", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")
    smtp_user: str | None = Field(default=None, validation_alias="SMTP_USER")
    smtp_pass: str | None = Field(default=None, validation_alias="SMTP_PASS")

    # Stripe Configuration
    stripe_api_key: str = Field(validation_alias="STRIPE_API_KEY")
    stripe_webhook_secret: str = Field(validation_alias="STRIPE_WEBHOOK_SECRET")
    stripe_publishable_key: str = Field(validation_alias="STRIPE_PUBLISHABLE_KEY")

    # RAG Configuration
    qdrant_url: str | None = Field(default=None, validation_alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, validation_alias="QDRANT_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    rag_task_execution_mode: str = Field(
        default="inline", validation_alias="RAG_TASK_EXECUTION_MODE"
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _uppercase_log_level(cls, value):
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("rate_limit_allowlist", "rate_limit_denylist", mode="before")
    @classmethod
    def _split_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item and item.strip()]
        return value

    @field_validator("encryption_keys", mode="before")
    @classmethod
    def _parse_encryption_keys(cls, value):
        if value is None or value == "":
            return {}
        if isinstance(value, str):
            return json.loads(value)
        return value

    @field_validator("rag_task_execution_mode", mode="before")
    @classmethod
    def _validate_task_execution_mode(cls, value):
        if value is None or value == "":
            return "inline"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized not in {"inline", "celery"}:
                raise ValueError(
                    "RAG_TASK_EXECUTION_MODE must be either 'inline' or 'celery'"
                )
            return normalized
        raise ValueError("Invalid RAG_TASK_EXECUTION_MODE value")

    @computed_field
    def jwt_access_ttl_minutes(self) -> int:
        return self.jwt_access_ttl_seconds // 60


@lru_cache(maxsize=1)
def get_settings() -> AppConfig:
    """Return a cached instance of the application settings.

    Always load .env from backend/.env, ignoring any .env in project root.
    This ensures the backend config is isolated from other project configs.
    """
    project_root = Path(__file__).parent.parent.parent
    root_env = project_root / ".env"
    backend_env = project_root / "backend" / ".env"

    load_dotenv(root_env, override=False)
    load_dotenv(backend_env, override=False)

    return AppConfig(_env_file=str(backend_env))


__all__ = ["AppConfig", "get_settings"]
