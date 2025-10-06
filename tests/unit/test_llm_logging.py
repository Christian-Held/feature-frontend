from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

if "dotenv" not in sys.modules:  # pragma: no cover - testing convenience
    sys.modules["dotenv"] = SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

from app.core.llm_logging import LLMTranscriptRecorder, append_llm_log


def test_append_llm_log_writes_json_line(tmp_path: Path) -> None:
    entry = {
        "job_id": "job-123",
        "role": "cto-plan",
        "model": "gpt-test",
        "provider": "openai",
        "messages": [{"role": "system", "content": "hello"}],
        "response_text": "response",
        "response": {"steps": []},
        "tokens_in": 10,
        "tokens_out": 5,
    }
    log_file = append_llm_log(tmp_path, entry)
    contents = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert contents, "log file should contain at least one line"
    payload = json.loads(contents[-1])
    assert payload["response_text"] == "response"
    assert payload["messages"][0]["content"] == "hello"
    assert payload["tokens_in"] == 10
    assert payload.get("timestamp"), "timestamp should be auto populated"


def test_recorder_buffers_until_base_path(tmp_path: Path) -> None:
    recorder = LLMTranscriptRecorder()
    entry = {
        "job_id": "job-123",
        "role": "cto-plan",
        "model": "gpt-test",
        "provider": "openai",
        "messages": [{"role": "system", "content": "hello"}],
        "response_text": "response",
        "response": {"steps": []},
        "tokens_in": 10,
        "tokens_out": 5,
    }
    recorder.record(entry)
    log_path = tmp_path / ".autodev" / "llm_calls.jsonl"
    assert not log_path.exists()
    recorder.set_base_path(tmp_path)
    assert log_path.exists()
    payloads = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert payloads[0]["response_text"] == "response"


def test_recorder_flushes_multiple_entries(tmp_path: Path) -> None:
    recorder = LLMTranscriptRecorder()
    recorder.record(
        {
            "job_id": "job-1",
            "role": "cto-plan",
            "model": "gpt-test",
            "provider": "openai",
            "messages": [{"role": "system", "content": "hello"}],
            "response_text": "plan",
            "response": {"steps": []},
            "tokens_in": 2,
            "tokens_out": 1,
        }
    )
    recorder.set_base_path(tmp_path)
    recorder.record(
        {
            "job_id": "job-1",
            "role": "coder-step",
            "step_id": "step-1",
            "model": "gpt-test",
            "provider": "openai",
            "messages": [{"role": "system", "content": "code"}],
            "response_text": "diff",
            "summary": "summary",
            "tokens_in": 3,
            "tokens_out": 4,
        }
    )
    log_path = tmp_path / ".autodev" / "llm_calls.jsonl"
    payloads = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(payloads) == 2
    assert payloads[1]["role"] == "coder-step"
    assert payloads[1]["response_text"] == "diff"
