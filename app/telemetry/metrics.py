from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.db.models import JobModel


@dataclass
class JobTelemetry:
    job_id: str
    status: str
    cost_usd: float
    tokens_in: int
    tokens_out: int
    requests_made: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    last_action: Optional[str]

    @classmethod
    def from_model(cls, job: JobModel) -> "JobTelemetry":
        return cls(
            job_id=job.id,
            status=job.status,
            cost_usd=job.cost_usd or 0.0,
            tokens_in=job.tokens_in or 0,
            tokens_out=job.tokens_out or 0,
            requests_made=job.requests_made or 0,
            started_at=job.started_at,
            finished_at=job.finished_at,
            last_action=job.last_action,
        )
