"""Check all users in database."""
from backend.core.config import get_settings
from backend.db.models.user import User, EmailVerification
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

settings = get_settings()
engine = create_engine(str(settings.database_url), echo=False)

with Session(engine) as session:
    print("=== All Users ===")
    stmt = select(User).order_by(User.created_at.desc())
    users = session.execute(stmt).scalars().all()

    for user in users:
        print(f"\nUser: {user.email}")
        print(f"  ID: {user.id}")
        print(f"  Status: {user.status.value}")
        print(f"  Email verified: {user.email_verified_at}")
        print(f"  Created: {user.created_at}")

        # Find associated verification tokens
        stmt = select(EmailVerification).where(EmailVerification.user_id == user.id).order_by(EmailVerification.created_at.desc())
        verifications = session.execute(stmt).scalars().all()

        for v in verifications:
            print(f"    Token ID: {v.id} | Expires: {v.expires_at} | Used: {v.used_at}")
