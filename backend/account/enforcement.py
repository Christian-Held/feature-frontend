"""Spend cap enforcement helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status

from backend.account.services import SpendAccountingService, SpendCapState, WARNING_HEADER_VALUE
from backend.db.session import session_scope

CAP_BLOCK_MESSAGE = "Your monthly spending limit has been reached. Adjust your limit to continue."


@dataclass(slots=True)
class EnforcementResult:
    """Result returned from spend cap enforcement."""

    cap_reached: bool
    hard_stop: bool
    remaining_usd: Decimal
    warning_header: str | None = None


def _run_enforcement(
    service: SpendAccountingService,
    *,
    user_id: UUID,
    estimated_usd: Decimal | float | int,
    actor_user_id: UUID | None,
    ip: str | None,
    user_agent: str | None,
    raise_on_block: bool,
) -> EnforcementResult:
    state: SpendCapState = service.enforce_cap(
        user_id=user_id,
        estimated_usd=estimated_usd,
        actor_user_id=actor_user_id,
        ip=ip,
        user_agent=user_agent,
    )
    if state.cap_reached and state.hard_stop and raise_on_block:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=CAP_BLOCK_MESSAGE)

    warning = WARNING_HEADER_VALUE if state.cap_reached and not state.hard_stop else None
    return EnforcementResult(
        cap_reached=state.cap_reached,
        hard_stop=state.hard_stop,
        remaining_usd=state.remaining_usd,
        warning_header=warning,
    )


def enforce_spend_cap(
    user_id: UUID,
    estimated_usd: Decimal | float | int,
    *,
    actor_user_id: UUID | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    session=None,
    raise_on_block: bool = True,
) -> EnforcementResult:
    """Check whether the estimated spend exceeds the configured cap."""

    if session is not None:
        service = SpendAccountingService(session)
        return _run_enforcement(
            service,
            user_id=user_id,
            estimated_usd=estimated_usd,
            actor_user_id=actor_user_id,
            ip=ip,
            user_agent=user_agent,
            raise_on_block=raise_on_block,
        )

    with session_scope() as scoped_session:
        service = SpendAccountingService(scoped_session)
        return _run_enforcement(
            service,
            user_id=user_id,
            estimated_usd=estimated_usd,
            actor_user_id=actor_user_id,
            ip=ip,
            user_agent=user_agent,
            raise_on_block=raise_on_block,
        )


__all__ = ["enforce_spend_cap", "EnforcementResult", "CAP_BLOCK_MESSAGE"]
