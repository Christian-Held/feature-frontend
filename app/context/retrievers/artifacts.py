from __future__ import annotations

from pathlib import Path
from typing import List

from app.llm.provider import estimate_tokens


def collect_artifacts(job_id: str, base_dir: Path | None = None) -> List[dict]:
    base = base_dir or Path("./artifacts")
    job_dir = base / job_id
    if not job_dir.exists():
        return []
    results: List[dict] = []
    for path in job_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.stat().st_size > 50_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        tokens = estimate_tokens(text)
        results.append(
            {
                "id": f"artifact::{path.name}",
                "source": "artifact",
                "content": f"{path.name}:\n{text}",
                "tokens": tokens,
                "metadata": {"path": str(path)},
            }
        )
    return results
