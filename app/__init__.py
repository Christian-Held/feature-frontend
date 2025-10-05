"""Auto Dev Orchestrator backend package."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_PATH = _ROOT_DIR / ".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH, override=False)
