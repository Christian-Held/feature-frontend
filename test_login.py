"""Test login with the verified user credentials."""
from backend.core.config import get_settings
from backend.db.models.user import User
from backend.security.passwords import get_password_service
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

settings = get_settings()
engine = create_engine(str(settings.database_url), echo=False)
password_service = get_password_service()

# Test password for christianheld81@gmx.de
test_email = "christianheld81@gmx.de"

with Session(engine) as session:
    stmt = select(User).where(User.email == test_email)
    user = session.execute(stmt).scalar_one_or_none()

    if not user:
        print(f"✗ User {test_email} not found")
        exit(1)

    print(f"✓ User found: {user.email}")
    print(f"  Status: {user.status.value}")
    print(f"  Email verified: {user.email_verified_at}")
    print(f"  Password hash: {user.password_hash[:50]}...")

    # Ask for password to test
    print("\n" + "="*50)
    password = input("Enter the password you used during registration: ")

    try:
        is_valid = password_service.verify(user.password_hash, password)
        if is_valid:
            print(f"✓ Password is CORRECT for {test_email}")
        else:
            print(f"✗ Password is INCORRECT for {test_email}")
    except Exception as e:
        print(f"✗ Error verifying password: {e}")
