"""Helpers for TOTP-based multi-factor authentication flows."""

from __future__ import annotations

import base64
import io
import secrets
from typing import Iterable, Tuple

import pyotp
import qrcode

from backend.auth.tokens import hash_token

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LENGTH = 10


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_otpauth_url(*, secret: str, email: str, issuer: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_svg(data: str) -> str:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def verify_totp(*, secret: str, otp: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(otp, valid_window=1)


def generate_recovery_codes() -> Tuple[list[str], list[str]]:
    raw_codes: list[str] = []
    hashed_codes: list[str] = []
    for _ in range(RECOVERY_CODE_COUNT):
        code = "-".join(
            secrets.token_hex(2).upper() for _ in range(3)
        )
        raw_codes.append(code)
        hashed_codes.append(hash_token(code))
    return raw_codes, hashed_codes


def rotate_recovery_codes(existing: Iterable[str], used_hash: str) -> list[str]:
    remaining = [code for code in existing if code != used_hash]
    return remaining


__all__ = [
    "generate_totp_secret",
    "build_otpauth_url",
    "generate_qr_svg",
    "verify_totp",
    "generate_recovery_codes",
    "rotate_recovery_codes",
    "RECOVERY_CODE_COUNT",
    "RECOVERY_CODE_LENGTH",
]
