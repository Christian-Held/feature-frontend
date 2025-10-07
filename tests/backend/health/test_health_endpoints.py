import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.health import router as health_router


class _DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs):
        return 1


class _HealthyRedis:
    async def ping(self):
        return True


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(health_router)

    from backend.health import routes as health_routes

    monkeypatch.setattr(health_routes, "engine", type("E", (), {"connect": lambda self=None: _DummyConnection()})())
    monkeypatch.setattr(health_routes, "get_redis_client", lambda: _HealthyRedis())
    monkeypatch.setattr(health_routes, "smtp_ping", lambda _settings: True)

    return TestClient(app)


def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_failure(monkeypatch):
    app = FastAPI()
    app.include_router(health_router)

    from backend.health import routes as health_routes

    class FailEngine:
        def connect(self):
            raise RuntimeError("db down")

    class FailRedis:
        async def ping(self):
            raise RuntimeError("redis down")

    monkeypatch.setattr(health_routes, "engine", FailEngine())
    monkeypatch.setattr(health_routes, "get_redis_client", lambda: FailRedis())
    monkeypatch.setattr(health_routes, "smtp_ping", lambda _settings: False)

    client = TestClient(app)
    response = client.get("/readyz")
    assert response.status_code == 503
    body = response.json()
    assert body["database"] is False
    assert body["redis"] is False
    assert body["smtp"] is False
