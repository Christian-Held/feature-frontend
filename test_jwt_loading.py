"""Test that JWT keys load correctly from files."""
from backend.core.config import get_settings
from backend.security.jwt_service import get_jwt_service

try:
    settings = get_settings()
    print(f"✓ Settings loaded")
    print(f"  JWT_JWK_CURRENT: {settings.jwt_jwk_current}")
    print(f"  JWT_JWK_NEXT: {settings.jwt_jwk_next}")

    jwt_service = get_jwt_service()
    print(f"\n✓ JWT Service initialized successfully!")
    print(f"  Active kid: {jwt_service.active_kid}")

    # Test token generation
    access_token = jwt_service.issue_access_token("test_user_123")
    print(f"\n✓ Access token generated: {access_token[:50]}...")

    # Test token verification
    claims = jwt_service.verify_token(access_token)
    print(f"✓ Token verified successfully!")
    print(f"  Subject: {claims['sub']}")
    print(f"  Type: {claims['type']}")

    print("\n" + "="*50)
    print("✅ JWT system is working correctly!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
