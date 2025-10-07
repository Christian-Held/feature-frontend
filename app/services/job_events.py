from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, AsyncIterator, Optional

from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import repo
from app.db.engine import session_scope
from app.db.models import JobModel, JobStatus

logger = get_logger(__name__)
_CHANNEL_JOBS = "job-events"


@dataclass(frozen=True)
class JobEvent:
    type: str
    payload: dict[str, Any]


def _calculate_progress(job: JobModel) -> float:
    steps = list(getattr(job, "steps", []) or [])
    if not steps:
        return 1.0 if job.status in {JobStatus.COMPLETED} else 0.0
    completed = len([step for step in steps if step.status == "completed"])
    return completed / len(steps)


def serialize_job(job: JobModel) -> dict[str, Any]:
    progress = _calculate_progress(job)
    return {
        "id": job.id,
        "task": job.task,
        "status": job.status,
        "repo_owner": job.repo_owner,
        "repo_name": job.repo_name,
        "branch_base": job.branch_base,
        "budget_usd": float(job.budget_usd),
        "max_requests": job.max_requests,
        "max_minutes": job.max_minutes,
        "model_cto": job.model_cto,
        "model_coder": job.model_coder,
        "cost_usd": float(job.cost_usd or 0.0),
        "tokens_in": job.tokens_in or 0,
        "tokens_out": job.tokens_out or 0,
        "requests_made": job.requests_made or 0,
        "progress": progress,
        "last_action": job.last_action,
        "pr_links": job.pr_links or [],
        "created_at": job.created_at.isoformat() if isinstance(job.created_at, datetime) else None,
        "updated_at": job.updated_at.isoformat() if isinstance(job.updated_at, datetime) else None,
    }


@lru_cache(maxsize=1)
def _get_sync_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def publish_job_event(event_type: str, job: JobModel) -> None:
    payload = serialize_job(job)
    message = JobEvent(type=event_type, payload=payload)
    try:
        client = _get_sync_redis()
        client.publish(_CHANNEL_JOBS, json.dumps(message.__dict__))
    except RedisError as exc:  # pragma: no cover - defensive logging
        logger.error(
            "job_event_publish_failed",
            error=str(exc),
            job_id=job.id,
            event_type=event_type,
        )


async def stream_job_events() -> AsyncIterator[JobEvent]:
    settings = get_settings()
    client = AsyncRedis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(_CHANNEL_JOBS)
    try:
        async for raw in pubsub.listen():
            if raw.get("type") != "message":
                continue
            data = raw.get("data")
            if not data:
                continue
            try:
                parsed = json.loads(data)
                yield JobEvent(type=parsed.get("type", "job.updated"), payload=parsed.get("payload", {}))
            except json.JSONDecodeError:
                logger.warning("job_event_decode_failed", raw=data)
    finally:
        await pubsub.unsubscribe(_CHANNEL_JOBS)
        await pubsub.close()
        await client.close()


def emit_job_event_for_id(event_type: str, job_id: str, session: Optional[Any] = None) -> None:
    if session is not None:
        job = repo.get_job(session, job_id)
        if job is not None:
            publish_job_event(event_type, job)
        return

    with session_scope() as scoped_session:
        job = repo.get_job(scoped_session, job_id)
        if job is not None:
            publish_job_event(event_type, job)
