"""OpenTelemetry instrumentation helpers for the auth service."""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from backend.core.config import AppConfig

_TRACING_CONFIGURED = False


def _build_resource(settings: AppConfig) -> Resource:
    attributes = {
        "service.name": settings.service_name,
        "service.namespace": "feature-auth",
        "service.version": settings.service_version,
        "deployment.environment": settings.environment,
        "cloud.region": settings.service_region,
    }
    return Resource.create(attributes)


def _build_exporter(settings: AppConfig) -> SpanExporter | None:
    if not settings.otel_exporter_endpoint:
        return None
    return OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint, insecure=settings.otel_exporter_insecure)


def setup_tracing(app: FastAPI, settings: AppConfig, exporter: Optional[SpanExporter] = None) -> None:
    """Configure OTLP tracing for FastAPI and Celery."""

    global _TRACING_CONFIGURED
    if _TRACING_CONFIGURED:
        return

    resource = _build_resource(settings)
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    span_exporter = exporter if exporter is not None else _build_exporter(settings)
    if span_exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(span_exporter))

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    app.add_middleware(OpenTelemetryMiddleware, tracer_provider=provider)

    celery_instrumentor = CeleryInstrumentor()
    is_instrumented = getattr(celery_instrumentor, "is_instrumented", None)
    if callable(is_instrumented):
        already = is_instrumented()
    else:  # pragma: no cover - compatibility shim
        already = getattr(celery_instrumentor, "is_instrumented_by_opentelemetry", False)
    if not already:
        celery_instrumentor.instrument(tracer_provider=provider)

    _TRACING_CONFIGURED = True


__all__ = ["setup_tracing"]
