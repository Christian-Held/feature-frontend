from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_port: int = Field(3000, alias="APP_PORT")
    redis_url: str = Field(..., alias="REDIS_URL")
    db_path: Path = Field(Path("./data/orchestrator.db"), alias="DB_PATH")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    model_cto: str = Field("gpt-4.1-mini", alias="MODEL_CTO")
    model_coder: str = Field("gpt-4.1", alias="MODEL_CODER")
    github_token: str = Field("", alias="GITHUB_TOKEN")
    github_owner: str = Field("", alias="GITHUB_OWNER")
    github_repo: str = Field("", alias="GITHUB_REPO")
    budget_usd_max: float = Field(5.0, alias="BUDGET_USD_MAX")
    max_requests: int = Field(300, alias="MAX_REQUESTS")
    max_wallclock_minutes: int = Field(720, alias="MAX_WALLCLOCK_MINUTES")
    allow_direct_push: bool = Field(False, alias="ALLOW_DIRECT_PUSH")
    allow_unsafe_automerge: bool = Field(False, alias="ALLOW_UNSAFE_AUTOMERGE")
    merge_conflict_behavior: str = Field("pr", alias="MERGE_CONFLICT_BEHAVIOR")
    dry_run: bool = Field(False, alias="DRY_RUN")
    log_level: str = Field("info", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    @property
    def database_uri(self) -> str:
        return f"sqlite:///{self.db_path}"


class BudgetLimits(BaseModel):
    budget_usd_max: float
    max_requests: int
    max_wallclock_minutes: int


@lru_cache
def get_settings() -> AppSettings:
    settings = AppSettings()
    db_dir = settings.db_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    return settings


@lru_cache
def get_budget_limits() -> BudgetLimits:
    settings = get_settings()
    return BudgetLimits(
        budget_usd_max=settings.budget_usd_max,
        max_requests=settings.max_requests,
        max_wallclock_minutes=settings.max_wallclock_minutes,
    )


def get_env_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}
