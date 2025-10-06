from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

LOG_SUBDIR = ".autodev"
LOG_FILENAME = "llm_calls.jsonl"


def _ensure_timestamp(entry: Dict[str, Any]) -> Dict[str, Any]:
    if "timestamp" not in entry or not entry.get("timestamp"):
        entry = {**entry, "timestamp": datetime.now(timezone.utc).isoformat()}
    return entry


def append_llm_log(base_path: Path, entry: Dict[str, Any]) -> Path:
    """Append a single LLM call transcript to the log file."""

    log_dir = Path(base_path) / LOG_SUBDIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / LOG_FILENAME
    payload = _ensure_timestamp(entry)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        handle.write("\n")
    return log_file


def append_llm_logs(base_path: Path, entries: Iterable[Dict[str, Any]]) -> Optional[Path]:
    log_file: Optional[Path] = None
    for entry in entries:
        log_file = append_llm_log(base_path, entry)
    return log_file


@dataclass
class LLMTranscriptRecorder:
    """Buffers LLM transcripts until a repository path is available."""

    base_path: Optional[Path] = None
    _buffer: List[Dict[str, Any]] = field(default_factory=list)

    def set_base_path(self, base_path: Path) -> None:
        self.base_path = Path(base_path)
        self.flush()

    def record(self, entry: Dict[str, Any]) -> None:
        self._buffer.append(entry)
        self.flush()

    def flush(self) -> None:
        if self.base_path is None or not self._buffer:
            return
        append_llm_logs(self.base_path, self._buffer)
        self._buffer.clear()
