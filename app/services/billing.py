"""Integration helpers for spend cap enforcement from the orchestrator."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from backend.account.enforcement import CAP_BLOCK_MESSAGE, EnforcementResult, enforce_spend_cap as _enforce_spend_cap


def enforce_spend_cap(user_id: UUID, estimated_usd: Decimal | float | int) -> EnforcementResult:
    """Proxy to the account service spend cap enforcement."""

    return _enforce_spend_cap(user_id=user_id, estimated_usd=estimated_usd)


__all__ = ["enforce_spend_cap", "EnforcementResult", "CAP_BLOCK_MESSAGE"]
