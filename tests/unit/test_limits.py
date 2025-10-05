from datetime import datetime, timedelta

import pytest

from app.workers.job_worker import _check_limits


class DummyJob:
    def __init__(self, cost, budget, requests, max_requests, started_at, max_minutes):
        self.cost_usd = cost
        self.budget_usd = budget
        self.requests_made = requests
        self.max_requests = max_requests
        self.started_at = started_at
        self.max_minutes = max_minutes


def test_check_limits_passes():
    job = DummyJob(1.0, 5.0, 10, 20, datetime.utcnow(), 60)
    _check_limits(job, now=datetime.utcnow())


def test_check_limits_budget_exceeded():
    job = DummyJob(5.0, 5.0, 0, 20, datetime.utcnow(), 60)
    with pytest.raises(RuntimeError):
        _check_limits(job, now=datetime.utcnow())


def test_check_limits_time_exceeded():
    started = datetime.utcnow() - timedelta(minutes=120)
    job = DummyJob(1.0, 5.0, 0, 20, started, 60)
    with pytest.raises(RuntimeError):
        _check_limits(job, now=datetime.utcnow())
