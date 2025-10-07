import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from backend.auth.email.tasks import send_verification_email_task
from backend.observability.otel import setup_tracing


def test_tracing_emits_spans(settings_env, monkeypatch):
    otel_module = importlib.import_module("backend.observability.otel")
    monkeypatch.setattr(otel_module, "_TRACING_CONFIGURED", False)

    app = FastAPI()
    exporter = InMemorySpanExporter()
    setup_tracing(app, settings_env, exporter=exporter)

    @app.get("/ping")
    async def ping():  # pragma: no cover - invoked via client
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    trace.get_tracer_provider().force_flush()
    spans = exporter.get_finished_spans()
    assert any("/ping" in span.name for span in spans)

    exporter.clear()
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("parent"):
        send_verification_email_task.apply(kwargs={"to_email": "user@example.com", "verification_url": "https://example.com"})
    trace.get_tracer_provider().force_flush()
    spans = exporter.get_finished_spans()
    assert any("email" in span.name.lower() or "celery" in span.name.lower() for span in spans)
