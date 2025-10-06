"""Logging configuration using structlog."""

from __future__ import annotations

import logging
from typing import Iterable

import structlog

from backend.core.config import AppConfig


class RedactingProcessor:
    """Structlog processor that redacts configured fields."""

    def __init__(self, redacted_fields: Iterable[str]):
        self._redacted = {field.lower() for field in redacted_fields}

    def __call__(self, logger, method_name, event_dict):  # type: ignore[override]
        for key in list(event_dict.keys()):
            if key.lower() in self._redacted:
                event_dict[key] = "***REDACTED***"
        return event_dict


def configure_logging(settings: AppConfig) -> None:
    """Configure structlog for JSON logging with redaction."""

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        RedactingProcessor(settings.log_redact_fields),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=settings.log_level)


__all__ = ["configure_logging", "RedactingProcessor"]
