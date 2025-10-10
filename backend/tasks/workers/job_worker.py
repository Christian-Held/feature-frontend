"""Compatibility layer that forwards job execution to the legacy worker."""

from __future__ import annotations

from app.workers.job_worker import execute_job as legacy_execute_job


def execute_job(*args, **kwargs):
    return legacy_execute_job(*args, **kwargs)


__all__ = ["execute_job"]
