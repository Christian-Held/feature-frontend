"""Pydantic request and response models for authentication APIs."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, model_validator


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


class LoginRequest(BaseModel):
    """Payload for initiating a password-based login."""

    email: EmailStr
    password: SecretStr
    captcha_token: str | None = Field(default=None, alias="captchaToken")

    model_config = ConfigDict(populate_by_name=True)


class LoginResponse(BaseModel):
    """Response for login attempts, optionally requiring MFA verification."""

    requires_2fa: bool = Field(default=False, alias="requires2fa")
    challenge_id: str | None = Field(default=None, alias="challengeId")
    access_token: str | None = Field(default=None, alias="accessToken")
    refresh_token: str | None = Field(default=None, alias="refreshToken")
    expires_in: int | None = Field(default=None, alias="expiresIn")

    model_config = ConfigDict(populate_by_name=True)


class TwoFAVerifyRequest(BaseModel):
    """Payload for verifying a TOTP challenge during login."""

    challenge_id: str = Field(..., alias="challengeId")
    otp: str
    captcha_token: str | None = Field(default=None, alias="captchaToken")

    model_config = ConfigDict(populate_by_name=True)


class TokenPairResponse(BaseModel):
    """Standard token pair response with expiry metadata."""

    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    expires_in: int = Field(..., alias="expiresIn")

    model_config = ConfigDict(populate_by_name=True)


class RefreshRequest(BaseModel):
    """Payload for rotating a refresh token."""

    refresh_token: str = Field(..., alias="refreshToken")

    model_config = ConfigDict(populate_by_name=True)


class LogoutResponse(BaseModel):
    """Simple acknowledgement for logout requests."""

    message: str


class TwoFAEnableInitResponse(BaseModel):
    """Response for initiating 2FA setup."""

    secret: str
    otpauth_url: str = Field(..., alias="otpauthUrl")
    qr_svg: str = Field(..., alias="qrSvg")
    challenge_id: str = Field(..., alias="challengeId")

    model_config = ConfigDict(populate_by_name=True)


class TwoFAEnableCompleteRequest(BaseModel):
    """Payload for completing 2FA enablement."""

    challenge_id: str = Field(..., alias="challengeId")
    otp: str

    model_config = ConfigDict(populate_by_name=True)


class TwoFAEnableCompleteResponse(BaseModel):
    """Response containing the generated recovery codes."""

    recovery_codes: List[str] = Field(..., alias="recoveryCodes")

    model_config = ConfigDict(populate_by_name=True)


class TwoFADisableRequest(BaseModel):
    """Payload for disabling 2FA."""

    password: SecretStr
    otp: str


class TwoFADisableResponse(BaseModel):
    """Acknowledgement of successful 2FA disable."""

    message: str


class RecoveryLoginRequest(BaseModel):
    """Payload for performing a recovery login."""

    email: EmailStr
    recovery_code: str = Field(..., alias="recoveryCode")
    password: SecretStr | None = None
    challenge_id: str | None = Field(default=None, alias="challengeId")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate_credentials(self) -> "RecoveryLoginRequest":
        if not (self.password or self.challenge_id):
            raise ValueError("password or challengeId must be provided")
        return self


class RecoveryLoginResponse(TokenPairResponse):
    """Token response for a successful recovery login."""

    pass


class TwoFAVerifyResponse(TokenPairResponse):
    """Token response issued after successful OTP verification."""

    pass


class RefreshResponse(TokenPairResponse):
    """Token response for refresh endpoint."""

    pass


__all__ = [
    "LoginRequest",
    "LoginResponse",
    "TwoFAVerifyRequest",
    "TwoFAVerifyResponse",
    "TwoFAEnableInitResponse",
    "TwoFAEnableCompleteRequest",
    "TwoFAEnableCompleteResponse",
    "TwoFADisableRequest",
    "TwoFADisableResponse",
    "RecoveryLoginRequest",
    "RecoveryLoginResponse",
    "TokenPairResponse",
    "RefreshRequest",
    "RefreshResponse",
    "LogoutResponse",
    "RegistrationRequest",
    "RegistrationResponse",
    "ResendVerificationRequest",
    "ResendVerificationResponse",
]
