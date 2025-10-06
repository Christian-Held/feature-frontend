"""Schema exports for the auth service."""

from .registration import (
    RegistrationRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
)

__all__ = [
    "RegistrationRequest",
    "RegistrationResponse",
    "ResendVerificationRequest",
    "ResendVerificationResponse",
]
