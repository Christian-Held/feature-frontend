from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List, Tuple

from app.core.logging import get_logger
from app.llm.provider import estimate_tokens

from .curator import RankedCandidate

logger = get_logger(__name__)


def _preferred_excerpt(text: str, max_chars: int) -> str:
    if "```" in text:
        parts: List[str] = []
        collect = False
        for line in text.splitlines():
            if line.strip().startswith("```"):
                collect = not collect
                continue
            if collect:
                parts.append(line)
            if sum(len(p) for p in parts) >= max_chars:
                break
        snippet = "\n".join(parts).strip()
        if snippet:
            return snippet[:max_chars]
    return text[:max_chars]


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    approx_chars = max_tokens * 4
    excerpt = _preferred_excerpt(text, approx_chars)
    if len(excerpt) <= approx_chars:
        return excerpt
    return excerpt[:approx_chars]


def compact_candidates(
    candidates: Iterable[RankedCandidate],
    *,
    available_tokens: int,
    threshold_ratio: float,
) -> Tuple[List[RankedCandidate], int]:
    compacted: List[RankedCandidate] = []
    operations = 0
    threshold = max(1, int(available_tokens * threshold_ratio))
    for candidate in candidates:
        tokens = estimate_tokens(candidate.content)
        if tokens <= threshold:
            compacted.append(replace(candidate, tokens=tokens))
            continue
        target_tokens = max(threshold, int(tokens * 0.5))
        truncated = _truncate_to_tokens(candidate.content, target_tokens)
        new_tokens = estimate_tokens(truncated)
        operations += 1
        compacted.append(
            replace(
                candidate,
                content=truncated,
                tokens=new_tokens,
            )
        )
    logger.info("compactor_done", candidates=len(compacted), ops=operations, threshold=threshold)
    return compacted, operations
