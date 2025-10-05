from __future__ import annotations

from typing import Optional

from github import Github

from app.core.config import get_settings


def get_github_client(token: Optional[str] = None) -> Github:
    settings = get_settings()
    token_to_use = token or settings.github_token
    if not token_to_use:
        raise ValueError("GitHub token missing")
    return Github(login_or_token=token_to_use)
