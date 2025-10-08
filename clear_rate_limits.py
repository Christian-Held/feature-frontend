"""Clear rate limits from Redis."""
import asyncio
from backend.redis.client import get_redis_client

async def clear_limits():
    redis = get_redis_client()

    # Clear all rate limit keys
    cursor = 0
    total_deleted = 0

    while True:
        cursor, keys = await redis.scan(cursor, match="rate_limit:*", count=100)
        if keys:
            deleted = await redis.delete(*keys)
            total_deleted += deleted
            print(f"Deleted {deleted} rate limit keys")

        if cursor == 0:
            break

    # Clear all auth-related keys (login failures, locks, etc.)
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="auth:*", count=100)
        if keys:
            deleted = await redis.delete(*keys)
            total_deleted += deleted
            print(f"Deleted {deleted} auth keys")

        if cursor == 0:
            break

    await redis.aclose()
    print(f"\n✓ Total keys deleted: {total_deleted}")
    print("✓ All rate limits and auth locks cleared!")

if __name__ == "__main__":
    asyncio.run(clear_limits())
