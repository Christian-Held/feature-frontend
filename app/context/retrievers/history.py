from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.db.models import MessageSummaryModel


def collect_history(session: Session, job_id: str, limit: int = 10) -> List[dict]:
    records = (
        session.query(MessageSummaryModel)
        .filter(MessageSummaryModel.job_id == job_id)
        .order_by(MessageSummaryModel.created_at.desc())
        .limit(limit)
        .all()
    )
    results: List[dict] = []
    for record in records:
        results.append(
            {
                "id": f"history::{record.id}",
                "source": "history",
                "content": record.summary,
                "tokens": record.tokens or 0,
                "metadata": {"role": record.role, "step_id": record.step_id},
            }
        )
    return results
