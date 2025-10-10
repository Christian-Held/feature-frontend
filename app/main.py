"""Compatibility wrapper exposing the unified backend FastAPI app.

The legacy orchestrator package previously mounted its own FastAPI instance
from this module. The consolidated architecture now lives under
``backend.app``. Importing ``app.main`` continues to work for existing
scripts while delegating all logic to the new backend application factory.
"""

from __future__ import annotations

from backend.app import app as app  # re-export for backwards compatibility
from backend.app import create_app as create_application

__all__ = ["app", "create_application"]
