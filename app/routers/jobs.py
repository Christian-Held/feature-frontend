from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import deps
from app.core.logging import get_logger
from app.db import repo
from app.db.models import JobStatus

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
    cost_usd: float
    tokens_in: int
    tokens_out: int
    requests_made: int
    progress: float
    last_action: Optional[str]
    pr_links: List[str]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(deps.get_db)) -> JobResponse:
    job = repo.get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    steps = job.steps
    completed = len([s for s in steps if s.status == "completed"])
    progress = completed / len(steps) if steps else (1.0 if job.status == JobStatus.COMPLETED else 0.0)
    return JobResponse(
        id=job.id,
        status=job.status,
        task=job.task,
        cost_usd=job.cost_usd or 0.0,
        tokens_in=job.tokens_in or 0,
        tokens_out=job.tokens_out or 0,
        requests_made=job.requests_made or 0,
        progress=progress,
        last_action=job.last_action,
        pr_links=job.pr_links or [],
    )


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, session: Session = Depends(deps.get_db)):
    job = repo.get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    repo.mark_job_cancelled(session, job)
    session.commit()
    return {"status": "cancelled"}
