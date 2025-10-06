"""Pydantic schemas for registration and verification flows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class RegistrationRequest(BaseModel):
    """Input payload for new account registration."""

    email: EmailStr
    password: SecretStr = Field(..., min_length=12)
    captcha_token: str = Field(..., alias="captchaToken", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class RegistrationResponse(BaseModel):
    """Response payload acknowledging registration submission."""

    message: str


class ResendVerificationRequest(BaseModel):
    """Input payload for resending verification email."""

    email: EmailStr


class ResendVerificationResponse(BaseModel):
    """Response payload for resend endpoint."""

    message: str


__all__ = [
    "RegistrationRequest",
    "RegistrationResponse",
    "ResendVerificationRequest",
    "ResendVerificationResponse",
]
