from datetime import datetime, timedelta, timezone

import pytest

from backend.security.jwt_service import JWTService, get_jwt_service


def test_jwt_accepts_current_and_previous(settings_env):
    service = get_jwt_service()
    access = service.issue_access_token("user-1")
    payload = service.decode(access)
    assert payload["sub"] == "user-1"

    settings_copy = settings_env.model_copy()
    settings_copy.jwt_jwk_current = settings_env.jwt_jwk_previous
    prev_service = JWTService(settings_copy)
    refresh = prev_service.issue_refresh_token("user-1")
    assert service.decode(refresh)["sub"] == "user-1"


def test_previous_key_rejected_after_grace(settings_env):
    service = get_jwt_service()
    settings_copy = settings_env.model_copy()
    settings_copy.jwt_jwk_current = settings_env.jwt_jwk_previous
    prev_service = JWTService(settings_copy)
    refresh = prev_service.issue_refresh_token("user-1")
    payload = service.decode(refresh)
    assert payload["sub"] == "user-1"

    # simulate expiry beyond grace window
    expired_payload = service.decode(refresh)
    expired_payload["iat"] = int((datetime.now(timezone.utc) - timedelta(seconds=settings_env.jwt_previous_grace_seconds + 10)).timestamp())
    with pytest.raises(ValueError):
        service._enforce_previous_window(expired_payload)
