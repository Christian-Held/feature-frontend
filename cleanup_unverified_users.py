"""Cleanup script to remove unverified test users."""
from backend.core.config import get_settings
from backend.db.models.user import User, UserStatus, EmailVerification
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import Session

settings = get_settings()
engine = create_engine(str(settings.database_url), echo=False)

with Session(engine) as session:
    # Find all unverified users
    stmt = select(User).where(User.status == UserStatus.UNVERIFIED)
    unverified_users = session.execute(stmt).scalars().all()

    print(f"Found {len(unverified_users)} unverified users")

    for user in unverified_users:
        print(f"  Deleting: {user.email} (ID: {user.id})")

        # Delete associated verification tokens first
        delete_tokens = delete(EmailVerification).where(EmailVerification.user_id == user.id)
        session.execute(delete_tokens)

        # Delete user
        session.delete(user)

    session.commit()
    print(f"✓ Cleanup complete")
