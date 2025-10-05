from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

from app.agents.coder import CoderAgent
from app.agents.cto import CTOAgent
from app.agents.prompts import build_prompt, parse_agents_file
from app.context.engine import ContextEngine
from app.core.config import get_settings
from app.core.diffs import apply_unified_diff, safe_write
from app.core.logging import get_logger
from app.core.pricing import get_pricing_table
from app.db import repo
from app.db.engine import session_scope
from app.db.models import JobStatus
from app.git import repo_ops
from app.llm.openai_provider import OpenAILLMProvider
from app.llm.provider import BaseLLMProvider, DryRunLLMProvider

from .celery_app import celery_app

logger = get_logger(__name__)


def _select_provider(dry_run: bool) -> BaseLLMProvider:
    if dry_run:
        return DryRunLLMProvider()
    return OpenAILLMProvider()


def _calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = get_pricing_table().get(model)
    return (tokens_in / 1000) * pricing.input + (tokens_out / 1000) * pricing.output


def _check_limits(job, *, now: datetime) -> None:
    settings = get_settings()
    if job.cost_usd >= job.budget_usd:
        raise RuntimeError("Budget limit exceeded")
    if job.requests_made >= job.max_requests:
        raise RuntimeError("Request limit exceeded")
    if job.started_at:
        elapsed = now - job.started_at
        if elapsed > timedelta(minutes=job.max_minutes):
            raise RuntimeError("Wall-clock limit exceeded")


def _apply_diff(repo_path: Path, diff_text: str) -> None:
    for file_path, content in apply_unified_diff(repo_path, diff_text):
        safe_write(file_path, content)


def _run_coro(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        result_holder: dict[str, object] = {}
        error_holder: dict[str, BaseException] = {}

        def runner() -> None:
            try:
                result_holder["value"] = asyncio.run(coro)
            except BaseException as exc:  # pragma: no cover
                error_holder["error"] = exc

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()
        if "error" in error_holder:
            raise error_holder["error"]
        return result_holder.get("value")
    return asyncio.run(coro)


def _prepare_messages(
    provider: BaseLLMProvider,
    *,
    job_id: str,
    step_id: Optional[str],
    role: str,
    task: str,
    step: Optional[Dict[str, Any]],
    base_messages: List[Dict[str, str]],
    repo_path: Optional[Path],
) -> tuple[List[Dict[str, str]], Optional[Dict[str, Any]]]:
    settings = get_settings()
    if not settings.context_engine_enabled:
        return base_messages, None
    engine = ContextEngine(provider)
    with session_scope() as session:
        result = engine.build_context(
            session=session,
            job_id=job_id,
            step_id=step_id,
            role=role,
            task=task,
            step=step,
            base_messages=base_messages,
            repo_path=repo_path,
        )
        return result.messages, result.diagnostics


def _format_context_report(diagnostics: Optional[Dict[str, Any]]) -> str:
    if not diagnostics:
        return "## Context Report\n- Context engine disabled"
    budget = diagnostics.get("budget", {})
    lines = ["## Context Report"]
    lines.append(
        f"- Tokens final: {diagnostics.get('tokens_final', 0)} (clipped: {diagnostics.get('tokens_clipped', 0)})"
    )
    lines.append(f"- Compact operations: {diagnostics.get('compact_ops', 0)}")
    lines.append(
        f"- Budget: {budget.get('budget_tokens', 0)} reserve={budget.get('reserve_tokens', 0)} hard_cap={budget.get('hard_cap_tokens', 0)}"
    )
    dropped = diagnostics.get("dropped", [])
    if dropped:
        lines.append(f"- Hard-cap drops: {len(dropped)} segments")
    lines.append("### Top Sources")
    for source in diagnostics.get("sources", [])[:5]:
        try:
            score = f"{source.get('score', 0.0):.2f}"
        except Exception:  # pragma: no cover - defensive
            score = "n/a"
        lines.append(
            f"- {source.get('source')} {source.get('metadata', {}).get('title', '')} (score={score}, tokens={source.get('tokens', 0)})"
        )
    return "\n".join(lines)


@celery_app.task(name="app.workers.job_worker.execute_job", bind=True)
def execute_job(self, job_id: str):
    settings = get_settings()
    spec = parse_agents_file()
    provider_cto = _select_provider(settings.dry_run)
    provider_coder = _select_provider(settings.dry_run)
    last_context_diag: Optional[Dict[str, Any]] = None
    try:
        with session_scope() as session:
            job = repo.get_job(session, job_id)
            if not job:
                raise RuntimeError("Job not found")
            if job.cancelled:
                logger.info("job_cancelled_pre_start", job_id=job.id)
                return
            job_task = job.task
            job_repo_owner = job.repo_owner
            job_repo_name = job.repo_name
            job_branch_base = job.branch_base
            model_cto = job.model_cto or settings.model_cto
            model_coder = job.model_coder or settings.model_coder
            repo.update_job_status(session, job, JobStatus.RUNNING)
            session.commit()
        cto_agent = CTOAgent(provider_cto, spec, model_cto, settings.dry_run)
        base_prompt = build_prompt(spec.section("CTO-AI"), f"Task: {job_task}")
        base_messages = [{"role": "system", "content": base_prompt}]
        plan_messages, context_diag = _prepare_messages(
            provider_cto,
            job_id=job_id,
            step_id=None,
            role="cto-plan",
            task=job_task,
            step=None,
            base_messages=base_messages,
            repo_path=None,
        )
        if context_diag:
            last_context_diag = context_diag
        plan, plan_tokens_in, plan_tokens_out = _run_coro(
            cto_agent.create_plan(job_task, messages=plan_messages)
        )
        with session_scope() as session:
            job = repo.get_job(session, job_id)
            if plan_tokens_in or plan_tokens_out:
                cost = _calculate_cost(model_cto, plan_tokens_in, plan_tokens_out)
                repo.increment_costs(
                    session,
                    job,
                    provider=provider_cto.name,
                    model=model_cto,
                    tokens_in=plan_tokens_in,
                    tokens_out=plan_tokens_out,
                    cost_usd=cost,
                )
            repo.add_message_summary(
                session,
                job_id=job_id,
                step_id=None,
                role="cto-plan",
                summary=json.dumps(plan, ensure_ascii=False)[:2000],
                tokens=plan_tokens_out,
            )
            session.commit()
        with session_scope() as session:
            job = repo.get_job(session, job_id)
            job.last_action = "plan"
            session.add(job)
            for step in plan:
                step_model = repo.create_step(session, job, step.get("title", "Step"), "plan")
                repo.update_step(session, step_model, status="completed", details="planned")
            session.commit()
        feature_branch = f"auto/{job_id[:8]}"
        if settings.dry_run:
            repo_path = Path("./data/dry-run") / job_id
            repo_path.mkdir(parents=True, exist_ok=True)
            repo_instance = None
        else:
            repo_path = repo_ops.clone_or_update_repo(job_repo_owner, job_repo_name, job_branch_base)
            repo_instance = repo_ops.Repo(repo_path)
            repo_ops.create_branch(repo_instance, feature_branch, job_branch_base)
        for step in plan:
            with session_scope() as session:
                job = repo.get_job(session, job_id)
                _check_limits(job, now=datetime.utcnow())
                step_model = repo.create_step(session, job, step.get("title", "step"), "execution")
                step_id = step_model.id
                repo.update_step(session, step_model, status="running")
                session.commit()
            coder_agent = CoderAgent(provider_coder, spec, model_coder, settings.dry_run)
            coder_context = json.dumps({"task": job_task, "step": step}, ensure_ascii=False, indent=2)
            coder_prompt = build_prompt(spec.section("CODER-AI"), coder_context)
            base_messages = [{"role": "system", "content": coder_prompt}]
            messages, context_diag = _prepare_messages(
                provider_coder,
                job_id=job_id,
                step_id=step_id,
                role="coder-step",
                task=job_task,
                step=step,
                base_messages=base_messages,
                repo_path=repo_path,
            )
            if context_diag:
                last_context_diag = context_diag
            result = _run_coro(coder_agent.implement_step(job_task, step, messages=messages))
            diff_text = result.get("diff", "")
            summary = result.get("summary", "")
            if diff_text:
                _apply_diff(Path(repo_path), diff_text)
                if repo_instance is not None:
                    repo_ops.commit_all(repo_instance, f"{step.get('title', 'Step')}\n\n{summary}")
            with session_scope() as session:
                job = repo.get_job(session, job_id)
                tokens_in = int(result.get("tokens_in", 0) or 0)
                tokens_out = int(result.get("tokens_out", 0) or 0)
                model_name = model_coder
                if tokens_in or tokens_out:
                    cost = _calculate_cost(model_name, tokens_in, tokens_out)
                    repo.increment_costs(
                        session,
                        job,
                        provider=provider_coder.name,
                        model=model_name,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost,
                    )
                repo.add_message_summary(
                    session,
                    job_id=job_id,
                    step_id=step_id,
                    role="coder-step",
                    summary=summary[:2000],
                    tokens=tokens_out,
                )
                job.last_action = summary or step.get("title")
                session.add(job)
                step_model = repo.get_step(session, step_id)
                if step_model:
                    repo.update_step(session, step_model, status="completed", details=summary)
                session.commit()
        if not settings.dry_run and repo_instance is not None:
            with session_scope() as session:
                job = repo.get_job(session, job_id)
                agents_hash_diff = (
                    f"{job.agents_hash} -> {spec.digest}" if job and job.agents_hash != spec.digest else "unchanged"
                )
            repo_ops.push_branch(repo_instance, feature_branch)
            context_report = _format_context_report(last_context_diag)
            pr_body = (
                f"Job {job.id} completed.\n"
                f"Agents hash current: {spec.digest}\n"
                f"Agents hash diff: {agents_hash_diff}\n"
                f"Merge strategy: {settings.merge_conflict_behavior}\n\n"
                f"{context_report}"
            )
            pr_url = repo_ops.open_pull_request(
                job_id=job.id,
                title=f"AutoDev Orchestrator Update {job.id[:8]}",
                body=pr_body,
                head=feature_branch,
                base=job_branch_base,
            )
            with session_scope() as session:
                job = repo.get_job(session, job_id)
                repo.append_pr_link(session, job, pr_url)
                repo.update_job_status(session, job, JobStatus.COMPLETED)
                session.commit()
        else:
            with session_scope() as session:
                job = repo.get_job(session, job_id)
                repo.update_job_status(session, job, JobStatus.COMPLETED)
                session.commit()
    except Exception as exc:
        logger.exception("job_failed", job_id=job_id)
        with session_scope() as session:
            job = repo.get_job(session, job_id)
            if job:
                repo.update_job_status(session, job, JobStatus.FAILED)
                session.commit()
        raise exc


class _EnqueueProxy:
    def delay(self, job_id: str) -> None:
        execute_job.delay(job_id)


enqueue_job = _EnqueueProxy()
