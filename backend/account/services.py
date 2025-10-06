"""Service layer for account plan management and spend accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable
from uuid import UUID

import structlog
from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from backend.account.schemas import PlanCode, SpendTotals
from backend.db.models.audit import AuditLog
from backend.db.models.billing import (
    Plan,
    PlanStatus,
    SpendLimit,
    SpendRecord,
    UserPlan,
)

logger = structlog.get_logger(__name__)

AUDIT_TARGET = "user"
WARNING_HEADER_VALUE = "cap_reached"
CAP_REACHED_EVENT = "cap_reached"
PLAN_CHANGED_EVENT = "plan_changed"
LIMITS_CHANGED_EVENT = "limits_changed"
SPEND_RECORDED_EVENT = "spend_recorded"


@dataclass(slots=True)
class SpendCapState:
    """State returned by spend cap enforcement routines."""

    cap_reached: bool
    hard_stop: bool
    remaining_usd: Decimal


def _quantize(amount: Decimal | float | int) -> Decimal:
    dec = Decimal(str(amount))
    return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _month_bounds(moment: datetime | None = None) -> tuple[datetime, datetime]:
    now = moment or datetime.now(UTC)
    start = datetime(now.year, now.month, 1, tzinfo=UTC)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
    return start, end


def _record_audit(
    session: Session,
    *,
    actor_user_id: UUID | None,
    target_user_id: UUID,
    action: str,
    metadata: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=AUDIT_TARGET,
        target_id=str(target_user_id),
        metadata_json=metadata,
        ip=ip,
        user_agent=user_agent,
        occurred_at=datetime.now(UTC),
    )
    session.add(entry)


class PlanService:
    """Manage plan assignments for users."""

    def __init__(self, session: Session):
        self._session = session

    def get_active_plan(self, user_id: UUID) -> Plan:
        plan_join: Select[tuple[Plan]] = (
            select(Plan)
            .join(UserPlan, UserPlan.plan_id == Plan.id)
            .where(UserPlan.user_id == user_id, UserPlan.status == PlanStatus.ACTIVE)
            .order_by(UserPlan.created_at.desc())
        )
        plan = self._session.scalars(plan_join).first()
        if plan:
            return plan

        # Auto-enroll in FREE plan if none exists
        free_plan = self.get_plan_by_code(PlanCode.FREE)
        enrollment = UserPlan(user_id=user_id, plan_id=free_plan.id, status=PlanStatus.ACTIVE)
        self._session.add(enrollment)
        logger.info("plan.auto_assigned", user_id=str(user_id), plan=free_plan.code)
        return free_plan

    def get_plan_by_code(self, code: PlanCode) -> Plan:
        plan = self._session.scalar(select(Plan).where(Plan.code == code.value))
        if not plan:
            raise ValueError(f"Plan {code.value} is not configured")
        return plan

    def set_plan(
        self,
        *,
        user_id: UUID,
        plan_code: PlanCode,
        actor_user_id: UUID | None,
        ip: str | None,
        user_agent: str | None,
    ) -> Plan:
        plan = self.get_plan_by_code(plan_code)
        active = self._session.scalar(
            select(UserPlan).where(UserPlan.user_id == user_id, UserPlan.status == PlanStatus.ACTIVE)
        )
        if active and active.plan_id == plan.id:
            logger.info(PLAN_CHANGED_EVENT, user_id=str(user_id), plan=plan.code, changed=False)
            return plan

        if active:
            active.status = PlanStatus.CANCELED
            active.cancelled_at = datetime.now(UTC)

        enrollment = UserPlan(user_id=user_id, plan_id=plan.id, status=PlanStatus.ACTIVE)
        self._session.add(enrollment)
        logger.info(PLAN_CHANGED_EVENT, user_id=str(user_id), plan=plan.code, changed=True)
        _record_audit(
            self._session,
            actor_user_id=actor_user_id,
            target_user_id=user_id,
            action=PLAN_CHANGED_EVENT,
            metadata={"plan": plan.code},
            ip=ip,
            user_agent=user_agent,
        )
        return plan

    def admin_override_plan(
        self,
        *,
        actor_user_id: UUID,
        target_user_id: UUID,
        plan_code: PlanCode,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Plan:
        return self.set_plan(
            user_id=target_user_id,
            plan_code=plan_code,
            actor_user_id=actor_user_id,
            ip=ip,
            user_agent=user_agent,
        )


class SpendLimitService:
    """Manage spend limits for users."""

    def __init__(self, session: Session):
        self._session = session

    def get_or_create(self, user_id: UUID) -> SpendLimit:
        limit = self._session.scalar(select(SpendLimit).where(SpendLimit.user_id == user_id))
        if limit:
            return limit
        limit = SpendLimit(user_id=user_id, monthly_cap_usd=Decimal("0.00"), hard_stop=False)
        self._session.add(limit)
        self._session.flush()
        return limit

    def update_limits(
        self,
        *,
        user_id: UUID,
        monthly_cap_usd: Decimal,
        hard_stop: bool,
        actor_user_id: UUID | None,
        ip: str | None,
        user_agent: str | None,
    ) -> SpendLimit:
        monthly_cap_usd = _quantize(monthly_cap_usd)
        limit = self.get_or_create(user_id)
        limit.monthly_cap_usd = monthly_cap_usd
        limit.hard_stop = hard_stop
        logger.info(
            LIMITS_CHANGED_EVENT,
            user_id=str(user_id),
            monthly_cap_usd=str(monthly_cap_usd),
            hard_stop=hard_stop,
        )
        _record_audit(
            self._session,
            actor_user_id=actor_user_id,
            target_user_id=user_id,
            action=LIMITS_CHANGED_EVENT,
            metadata={"monthly_cap_usd": str(monthly_cap_usd), "hard_stop": hard_stop},
            ip=ip,
            user_agent=user_agent,
        )
        return limit

    def admin_override_limits(
        self,
        *,
        actor_user_id: UUID,
        target_user_id: UUID,
        monthly_cap_usd: Decimal,
        hard_stop: bool,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> SpendLimit:
        return self.update_limits(
            user_id=target_user_id,
            monthly_cap_usd=monthly_cap_usd,
            hard_stop=hard_stop,
            actor_user_id=actor_user_id,
            ip=ip,
            user_agent=user_agent,
        )


class SpendAccountingService:
    """Record spend and compute usage totals."""

    def __init__(self, session: Session):
        self._session = session

    def record(self, user_id: UUID, usd_amount: Decimal | float | int, meta: dict[str, Any] | None = None) -> SpendRecord:
        amount = _quantize(usd_amount)
        record = SpendRecord(user_id=user_id, amount_usd=amount, metadata_json=meta or {})
        self._session.add(record)
        logger.info(SPEND_RECORDED_EVENT, user_id=str(user_id), amount=str(amount))
        _record_audit(
            self._session,
            actor_user_id=user_id,
            target_user_id=user_id,
            action=SPEND_RECORDED_EVENT,
            metadata={"amount_usd": str(amount), "meta": meta or {}},
        )
        return record

    def get_month_totals(self, user_id: UUID) -> SpendTotals:
        start, end = _month_bounds()
        total = self._session.scalar(
            select(func.coalesce(func.sum(SpendRecord.amount_usd), Decimal("0.00")))
            .where(
                and_(
                    SpendRecord.user_id == user_id,
                    SpendRecord.created_at >= start,
                    SpendRecord.created_at < end,
                )
            )
        )
        total = _quantize(total or Decimal("0.00"))

        limit = self._session.scalar(select(SpendLimit).where(SpendLimit.user_id == user_id))
        cap = _quantize(limit.monthly_cap_usd) if limit else Decimal("0.00")
        hard_stop = bool(limit.hard_stop) if limit else False
        remaining = cap - total
        if remaining < Decimal("0.00"):
            remaining = Decimal("0.00")
        cap_reached = cap > Decimal("0.00") and total >= cap
        return SpendTotals(
            usage_usd=total,
            cap_usd=cap,
            remaining_usd=remaining,
            cap_reached=cap_reached,
            hard_stop=hard_stop,
        )

    def enforce_cap(
        self,
        *,
        user_id: UUID,
        estimated_usd: Decimal | float | int,
        actor_user_id: UUID | None,
        ip: str | None,
        user_agent: str | None,
    ) -> SpendCapState:
        totals = self.get_month_totals(user_id)
        projected_usage = totals.usage_usd + _quantize(estimated_usd)
        cap = totals.cap_usd or Decimal("0.00")
        cap_reached = cap > Decimal("0.00") and projected_usage >= cap
        if cap_reached:
            logger.info(
                CAP_REACHED_EVENT,
                user_id=str(user_id),
                cap=str(cap),
                usage=str(totals.usage_usd),
                estimated=str(estimated_usd),
                hard_stop=totals.hard_stop,
            )
            _record_audit(
                self._session,
                actor_user_id=actor_user_id,
                target_user_id=user_id,
                action=CAP_REACHED_EVENT,
                metadata={
                    "cap_usd": str(cap),
                    "usage_usd": str(totals.usage_usd),
                    "estimated_usd": str(_quantize(estimated_usd)),
                    "hard_stop": totals.hard_stop,
                },
                ip=ip,
                user_agent=user_agent,
            )
        remaining = cap - projected_usage
        if remaining < Decimal("0.00"):
            remaining = Decimal("0.00")
        return SpendCapState(cap_reached=cap_reached, hard_stop=totals.hard_stop, remaining_usd=remaining)


__all__ = [
    "PlanService",
    "SpendAccountingService",
    "SpendLimitService",
    "SpendCapState",
    "WARNING_HEADER_VALUE",
    "CAP_REACHED_EVENT",
    "PLAN_CHANGED_EVENT",
    "LIMITS_CHANGED_EVENT",
    "SPEND_RECORDED_EVENT",
]
