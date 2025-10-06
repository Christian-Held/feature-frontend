"""JWT service handling ES256 signing and key rotation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey

from backend.core.config import AppConfig, get_settings


@dataclass(slots=True)
class JWTKeyPair:
    kid: str
    private_key: EllipticCurvePrivateKey
    public_pem: bytes


class JWTService:
    """Service responsible for issuing and validating JWTs."""

    def __init__(self, settings: AppConfig):
        self._settings = settings
        self._keys: dict[str, JWTKeyPair] = {}
        self._load_keys()
        if settings.jwt_active_kid not in self._keys:
            raise ValueError(f"Active KID {settings.jwt_active_kid} not found in key set")
        self._active_kid = settings.jwt_active_kid

    def _load_keys(self) -> None:
        private_dir: Path = self._settings.jwt_private_keys_dir
        public_dir: Path | None = self._settings.jwt_public_keys_dir
        if not private_dir.exists():
            raise FileNotFoundError(f"JWT private key directory {private_dir} does not exist")

        for pem_path in private_dir.glob("*.pem"):
            kid = pem_path.stem
            with pem_path.open("rb") as fh:
                private_key = serialization.load_pem_private_key(fh.read(), password=None)
            if not isinstance(private_key, EllipticCurvePrivateKey):
                raise ValueError(f"Key {kid} is not an EC private key")

            public_bytes: bytes
            if public_dir:
                pub_path = public_dir / f"{kid}.pem"
                if not pub_path.exists():
                    raise FileNotFoundError(f"Public key for {kid} not found at {pub_path}")
                public_bytes = pub_path.read_bytes()
            else:
                public_bytes = private_key.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )

            self._keys[kid] = JWTKeyPair(kid=kid, private_key=private_key, public_pem=public_bytes)

    @property
    def active_kid(self) -> str:
        return self._active_kid

    def set_active_kid(self, kid: str) -> None:
        if kid not in self._keys:
            raise ValueError(f"Unknown KID {kid}")
        self._active_kid = kid

    def _encode(self, payload: dict[str, Any], ttl_seconds: int) -> str:
        issued_at = datetime.now(timezone.utc)
        payload = {**payload}
        payload.setdefault("iat", int(issued_at.timestamp()))
        payload.setdefault("exp", int((issued_at + timedelta(seconds=ttl_seconds)).timestamp()))
        payload.setdefault("iss", self._settings.jwt_issuer)
        payload.setdefault("aud", self._settings.jwt_audience)
        payload.setdefault("jti", str(uuid.uuid4()))

        keypair = self._keys[self._active_kid]
        private_bytes = keypair.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        return jwt.encode(
            payload,
            private_bytes,
            algorithm="ES256",
            headers={"kid": keypair.kid},
        )

    def issue_access_token(self, subject: str, claims: dict[str, Any] | None = None) -> str:
        payload = {"sub": subject, "type": "access"}
        if claims:
            payload.update(claims)
        return self._encode(payload, self._settings.jwt_access_ttl_seconds)

    def issue_refresh_token(self, subject: str, claims: dict[str, Any] | None = None) -> str:
        payload = {"sub": subject, "type": "refresh"}
        if claims:
            payload.update(claims)
        return self._encode(payload, self._settings.jwt_refresh_ttl_seconds)

    def decode(self, token: str, *, verify_audience: bool = True) -> Dict[str, Any]:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid or kid not in self._keys:
            raise ValueError("Unknown KID in token header")

        options = {"verify_aud": verify_audience}
        return jwt.decode(
            token,
            self._keys[kid].public_pem,
            algorithms=["ES256"],
            audience=self._settings.jwt_audience if verify_audience else None,
            issuer=self._settings.jwt_issuer,
            options=options,
        )

    def export_public_jwks(self) -> dict[str, Any]:
        """Return JWKS representation of available keys."""

        jwks = {"keys": []}
        for key in self._keys.values():
            public_key = serialization.load_pem_public_key(key.public_pem)
            numbers = public_key.public_numbers()
            jwk = {
                "kty": "EC",
                "crv": "P-256",
                "kid": key.kid,
                "use": "sig",
                "alg": "ES256",
                "x": _b64url_uint(numbers.x),
                "y": _b64url_uint(numbers.y),
            }
            jwks["keys"].append(jwk)
        return jwks


def _b64url_uint(val: int) -> str:
    return jwt.utils.base64url_encode(val.to_bytes((val.bit_length() + 7) // 8, "big")).decode("ascii")


def get_jwt_service() -> JWTService:
    return JWTService(get_settings())


__all__ = ["JWTService", "JWTKeyPair", "get_jwt_service"]

