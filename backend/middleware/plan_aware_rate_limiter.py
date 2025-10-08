"""Plan-aware rate limiting middleware that applies subscription multipliers."""

from __future__ import annotations

from typing import Awaitable, Callable

import structlog
from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from backend.observability import RATE_LIMIT_BLOCK


class PlanAwareRateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiter that applies subscription plan multipliers."""

    def __init__(
        self,
        app,
        redis: Redis,
        *,
        base_requests: int,
        window_seconds: int,
        prefix: str,
    ) -> None:
        super().__init__(app)
        self._redis = redis
        self._base_requests = base_requests
        self._window = window_seconds
        self._prefix = prefix
        self._logger = structlog.get_logger(__name__)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # type: ignore[override]
        # Skip rate limiting for non-authenticated requests or health checks
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if not user:
            # No user authenticated, use base rate limit with IP
            identifier = self._get_client_ip(request)
            multiplier = 1.0
        else:
            # User authenticated, get their plan multiplier
            identifier = str(user.id)
            multiplier = await self._get_user_rate_limit_multiplier(user.id)

        # Calculate effective limit
        effective_limit = int(self._base_requests * multiplier)

        # Build Redis key
        key = f"{self._prefix}:global:{identifier}"

        try:
            current = await self._redis.incr(key)
            if current == 1:
                await self._redis.expire(key, self._window)

            if current > effective_limit:
                retry_after = await self._redis.ttl(key)
                RATE_LIMIT_BLOCK.inc()

                self._logger.warning(
                    "rate_limit.exceeded",
                    identifier=identifier,
                    current=current,
                    limit=effective_limit,
                    multiplier=multiplier,
                    path=request.url.path,
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please try again later.",
                        "limit": effective_limit,
                        "reset_in": max(retry_after, 0) if retry_after else self._window,
                    },
                    headers={
                        "X-RateLimit-Limit": str(effective_limit),
                        "X-RateLimit-Remaining": str(max(effective_limit - current, 0)),
                        "X-RateLimit-Reset": str(max(retry_after, 0) if retry_after else self._window),
                        "Retry-After": str(max(retry_after, 0) if retry_after else self._window),
                    },
                )

            # Add rate limit headers to successful response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(effective_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(effective_limit - current, 0))
            retry_after = await self._redis.ttl(key)
            response.headers["X-RateLimit-Reset"] = str(max(retry_after, 0) if retry_after else self._window)

            return response

        except RedisError as exc:
            self._logger.error(
                "rate_limit.redis_error",
                error=str(exc),
                identifier=identifier,
            )
            # Fail open for GET requests
            if request.method.upper() == "GET":
                return await call_next(request)

            RATE_LIMIT_BLOCK.inc()
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Rate limiting temporarily unavailable. Please retry."
                },
            )

    async def _get_user_rate_limit_multiplier(self, user_id) -> float:
        """Get the rate limit multiplier for a user based on their subscription plan."""
        try:
            from backend.subscription import service as subscription_service
            from backend.db.session import SessionLocal

            db = SessionLocal()
            try:
                plan = subscription_service.get_user_plan(db, user_id)
                if plan and plan.rate_limit_multiplier:
                    return float(plan.rate_limit_multiplier)
                return 1.0
            finally:
                db.close()
        except Exception as exc:
            self._logger.warning(
                "rate_limit.multiplier_lookup_failed",
                user_id=str(user_id),
                error=str(exc),
            )
            return 1.0  # Default to base rate if lookup fails

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"


__all__ = ["PlanAwareRateLimiterMiddleware"]
