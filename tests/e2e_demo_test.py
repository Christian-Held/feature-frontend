import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DRY_RUN", "1")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.core import config
from app.main import create_application
from app.workers import job_worker


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    db_path = tmp_path / "orchestrator.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("GITHUB_OWNER", "demo")
    monkeypatch.setenv("GITHUB_REPO", "demo-repo")
    config.get_settings.cache_clear()
    config.get_budget_limits.cache_clear()
    app = create_application()
    monkeypatch.setattr(job_worker.enqueue_job, "delay", lambda job_id: job_worker.execute_job.run(job_id))
    with TestClient(app) as client:
        yield client


def test_create_job_and_run(setup_env):
    client = setup_env
    response = client.post(
        "/tasks",
        json={
            "task": "Demo Aufgabe",
            "repo_owner": "demo",
            "repo_name": "demo-repo",
            "branch_base": "main",
            "budgetUsd": 5.0,
            "maxRequests": 10,
            "maxMinutes": 60,
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    job_resp = client.get(f"/jobs/{job_id}")
    assert job_resp.status_code == 200
    data = job_resp.json()
    assert data["status"] in {"completed", "running"}
    assert isinstance(data["pr_links"], list)
