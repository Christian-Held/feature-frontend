from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware.security_headers import SecurityHeadersMiddleware, _CSP_VALUE


def test_security_headers_present():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    def ping():  # pragma: no cover - exercised via client
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/ping")
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == _CSP_VALUE
