from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from app.core.config import get_settings
from app.llm.provider import estimate_tokens


def _with_line_numbers(content: str, max_tokens: int) -> str:
    max_chars = max_tokens * 4
    lines = content.splitlines()
    numbered: List[str] = []
    for idx, line in enumerate(lines, start=1):
        numbered_line = f"{idx:04d}: {line}"
        numbered.append(numbered_line)
        if sum(len(entry) for entry in numbered) > max_chars:
            break
    return "\n".join(numbered)


def collect_repo_snippets(repo_path: Path | None, requested_files: Iterable[str] | None = None) -> List[dict]:
    if repo_path is None or not repo_path.exists():
        return []
    settings = get_settings()
    files: List[str] = []
    if requested_files:
        files = list(dict.fromkeys(requested_files))
    else:
        for candidate in repo_path.rglob("*"):
            if candidate.is_file():
                relative = str(candidate.relative_to(repo_path))
                files.append(relative)
                if len(files) >= settings.retriever_max_files:
                    break
    results: List[dict] = []
    for index, relative in enumerate(files[: settings.retriever_max_files]):
        path = repo_path / relative
        if not path.exists() or path.is_dir():
            continue
        try:
            data = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            data = path.read_text(encoding="utf-8", errors="ignore")
        if len(data) > 50_000:
            data = data[:50_000]
        snippet = _with_line_numbers(data, settings.retriever_max_snippet_tokens)
        tokens = estimate_tokens(snippet)
        results.append(
            {
                "id": f"repo::{relative}::{index}",
                "source": "repo",
                "content": f"{relative}:\n{snippet}",
                "tokens": tokens,
                "metadata": {"path": relative},
            }
        )
    return results
