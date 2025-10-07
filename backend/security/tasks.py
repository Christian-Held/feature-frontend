"""Celery tasks related to security maintenance."""

from __future__ import annotations

import json

import structlog

from backend.auth.email.celery_app import get_celery_app
from backend.db.models.user import User
from backend.db.session import session_scope
from backend.security.encryption import get_encryption_service

logger = structlog.get_logger(__name__)

celery_app = get_celery_app()


@celery_app.task(name="backend.security.reencrypt_sensitive", bind=True)
def reencrypt_sensitive_task(self) -> int:
    """Re-encrypt MFA secrets and recovery codes with the active key version."""

    encryption = get_encryption_service()
    updated = 0
    with session_scope() as session:
        users = session.query(User).filter(  # type: ignore[attr-defined]
            (User.mfa_secret.isnot(None)) | (User.recovery_codes.isnot(None))
        )
        for user in users:
            rotated = False
            if user.mfa_secret:
                payload = json.loads(user.mfa_secret.decode("utf-8"))
                if payload.get("version") != encryption.active_version:
                    secret = encryption.decrypt_bytes(user.mfa_secret)
                    user.mfa_secret = encryption.encrypt_bytes(secret)
                    rotated = True
            if user.recovery_codes:
                payload = user.recovery_codes
                if isinstance(payload, dict) and payload.get("version") != encryption.active_version:
                    codes = encryption.decrypt_json(payload)
                    user.recovery_codes = encryption.encrypt_json(codes)
                    rotated = True
            if rotated:
                updated += 1
        session.flush()
    logger.info("security.reencrypt.completed", updated=updated, version=encryption.active_version)
    return updated


__all__ = ["reencrypt_sensitive_task"]
