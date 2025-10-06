from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis.aioredis

from backend.middleware.rate_limiter import RateLimiterMiddleware


def test_rate_limiter_blocks_after_threshold(settings_env):
    app = FastAPI()
    redis = fakeredis.aioredis.FakeRedis()

    app.add_middleware(
        RateLimiterMiddleware,
        redis=redis,
        requests=2,
        window_seconds=60,
        prefix="test",
    )

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    response = client.get("/ping")
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Please try again later."
