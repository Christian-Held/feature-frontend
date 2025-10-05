import os

import pytest

from app.context.curator import Curator
from app.embeddings.openai_embed import OpenAIEmbeddingProvider
from app.core import config


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch, tmp_path):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "orchestrator.db"))
    monkeypatch.setenv("CURATOR_MIN_SCORE", "0")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_curator_prefers_relevant_candidate():
    provider = OpenAIEmbeddingProvider()
    curator = Curator(provider)
    query = "Implement HTTP client"
    candidates = [
        {"id": "1", "source": "repo", "content": "Implement HTTP client using requests", "tokens": 10, "metadata": {}},
        {"id": "2", "source": "memory", "content": "Refactor CSS layout", "tokens": 10, "metadata": {}},
    ]
    ranked = curator.rank(query, candidates)
    assert ranked
    assert ranked[0].id == "1"


def test_curator_filters_when_below_threshold(monkeypatch):
    monkeypatch.setenv("CURATOR_MIN_SCORE", "10")
    config.get_settings.cache_clear()
    provider = OpenAIEmbeddingProvider()
    curator = Curator(provider)
    ranked = curator.rank("irrelevant", [{"id": "1", "source": "repo", "content": "foo", "tokens": 1, "metadata": {}}])
    assert ranked == []
