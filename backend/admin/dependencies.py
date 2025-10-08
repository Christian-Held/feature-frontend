"""Dependency helpers for admin APIs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.auth.api.deps import require_current_user
from backend.db.models.user import Role, User
from backend.middleware.request_context import bind_admin_user_id

ADMIN_ROLE = "ADMIN"
FORBIDDEN_MESSAGE = "You don’t have permission to perform this action."


def _role_names(roles: Iterable[Role]) -> set[str]:
    return {role.name for role in roles}


async def require_admin_user(current_user: Annotated[User, Depends(require_current_user)]) -> User:
    """Ensure the current user is an ADMIN with MFA enabled, or a superadmin.

    Superadmins (is_superadmin=True) bypass the MFA requirement and role check.
    """

    # Superadmins bypass all checks
    if current_user.is_superadmin:
        bind_admin_user_id(str(current_user.id))
        return current_user

    # Regular admin users need MFA enabled
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_MESSAGE)

    # Regular admin users need ADMIN role
    if ADMIN_ROLE not in _role_names(current_user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_MESSAGE)

    bind_admin_user_id(str(current_user.id))

    return current_user


__all__ = ["require_admin_user", "ADMIN_ROLE", "FORBIDDEN_MESSAGE"]
