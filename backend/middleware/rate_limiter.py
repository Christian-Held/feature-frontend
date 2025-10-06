"""FastAPI middleware implementing Redis-backed rate limiting."""

from __future__ import annotations

import time
from typing import Awaitable, Callable

from fastapi import Request
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


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
    ) -> None:
        super().__init__(app)
        self._redis = redis
        self._requests = requests
        self._window = window_seconds
        self._prefix = prefix
        self._identifier = identifier or self._default_identifier

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # type: ignore[override]
        identifier = self._identifier(request)
        if not identifier:
            return await call_next(request)

        key = self._build_key(identifier)
        current = await self._redis.incr(key)
        if current == 1:
            await self._redis.expire(key, self._window)

        if current > self._requests:
            retry_after = await self._redis.ttl(key)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": str(max(retry_after, 0)) if retry_after else str(self._window)},
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

