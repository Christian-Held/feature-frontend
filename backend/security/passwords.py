"""Argon2id password hashing utilities."""

from __future__ import annotations

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.core.config import AppConfig, get_settings


class PasswordHashingService:
    """Service encapsulating Argon2id hashing and verification."""

    def __init__(self, settings: AppConfig):
        self._hasher = PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
            hash_len=settings.argon2_hash_len,
        )

    def hash(self, password: str) -> str:
        if not password:
            raise ValueError("Password must be provided for hashing")
        return self._hasher.hash(password)

    def verify(self, hashed_password: str, password: str) -> bool:
        if not hashed_password:
            raise ValueError("Stored password hash must be provided")
        try:
            return self._hasher.verify(hashed_password, password)
        except VerifyMismatchError:
            return False


@lru_cache(maxsize=1)
def get_password_service() -> PasswordHashingService:
    """Return a cached password hashing service instance."""

    return PasswordHashingService(get_settings())


__all__ = ["PasswordHashingService", "get_password_service"]

