"""Reset password for a user."""
import sys
from backend.core.config import get_settings
from backend.db.models.user import User
from backend.security.passwords import get_password_service
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

if len(sys.argv) < 3:
    print("Usage: python reset_password.py <email> <new_password>")
    sys.exit(1)

email = sys.argv[1].lower()
new_password = sys.argv[2]

settings = get_settings()
engine = create_engine(str(settings.database_url), echo=False)
password_service = get_password_service()

with Session(engine) as session:
    stmt = select(User).where(User.email == email)
    user = session.execute(stmt).scalar_one_or_none()

    if not user:
        print(f"✗ User {email} not found")
        sys.exit(1)

    print(f"✓ User found: {user.email}")
    print(f"  Status: {user.status.value}")
    print(f"  Email verified: {user.email_verified_at}")

    # Hash new password
    new_hash = password_service.hash(new_password)
    user.password_hash = new_hash

    session.commit()
    print(f"✓ Password reset successfully for {email}")
    print(f"\nYou can now login with:")
    print(f"  Email: {email}")
    print(f"  Password: {new_password}")
