"""Service layer exports for auth flows."""

from importlib import import_module
from typing import Any

__all__ = [
    "register_user",
    "resend_verification",
    "complete_email_verification",
    "validate_email_verification_token",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        module = import_module("backend.auth.service.registration_service")
        return getattr(module, name)
    raise AttributeError(name)

