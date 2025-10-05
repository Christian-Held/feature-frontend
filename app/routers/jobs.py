from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import deps
from app.core.logging import get_logger
from app.db import repo
from app.db.models import JobStatus
from app.services.job_events import emit_job_event_for_id, serialize_job

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger(__name__)


class JobStepResponse(BaseModel):
    name: str
    type: str
    status: str
    details: Optional[str]


class JobResponse(BaseModel):
    id: str
    status: str
    task: str
    repo_owner: str
    repo_name: str
    branch_base: str
    budget_usd: float
    max_requests: int
    max_minutes: int
    cost_usd: float
    tokens_in: int
    tokens_out: int
    requests_made: int
    progress: float
    last_action: Optional[str]
    pr_links: List[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_cto: Optional[str] = None
    model_coder: Optional[str] = None


class ContextDiagnosticsResponse(BaseModel):
    job_id: str
    step_id: Optional[str]
    tokens_final: int
    tokens_clipped: int
    compact_ops: int
    budget: dict[str, Any]
    sources: List[dict]
    dropped: List[dict]
    hints: List[str]


@router.get("/", response_model=List[JobResponse])
def list_jobs(session: Session = Depends(deps.get_db)) -> List[JobResponse]:
    jobs = repo.list_jobs(session)
    return [JobResponse.model_validate(serialize_job(job)) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(deps.get_db)) -> JobResponse:
    job = repo.get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(serialize_job(job))


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, session: Session = Depends(deps.get_db)):
    job = repo.get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    repo.mark_job_cancelled(session, job)
    session.commit()
    emit_job_event_for_id("job.cancelled", job_id, session=session)
    return {"status": "cancelled"}


@router.get("/{job_id}/context", response_model=ContextDiagnosticsResponse)
def get_job_context(job_id: str, session: Session = Depends(deps.get_db)) -> ContextDiagnosticsResponse:
    metric = repo.get_latest_context_metric(session, job_id)
    if not metric or not metric.details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context diagnostics not found")
    details = metric.details
    return ContextDiagnosticsResponse(
        job_id=job_id,
        step_id=metric.step_id,
        tokens_final=metric.tokens_final or details.get("tokens_final", 0),
        tokens_clipped=metric.tokens_clipped or details.get("tokens_clipped", 0),
        compact_ops=metric.compact_ops or details.get("compact_ops", 0),
        budget=details.get("budget", {}),
        sources=details.get("sources", []),
        dropped=details.get("dropped", []),
        hints=details.get("hints", []),
    )
