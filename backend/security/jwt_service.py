"""JWT issuance and verification with key rotation support."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)
from jwt.algorithms import get_default_algorithms

from backend.core.config import AppConfig, get_settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class JWKMaterial:
    kid: str
    private_key: Optional[EllipticCurvePrivateKey]
    public_key: EllipticCurvePublicKey
    jwk: Dict[str, Any]


def _load_jwk(
    data: str | dict[str, Any],
    *,
    require_private: bool,
) -> JWKMaterial:
    if isinstance(data, str):
        jwk_dict = json.loads(data)
    else:
        jwk_dict = data
    kid = jwk_dict.get("kid")
    if not kid:
        raise ValueError("JWK is missing 'kid'")

    algo = get_default_algorithms()["ES256"]
    key_obj = algo.from_jwk(json.dumps(jwk_dict))
    private_key: EllipticCurvePrivateKey | None = None
    public_key: EllipticCurvePublicKey

    if isinstance(key_obj, EllipticCurvePrivateKey):
        private_key = key_obj
        public_key = key_obj.public_key()
    elif isinstance(key_obj, EllipticCurvePublicKey):
        public_key = key_obj
    else:  # pragma: no cover - unexpected key type
        raise TypeError("Unsupported key type loaded from JWK")

    if require_private and private_key is None:
        raise ValueError("JWK must contain private component for signing")

    if private_key is None and "d" in jwk_dict:
        # When explicitly marked as public-only ensure we drop private fields
        jwk_dict = {k: v for k, v in jwk_dict.items() if k != "d"}

    public_only = {k: v for k, v in jwk_dict.items() if k != "d"}
    public_key = (
        algo.from_jwk(json.dumps(public_only))
        if not isinstance(public_key, EllipticCurvePublicKey)
        else public_key
    )

    return JWKMaterial(
        kid=kid,
        private_key=private_key,
        public_key=public_key,
        jwk=public_only,
    )


class JWTService:
    """Issue and validate JWTs with rotating keys."""

    def __init__(self, settings: AppConfig):
        self._settings = settings
        self._current = _load_jwk(
            settings.jwt_jwk_current,
            require_private=True,
        )
        self._next = (
            _load_jwk(settings.jwt_jwk_next, require_private=False)
            if settings.jwt_jwk_next
            else None
        )
        self._previous = (
            _load_jwk(settings.jwt_jwk_previous, require_private=False)
            if settings.jwt_jwk_previous
            else None
        )

    @property
    def active_kid(self) -> str:
        return self._current.kid

    def issue_access_token(
        self, subject: str, claims: dict[str, Any] | None = None
    ) -> str:
        payload = {"sub": subject, "type": "access"}
        if claims:
            payload.update(claims)
        return self._encode(payload, self._settings.jwt_access_ttl_seconds)

    def issue_refresh_token(
        self, subject: str, claims: dict[str, Any] | None = None
    ) -> str:
        payload = {"sub": subject, "type": "refresh"}
        if claims:
            payload.update(claims)
        return self._encode(payload, self._settings.jwt_refresh_ttl_seconds)

    def export_public_jwks(self) -> dict[str, Any]:
        keys = [self._current.jwk]
        if self._next:
            keys.append(self._next.jwk)
        if self._previous:
            keys.append(self._previous.jwk)
        return {"keys": keys}

    def set_active_kid(self, kid: str) -> None:
        """Set the active signing key by kid for testing and rotation flows."""

        if kid == self._current.kid:
            return
        if self._next and kid == self._next.kid:
            self._previous = self._current
            self._current = self._next
            self._next = None
            return
        if self._previous and kid == self._previous.kid:
            self._current, self._previous = self._previous, self._current
            return
        raise ValueError(f"Unknown key id {kid}")

    def decode(
        self, token: str, *, verify_audience: bool = True
    ) -> Dict[str, Any]:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise ValueError("JWT missing kid header")

        material = self._resolve_key(kid)
        options = {"verify_aud": verify_audience}
        payload = jwt.decode(
            token,
            material.public_key,
            algorithms=["ES256"],
            audience=self._settings.jwt_audience if verify_audience else None,
            issuer=self._settings.jwt_issuer,
            options=options,
        )

        if material is self._previous:
            self._enforce_previous_window(payload)

        return payload

    def _encode(self, payload: dict[str, Any], ttl_seconds: int) -> str:
        issued_at = _utcnow()
        claims = {
            **payload,
            "iat": int(issued_at.timestamp()),
            "exp": int(
                (issued_at + timedelta(seconds=ttl_seconds)).timestamp()
            ),
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "jti": str(uuid.uuid4()),
        }
        if self._current.private_key is None:  # pragma: no cover - defensive
            raise RuntimeError("Active JWK lacks private component")
        return jwt.encode(
            claims,
            self._current.private_key,
            algorithm="ES256",
            headers={"kid": self._current.kid},
        )

    def _resolve_key(self, kid: str) -> JWKMaterial:
        if kid == self._current.kid:
            return self._current
        if self._next and kid == self._next.kid:
            return self._next
        if self._previous and kid == self._previous.kid:
            return self._previous
        raise ValueError(f"Unknown KID {kid}")

    def _enforce_previous_window(self, payload: Dict[str, Any]) -> None:
        token_type = payload.get("type")
        if token_type != "refresh":  # nosec B105 - allow legacy access tokens
            return
        issued_at = payload.get("iat")
        if not issued_at:
            raise ValueError(
                "Token missing issued-at for previous key validation"
            )
        issued_dt = datetime.fromtimestamp(int(issued_at), tz=timezone.utc)
        if _utcnow() - issued_dt > timedelta(
            seconds=self._settings.jwt_previous_grace_seconds
        ):
            raise ValueError(
                "Token signed with previous key is outside grace window"
            )


def get_jwt_service() -> JWTService:
    return JWTService(get_settings())


__all__ = ["JWTService", "get_jwt_service"]
