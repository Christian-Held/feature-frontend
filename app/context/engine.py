from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.agents.archivist_agent import ArchivistAgent
from app.agents.curator_agent import CuratorAgent
from app.context.compactor import compact_candidates
from app.context.curator import Curator, RankedCandidate
from app.context.memory_store import MemoryStore
from app.context.retrievers import artifacts, external, history, repo
from app.core.config import get_settings
from app.core.logging import get_logger
from app.embeddings.openai_embed import OpenAIEmbeddingProvider
from app.llm.provider import BaseLLMProvider, estimate_tokens

logger = get_logger(__name__)


@dataclass(slots=True)
class ContextCandidate:
    id: str
    source: str
    content: str
    tokens: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContextBuildResult:
    messages: List[Dict[str, str]]
    diagnostics: Dict[str, Any]
    candidates: List[ContextCandidate]
    hints: List[str]


class ContextEngine:
    def __init__(self, provider: BaseLLMProvider):
        settings = get_settings()
        self.provider = provider
        self.settings = settings
        self.embedding_provider = OpenAIEmbeddingProvider(settings.embedding_model)
        self.curator = Curator(self.embedding_provider)
        self.curator_agent = CuratorAgent()
        self.memory_store = MemoryStore()
        self.archivist_agent = ArchivistAgent(self.memory_store)

    def _gather_candidates(
        self,
        session: Session,
        job_id: str,
        task: str,
        step: Optional[Dict[str, Any]],
        repo_path: Optional[Path],
    ) -> List[ContextCandidate]:
        candidates: List[ContextCandidate] = []
        task_content = task.strip()
        candidates.append(
            ContextCandidate(
                id="task",
                source="task",
                content=task_content,
                tokens=estimate_tokens(task_content),
            )
        )
        if step:
            step_summary = json.dumps(step, ensure_ascii=False, indent=2)
            candidates.append(
                ContextCandidate(
                    id="step",
                    source="step",
                    content=step_summary,
                    tokens=estimate_tokens(step_summary),
                )
            )
        notes = self.memory_store.list_notes(session, job_id)
        for index, note in enumerate(notes):
            body = note.get("body", "")
            title = note.get("title", f"note-{index}")
            content = f"{note.get('type')}: {title}\n{body}"
            candidates.append(
                ContextCandidate(
                    id=f"note::{index}",
                    source="memory",
                    content=content,
                    tokens=estimate_tokens(content),
                    metadata=note,
                )
            )
        repo_candidates = repo.collect_repo_snippets(repo_path, step.get("files") if step else None)
        for item in repo_candidates:
            candidates.append(
                ContextCandidate(
                    id=item["id"],
                    source=item["source"],
                    content=item["content"],
                    tokens=item.get("tokens", estimate_tokens(item["content"])),
                    metadata=item.get("metadata", {}),
                )
            )
        candidates.extend(
            ContextCandidate(
                id=item["id"],
                source=item["source"],
                content=item["content"],
                tokens=item.get("tokens", estimate_tokens(item["content"])),
                metadata=item.get("metadata", {}),
            )
            for item in artifacts.collect_artifacts(job_id)
        )
        candidates.extend(
            ContextCandidate(
                id=item["id"],
                source=item["source"],
                content=item["content"],
                tokens=item.get("tokens", estimate_tokens(item["content"])),
                metadata=item.get("metadata", {}),
            )
            for item in history.collect_history(session, job_id)
        )
        if self.settings.jit_enable:
            query = self._build_query(task, step)
            for item in external.collect_external_docs(session, self.embedding_provider, query):
                candidates.append(
                    ContextCandidate(
                        id=item["id"],
                        source=item["source"],
                        content=item["content"],
                        tokens=item.get("tokens", estimate_tokens(item["content"])),
                        metadata=item.get("metadata", {}),
                    )
                )
        return candidates

    def _build_query(self, task: str, step: Optional[Dict[str, Any]]) -> str:
        parts = [task]
        if step:
            parts.append(step.get("title", ""))
            if step.get("rationale"):
                parts.append(step["rationale"])
            if step.get("acceptance"):
                parts.append(step["acceptance"])
        return "\n".join(part for part in parts if part)

    def build_context(
        self,
        *,
        session: Session,
        job_id: str,
        step_id: str | None,
        role: str,
        task: str,
        step: Optional[Dict[str, Any]],
        base_messages: List[Dict[str, str]],
        repo_path: Optional[Path] = None,
    ) -> ContextBuildResult:
        logger.info("context_build_start", job_id=job_id, role=role)
        self.archivist_agent.maintain(session, job_id)
        candidates = self._gather_candidates(session, job_id, task, step, repo_path)
        raw_docs = [
            {
                "id": candidate.id,
                "source": candidate.source,
                "content": candidate.content,
                "tokens": candidate.tokens,
                "metadata": candidate.metadata,
            }
            for candidate in candidates
        ]
        query = self._build_query(task, step)
        ranked = self.curator.rank(query, raw_docs)
        compacted, compact_ops = compact_candidates(
            ranked,
            available_tokens=self.settings.context_budget_tokens,
            threshold_ratio=self.settings.context_compact_threshold_ratio,
        )
        available_budget = max(
            1, self.settings.context_budget_tokens - self.settings.context_output_reserve_tokens
        )
        selected: List[RankedCandidate] = []
        tokens_used = 0
        tokens_clipped = 0
        for item in compacted:
            current = item
            if tokens_used + item.tokens > available_budget:
                remaining = available_budget - tokens_used
                if remaining <= 0:
                    tokens_clipped += item.tokens
                    continue
                truncated_text = item.content[: remaining * 4]
                truncated_tokens = estimate_tokens(truncated_text)
                tokens_clipped += max(0, item.tokens - truncated_tokens)
                current = replace(item, content=truncated_text, tokens=truncated_tokens)
            selected.append(current)
            tokens_used += current.tokens
        hints = self.curator_agent.build_hints(query, selected)
        context_message = self._build_context_message(selected, hints)
        messages = [context_message] + base_messages
        tokens_final = self.provider.count_tokens(messages)
        hard_cap = self.settings.context_hard_cap_tokens
        dropped: List[RankedCandidate] = []
        while tokens_final > hard_cap and selected:
            removed = selected.pop()
            dropped.append(removed)
            tokens_clipped += removed.tokens
            hints = self.curator_agent.build_hints(query, selected)
            context_message = self._build_context_message(selected, hints)
            messages = [context_message] + base_messages
            tokens_final = self.provider.count_tokens(messages)
        diagnostics = {
            "job_id": job_id,
            "step_id": step_id,
            "role": role,
            "tokens_final": tokens_final,
            "tokens_clipped": tokens_clipped,
            "compact_ops": compact_ops,
            "budget": {
                "budget_tokens": self.settings.context_budget_tokens,
                "reserve_tokens": self.settings.context_output_reserve_tokens,
                "hard_cap_tokens": hard_cap,
            },
            "sources": [
                {
                    "id": item.id,
                    "source": item.source,
                    "score": item.score,
                    "tokens": item.tokens,
                    "metadata": item.metadata,
                }
                for item in selected
            ],
            "dropped": [
                {
                    "id": item.id,
                    "source": item.source,
                    "score": item.score,
                    "tokens": item.tokens,
                }
                for item in dropped
            ],
            "hints": hints,
        }
        self._persist_diagnostics(session, job_id, step_id, diagnostics)
        logger.info(
            "context_build_complete",
            job_id=job_id,
            role=role,
            tokens_final=tokens_final,
            compact_ops=compact_ops,
            selected=len(selected),
        )
        return ContextBuildResult(messages=messages, diagnostics=diagnostics, candidates=candidates, hints=hints)

    def _persist_diagnostics(
        self,
        session: Session,
        job_id: str,
        step_id: str | None,
        diagnostics: Dict[str, Any],
    ) -> None:
        from app.db import repo as db_repo

        db_repo.record_context_metric(
            session,
            job_id=job_id,
            step_id=step_id,
            tokens_final=diagnostics.get("tokens_final", 0),
            tokens_clipped=diagnostics.get("tokens_clipped", 0),
            compact_ops=diagnostics.get("compact_ops", 0),
            details=diagnostics,
        )
        session.commit()
        artifact_dir = Path("./artifacts") / job_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        step_name = step_id or diagnostics.get("role", "context")
        artifact_path = artifact_dir / f"context_{step_name}.json"
        artifact_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_context_message(
        self, candidates: List[RankedCandidate], hints: List[str]
    ) -> Dict[str, str]:
        context_sections: List[str] = []
        for item in candidates:
            title = item.metadata.get("title") if isinstance(item.metadata, dict) else None
            header = f"# {item.source} (score={item.score:.2f})"
            if title:
                header += f" {title}"
            context_sections.append(f"{header}\n{item.content}")
        context_body = (
            "\n\n".join(context_sections) if context_sections else "# Context\nNo supplemental context selected."
        )
        hints_block = "\n".join(f"- {hint}" for hint in hints) if hints else "- No curator hints"
        return {
            "role": "system",
            "content": f"[Curated Context]\n{context_body}\n\n[Curator Hints]\n{hints_block}",
        }
