"""Create password_resets table in database."""
from backend.core.config import get_settings
from backend.db.base import Base
from backend.db.models.user import PasswordReset
from sqlalchemy import create_engine

def create_table():
    settings = get_settings()
    engine = create_engine(str(settings.database_url), echo=True)

    # Create only the password_resets table
    PasswordReset.__table__.create(bind=engine, checkfirst=True)
    print("\n✓ password_resets table created successfully!")

if __name__ == "__main__":
    create_table()
