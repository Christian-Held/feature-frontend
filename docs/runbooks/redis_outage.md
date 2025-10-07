# Redis Outage Runbook

## Symptoms
- `readyz` returns 503 citing Redis.
- `RateLimiterBlocksSpike` alert fires or login flow errors.
- Logs show `rate_limit.redis_unavailable` events.

## Immediate Response
1. Confirm Redis availability via monitoring or cloud provider dashboard.
2. Classify endpoints:
   - High-risk (login, 2FA, recovery) must fail closed.
   - Low-risk GETs should remain available (middleware already fails open).
3. If Redis is down, scale API pods only if necessary to reduce connection churn.
4. Communicate to stakeholders about authentication impact.

## Mitigation
- Attempt Redis failover or restart managed instance.
- Flush or disable problematic Lua scripts/keys causing lock if applicable.
- Update deny/allow lists manually if certain IPs cause overload.

## Recovery
- After Redis recovery, verify `/readyz` success and metrics normalization.
- Rebuild caches as needed and ensure rate limiter counters reset.
- Run load smoke test (`scripts/load_smoke_test.py`) to confirm p95 latency within SLO.
