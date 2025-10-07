"""FastAPI middleware implementing Redis-backed rate limiting."""

from __future__ import annotations

import time
from typing import Awaitable, Callable, Iterable

import structlog
from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from backend.observability import RATE_LIMIT_BLOCK

IdentifierFunc = Callable[[Request], str]


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple fixed-window rate limiter backed by Redis."""

    def __init__(
        self,
        app,
        redis: Redis,
        *,
        requests: int,
        window_seconds: int,
        prefix: str,
        identifier: IdentifierFunc | None = None,
        allowlist: Iterable[str] | None = None,
        denylist: Iterable[str] | None = None,
        high_risk_paths: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._redis = redis
        self._requests = requests
        self._window = window_seconds
        self._prefix = prefix
        self._identifier = identifier or self._default_identifier
        self._allowlist = {entry.lower() for entry in (allowlist or [])}
        self._denylist = {entry.lower() for entry in (denylist or [])}
        self._high_risk_paths = set(high_risk_paths or [])
        self._logger = structlog.get_logger(__name__)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # type: ignore[override]
        identifier = self._identifier(request)
        if not identifier:
            return await call_next(request)

        key = self._build_key(identifier)
        lowered_id = identifier.lower()
        if lowered_id in self._allowlist:
            return await call_next(request)
        if lowered_id in self._denylist:
            RATE_LIMIT_BLOCK.inc()
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        path = request.url.path
        method = request.method.upper()
        try:
            current = await self._redis.incr(key)
            if current == 1:
                await self._redis.expire(key, self._window)
        except RedisError as exc:
            high_risk = path in self._high_risk_paths
            fail_open = method == "GET" and not high_risk
            log = self._logger.bind(path=path, method=method, identifier=identifier)
            log.error(
                "rate_limit.redis_unavailable", error=str(exc), high_risk=high_risk
            )
            if fail_open:
                log.warning("rate_limit.fail_open")
                return await call_next(request)
            RATE_LIMIT_BLOCK.inc()
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Authentication temporarily unavailable. Please retry."
                },
            )

        if current > self._requests:
            retry_after = await self._redis.ttl(key)
            RATE_LIMIT_BLOCK.inc()
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={
                    "Retry-After": (
                        str(max(retry_after, 0)) if retry_after else str(self._window)
                    )
                },
            )

        return await call_next(request)

    def _build_key(self, identifier: str) -> str:
        window = int(time.time() // self._window)
        return f"{self._prefix}:{identifier}:{window}"

    @staticmethod
    def _default_identifier(request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        return request.headers.get("X-Forwarded-For", "")


__all__ = ["RateLimiterMiddleware"]
