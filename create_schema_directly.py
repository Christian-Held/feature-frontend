#!/usr/bin/env python3
"""Create database schema directly from SQLAlchemy models, bypassing Alembic."""

from backend.core.config import get_settings
from backend.db.base import Base
from backend.db import models  # Import all models
from sqlalchemy import create_engine

def create_schema():
    settings = get_settings()
    db_url = settings.database_url

    print(f"Connecting to: {db_url}")
    engine = create_engine(str(db_url), echo=True)

    print("\nCreating all tables...")
    Base.metadata.create_all(bind=engine)

    print("\n✅ Database schema created successfully!")
    print("All tables have been created from SQLAlchemy models.")

if __name__ == "__main__":
    create_schema()
