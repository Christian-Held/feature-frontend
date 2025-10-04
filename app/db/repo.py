from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from .models import CostEntryModel, JobModel, JobStatus, JobStepModel


def create_job(
    session: Session,
    *,
    task: str,
    repo_owner: str,
    repo_name: str,
    branch_base: str,
    budget_usd: float,
    max_requests: int,
    max_minutes: int,
    model_cto: Optional[str],
    model_coder: Optional[str],
    agents_hash: Optional[str],
) -> JobModel:
    job = JobModel(
        task=task,
        repo_owner=repo_owner,
        repo_name=repo_name,
        branch_base=branch_base,
        budget_usd=budget_usd,
        max_requests=max_requests,
        max_minutes=max_minutes,
        model_cto=model_cto,
        model_coder=model_coder,
        agents_hash=agents_hash,
    )
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, job_id: str) -> Optional[JobModel]:
    return session.get(JobModel, job_id)


def list_jobs(session: Session) -> List[JobModel]:
    return session.query(JobModel).order_by(JobModel.created_at.desc()).all()


def update_job_status(session: Session, job: JobModel, status: str) -> None:
    job.status = status
    if status in {JobStatus.RUNNING} and job.started_at is None:
        job.started_at = datetime.utcnow()
    if status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
        job.finished_at = datetime.utcnow()
    session.add(job)


def mark_job_cancelled(session: Session, job: JobModel) -> None:
    job.cancelled = True
    job.status = JobStatus.CANCELLED
    job.finished_at = datetime.utcnow()
    session.add(job)


def append_pr_link(session: Session, job: JobModel, link: str) -> None:
    links = list(job.pr_links or [])
    links.append(link)
    job.pr_links = links
    session.add(job)


def increment_costs(
    session: Session,
    job: JobModel,
    *,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
) -> CostEntryModel:
    cost = CostEntryModel(
        job_id=job.id,
        provider=provider,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
    )
    job.tokens_in += tokens_in
    job.tokens_out += tokens_out
    job.cost_usd += cost_usd
    job.requests_made += 1
    session.add(cost)
    session.add(job)
    return cost


def create_step(session: Session, job: JobModel, name: str, step_type: str) -> JobStepModel:
    step = JobStepModel(job_id=job.id, name=name, step_type=step_type, status="pending")
    session.add(step)
    session.flush()
    return step


def update_step(session: Session, step: JobStepModel, *, status: str, details: Optional[str] = None) -> None:
    step.status = status
    step.details = details
    now = datetime.utcnow()
    if status == "running" and step.started_at is None:
        step.started_at = now
    if status in {"completed", "failed"}:
        step.finished_at = now
    session.add(step)


def get_steps(session: Session, job_id: str) -> Iterable[JobStepModel]:
    return session.query(JobStepModel).filter(JobStepModel.job_id == job_id).order_by(JobStepModel.created_at).all()


def get_step(session: Session, step_id: str) -> Optional[JobStepModel]:
    return session.get(JobStepModel, step_id)
