"""Admin authentication dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from backend.auth.api.deps import require_current_user
from backend.db.models.user import User


def require_admin(current_user: User = Depends(require_current_user)) -> User:
    """Require user to be a superadmin.

    Args:
        current_user: The authenticated user from JWT token

    Returns:
        User: The admin user

    Raises:
        HTTPException: 403 Forbidden if user is not a superadmin
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


__all__ = ["require_admin"]
