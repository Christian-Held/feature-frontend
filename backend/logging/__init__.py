"""Logging configuration using structlog."""

from __future__ import annotations

import logging
import re
from typing import Iterable

import structlog

from backend.core.config import AppConfig
from backend.middleware.request_context import (
    get_admin_user_id,
    get_request_id,
    get_user_id,
)

try:
    from opentelemetry import trace
except Exception:  # pragma: no cover - otel optional for some environments
    trace = None  # type: ignore[assignment]


class RedactingProcessor:
    """Structlog processor that redacts configured fields."""

    def __init__(self, redacted_fields: Iterable[str]):
        self._redacted = {field.lower() for field in redacted_fields}

    def __call__(self, logger, method_name, event_dict):  # type: ignore[override]
        for key in list(event_dict.keys()):
            key_lower = key.lower()
            if key_lower in self._redacted or "email" in key_lower:
                event_dict[key] = "***REDACTED***"
            elif isinstance(event_dict[key], str) and self._is_email(event_dict[key]):
                event_dict[key] = "***REDACTED***"
        return event_dict

    @staticmethod
    def _is_email(value: str) -> bool:
        return bool(
            re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+", value, flags=re.IGNORECASE)
        )


def configure_logging(settings: AppConfig) -> None:
    """Configure structlog for JSON logging with redaction."""

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    processors = [
        timestamper,
        RedactingProcessor(settings.log_redact_fields),
        _request_context_processor,
        _otel_context_processor,
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    # Convert log level string to logging level constant
    log_level_num = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level_num),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=log_level_num)


def _request_context_processor(logger, method_name, event_dict):  # type: ignore[override]
    request_id = get_request_id()
    admin_user_id = get_admin_user_id()
    user_id = get_user_id()
    if request_id and "request_id" not in event_dict:
        event_dict["request_id"] = request_id
    if admin_user_id and "admin_user_id" not in event_dict:
        event_dict["admin_user_id"] = admin_user_id
    if user_id and "user_id" not in event_dict:
        event_dict["user_id"] = user_id
    return event_dict


def _otel_context_processor(logger, method_name, event_dict):  # type: ignore[override]
    if trace is None:
        return event_dict
    span = trace.get_current_span()
    context = span.get_span_context() if span else None
    if context and context.is_valid:
        if "trace_id" not in event_dict:
            event_dict["trace_id"] = format(context.trace_id, "032x")
        if "span_id" not in event_dict:
            event_dict["span_id"] = format(context.span_id, "016x")
    return event_dict


__all__ = ["configure_logging", "RedactingProcessor"]
