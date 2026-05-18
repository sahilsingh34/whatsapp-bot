"""
Health check endpoint.
Verifies database and Redis connectivity.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database.connection import engine
from app.database.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns service status including database and Redis connectivity.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "unknown",
            "redis": "unknown",
        },
    }
    all_healthy = True

    # ---- Check Database ----
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health["services"]["database"] = "connected"
    except Exception as e:
        health["services"]["database"] = f"error: {str(e)[:100]}"
        all_healthy = False

    # ---- Check Redis ----
    try:
        redis = get_redis()
        await redis.ping()
        health["services"]["redis"] = "connected"
    except Exception as e:
        health["services"]["redis"] = f"error: {str(e)[:100]}"
        all_healthy = False

    if not all_healthy:
        health["status"] = "degraded"
        return JSONResponse(content=health, status_code=503)

    return JSONResponse(content=health, status_code=200)
