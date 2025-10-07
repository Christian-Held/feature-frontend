import json

import jwt

from backend.security.jwt_service import JWTService


def test_jwt_rotation(settings_env):
    service = JWTService(settings_env)

    first_token = service.issue_access_token("user-123")
    first_header = jwt.get_unverified_header(first_token)
    assert first_header["kid"] == "current"

    decoded_first = service.decode(first_token)
    assert decoded_first["sub"] == "user-123"
    assert decoded_first["type"] == "access"

    next_payload = json.loads(settings_env.jwt_jwk_next)
    service.set_active_kid(next_payload["kid"])
    rotated_token = service.issue_access_token("user-123")
    rotated_header = jwt.get_unverified_header(rotated_token)
    assert rotated_header["kid"] == next_payload["kid"]

    decoded_rotated = service.decode(rotated_token)
    assert decoded_rotated["sub"] == "user-123"
    assert decoded_rotated["iss"] == settings_env.jwt_issuer

    # Ensure tokens signed with old key are still valid post-rotation
    assert service.decode(first_token)["sub"] == "user-123"
