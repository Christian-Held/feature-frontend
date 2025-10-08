"""Debug token validation issue."""
from backend.core.config import get_settings
from backend.db.models.user import EmailVerification, User
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import uuid
import hashlib
import hmac

settings = get_settings()
engine = create_engine(str(settings.database_url), echo=False)

# Token from user's email
token = "bedfde83-7857-4761-baf9-3fd3ff3abb77.46c13444b974acc8a610d5d5cdbd5a43d7f9339dcbe68d4ec7a6be8d161f9dcb"

try:
    verification_id_str, signature = token.split(".")
    verification_id = uuid.UUID(verification_id_str)
    print(f"✓ Token format valid")
    print(f"  Verification ID: {verification_id}")
    print(f"  Signature: {signature}")
except (ValueError, AttributeError) as e:
    print(f"✗ Token format invalid: {e}")
    exit(1)

with Session(engine) as session:
    # Check if verification record exists
    stmt = select(EmailVerification).where(EmailVerification.id == verification_id)
    verification = session.execute(stmt).scalar_one_or_none()

    if verification is None:
        print(f"✗ Verification record NOT FOUND in database")

        # Check all verification records for this user email
        print("\n=== All verification records ===")
        stmt = select(EmailVerification).order_by(EmailVerification.created_at.desc()).limit(10)
        all_verifications = session.execute(stmt).scalars().all()
        for v in all_verifications:
            user = session.get(User, v.user_id)
            print(f"  {v.id} | User: {user.email if user else 'UNKNOWN'} | Expires: {v.expires_at} | Used: {v.used_at}")
    else:
        print(f"✓ Verification record found")
        user = session.get(User, verification.user_id)
        print(f"  User: {user.email if user else 'UNKNOWN'} (ID: {verification.user_id})")
        print(f"  Created: {verification.created_at}")
        print(f"  Expires: {verification.expires_at}")
        print(f"  Used at: {verification.used_at}")
        print(f"  Token hash in DB: {verification.token_hash}")

        # Verify signature
        expected_hash = hashlib.sha256(signature.encode("utf-8")).hexdigest()
        print(f"  Expected hash: {expected_hash}")

        if verification.token_hash == expected_hash:
            print(f"✓ Signature matches!")
        else:
            print(f"✗ Signature MISMATCH!")

            # Try generating signature from scratch
            print("\n=== Testing signature generation ===")
            test_sig = hmac.new(
                settings.email_verification_secret.encode("utf-8"),
                str(verification_id).encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            test_hash = hashlib.sha256(test_sig.encode("utf-8")).hexdigest()

            print(f"  Generated signature: {test_sig}")
            print(f"  Generated hash: {test_hash}")
            print(f"  Matches signature from token: {test_sig == signature}")
            print(f"  Matches hash from DB: {test_hash == verification.token_hash}")
