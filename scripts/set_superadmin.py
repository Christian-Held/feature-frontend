#!/usr/bin/env python3
"""Script to set a user as superadmin.

Usage:
    python scripts/set_superadmin.py <email>

Example:
    python scripts/set_superadmin.py admin@example.com
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.session import SessionLocal
from backend.db.models.user import User


def set_superadmin(email: str) -> None:
    """Set a user as superadmin by email."""
    db = SessionLocal()
    try:
        # Find user by email
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print(f"❌ User with email '{email}' not found.")
            print("\nAvailable users:")
            users = db.query(User).limit(10).all()
            for u in users:
                print(f"  - {u.email} (id: {u.id}, superadmin: {u.is_superadmin})")
            sys.exit(1)

        if user.is_superadmin:
            print(f"✓ User '{email}' is already a superadmin.")
            return

        # Set as superadmin
        user.is_superadmin = True
        db.commit()

        print(f"✅ Successfully set user '{email}' as superadmin!")
        print(f"   User ID: {user.id}")
        print(f"   Status: {user.status}")
        print(f"   MFA Enabled: {user.mfa_enabled}")
        print(f"\nNote: Superadmins bypass MFA requirements for admin endpoints.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/set_superadmin.py <email>")
        print("\nExample:")
        print("  python scripts/set_superadmin.py admin@example.com")
        sys.exit(1)

    email = sys.argv[1]
    set_superadmin(email)
