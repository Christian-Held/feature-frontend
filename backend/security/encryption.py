"""Envelope encryption utilities with key rotation."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.core.config import AppConfig, get_settings


@dataclass(slots=True)
class EncryptionKey:
    version: str
    key: bytes


class EncryptionService:
    """Encrypt and decrypt secrets with AES-GCM and version metadata."""

    def __init__(self, settings: AppConfig):
        if not settings.encryption_keys:
            raise ValueError("ENCRYPTION_KEYS is not configured")
        self._keys: Dict[str, EncryptionKey] = {}
        for version, encoded in settings.encryption_keys.items():
            try:
                key_bytes = base64.b64decode(encoded)
            except Exception as exc:  # pragma: no cover - invalid config
                raise ValueError(f"Invalid key material for version {version}") from exc
            if len(key_bytes) not in (16, 24, 32):
                raise ValueError(f"Encryption key {version} must be 128/192/256 bits")
            self._keys[version] = EncryptionKey(version=version, key=key_bytes)
        if settings.encryption_active_key not in self._keys:
            raise ValueError("Active encryption key not found in key set")
        self._active_version = settings.encryption_active_key

    @property
    def active_version(self) -> str:
        return self._active_version

    def encrypt_bytes(self, plaintext: bytes) -> bytes:
        record = self._encrypt(plaintext)
        return json.dumps(record).encode("utf-8")

    def decrypt_bytes(self, payload: bytes) -> bytes:
        data = json.loads(payload.decode("utf-8"))
        return self._decrypt(data)

    def encrypt_json(self, payload: Any) -> dict[str, str]:
        plaintext = json.dumps(payload).encode("utf-8")
        return self._encrypt(plaintext)

    def decrypt_json(self, payload: dict[str, str]) -> Any:
        plaintext = self._decrypt(payload)
        return json.loads(plaintext.decode("utf-8"))

    def _encrypt(self, plaintext: bytes) -> dict[str, str]:
        key = self._keys[self._active_version]
        nonce = os.urandom(12)
        aes = AESGCM(key.key)
        ciphertext = aes.encrypt(nonce, plaintext, None)
        return {
            "version": key.version,
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
        }

    def _decrypt(self, payload: dict[str, str]) -> bytes:
        version = payload.get("version")
        if not version or version not in self._keys:
            raise ValueError("Unknown encryption key version")
        nonce = base64.b64decode(payload["nonce"])
        ciphertext = base64.b64decode(payload["ciphertext"])
        aes = AESGCM(self._keys[version].key)
        return aes.decrypt(nonce, ciphertext, None)


def get_encryption_service() -> EncryptionService:
    return EncryptionService(get_settings())


__all__ = ["EncryptionService", "get_encryption_service"]
