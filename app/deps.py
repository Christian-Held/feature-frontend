from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import AppSettings, get_settings
from app.db.engine import get_session_factory


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_app_settings() -> AppSettings:
    return get_settings()


def SettingsDep() -> Depends:  # type: ignore
    return Depends(get_app_settings)


def DbDep() -> Depends:  # type: ignore
    return Depends(get_db)
