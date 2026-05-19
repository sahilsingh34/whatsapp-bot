"""
Async Redis client for conversation caching.
"""

import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---- Module-level client ----
_redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """Initialize and return the Redis client."""
    global _redis_client
    try:
        logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        # Verify connection
        await _redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        logger.info("Falling back to in-memory FakeRedis client for development/demo...")
        import fakeredis.aioredis
        _redis_client = fakeredis.aioredis.FakeRedis(
            decode_responses=True,
        )
    return _redis_client


def get_redis() -> aioredis.Redis:
    """Get the active Redis client instance."""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis_client


async def close_redis():
    """Close the Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")
