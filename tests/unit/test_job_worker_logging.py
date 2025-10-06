from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

if "dotenv" not in sys.modules:  # pragma: no cover - testing convenience
    sys.modules["dotenv"] = SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

from app.core.llm_logging import LLMTranscriptRecorder


def test_recorder_simulates_job_worker_flow(tmp_path: Path) -> None:
    recorder = LLMTranscriptRecorder()
    recorder.record(
        {
            "job_id": "job-42",
            "role": "cto-plan",
            "model": "gpt-cto",
            "provider": "openai",
            "messages": [{"role": "system", "content": "Task"}],
            "response_text": "[{\"title\": \"Step\"}]",
            "response": [{"title": "Step"}],
            "tokens_in": 12,
            "tokens_out": 6,
        }
    )
    recorder.set_base_path(tmp_path)
    recorder.record(
        {
            "job_id": "job-42",
            "step_id": "step-1",
            "role": "coder-step",
            "model": "gpt-coder",
            "provider": "openai",
            "messages": [{"role": "system", "content": "Code"}],
            "response_text": "diff",
            "summary": "summary",
            "tokens_in": 30,
            "tokens_out": 40,
        }
    )
    log_path = tmp_path / ".autodev" / "llm_calls.jsonl"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    plan_entry = json.loads(lines[0])
    coder_entry = json.loads(lines[1])
    assert plan_entry["response"][0]["title"] == "Step"
    assert coder_entry["summary"] == "summary"
    assert coder_entry["response_text"] == "diff"
