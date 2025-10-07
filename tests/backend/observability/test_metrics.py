from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.observability import (
    AUTH_LOGIN_SUCCESS,
    EMAIL_SEND_LATENCY,
    PrometheusRequestMiddleware,
    metrics_router,
)


def test_metrics_endpoint_exposes_series():
    app = FastAPI()
    app.include_router(metrics_router())

    AUTH_LOGIN_SUCCESS.inc()
    EMAIL_SEND_LATENCY.observe(150)

    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "auth_login_success_total" in body
    assert "email_send_latency_ms_bucket" in body


def test_request_duration_histogram_records():
    app = FastAPI()
    app.add_middleware(PrometheusRequestMiddleware, excluded_paths=set())

    @app.get("/hello")
    async def hello():  # pragma: no cover - exercised via client
        return {"status": "ok"}

    app.include_router(metrics_router())

    client = TestClient(app)
    assert client.get("/hello").status_code == 200
    metrics_response = client.get("/metrics")
    assert "http_request_duration_seconds_bucket" in metrics_response.text
