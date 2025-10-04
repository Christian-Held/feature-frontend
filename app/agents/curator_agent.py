from __future__ import annotations

from typing import Iterable, List

from app.core.logging import get_logger

from app.context.curator import RankedCandidate

logger = get_logger(__name__)


class CuratorAgent:
    """Produces human-readable hints for the final prompt."""

    def build_hints(self, query: str, candidates: Iterable[RankedCandidate]) -> List[str]:
        hints: List[str] = []
        for candidate in candidates:
            source = candidate.source
            score = f"{candidate.score:.2f}"
            title = candidate.metadata.get("title") if isinstance(candidate.metadata, dict) else None
            prefix = f"[{source} score={score}]"
            if title:
                prefix = f"{prefix} {title}"
            snippet = candidate.content.strip().splitlines()[:3]
            body = " ".join(line.strip() for line in snippet)
            hints.append(f"{prefix} {body}")
        logger.info("curator_hints", count=len(hints))
        return hints
