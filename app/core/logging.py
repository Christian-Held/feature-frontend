from __future__ import annotations

import logging
from typing import Any, Dict

import structlog


def configure_logging(level: str = "info") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> "structlog.stdlib.BoundLogger":
    return structlog.get_logger(name)


def log_event(logger: "structlog.stdlib.BoundLogger", event: str, **fields: Dict[str, Any]) -> None:
    logger.info(event, **fields)
