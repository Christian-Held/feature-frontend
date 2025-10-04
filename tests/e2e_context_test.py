import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DRY_RUN", "1")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CONTEXT_ENGINE_ENABLED", "1")

from app.core import config
from app.main import create_application
from app.workers import job_worker


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    db_path = tmp_path / "orchestrator.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("GITHUB_OWNER", "demo")
    monkeypatch.setenv("GITHUB_REPO", "demo-repo")
    monkeypatch.setenv("MEMORY_MAX_ITEMS_PER_JOB", "10")
    config.get_settings.cache_clear()
    config.get_budget_limits.cache_clear()
    app = create_application()
    monkeypatch.setattr(job_worker.enqueue_job, "delay", lambda job_id: job_worker.execute_job.run(job_id))
    with TestClient(app) as client:
        yield client


def test_context_engine_diagnostics(setup_env):
    client = setup_env
    response = client.post("/context/docs", json={"title": "Guide", "text": "Use context engine"})
    assert response.status_code == 201
    response = client.post(
        "/tasks",
        json={
            "task": "Context engine e2e",
            "repo_owner": "demo",
            "repo_name": "demo-repo",
            "branch_base": "main",
            "budgetUsd": 5.0,
            "maxRequests": 5,
            "maxMinutes": 10,
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    response = client.post(
        f"/memory/{job_id}/notes",
        json={
            "type": "Decision",
            "title": "Seed",
            "body": "Enable context",
        },
    )
    assert response.status_code == 201
    context_resp = client.get(f"/jobs/{job_id}/context")
    assert context_resp.status_code == 200
    data = context_resp.json()
    assert data["budget"]["reserve_tokens"] == 8000
    assert data["tokens_final"] <= 70000
    assert "sources" in data and isinstance(data["sources"], list)
