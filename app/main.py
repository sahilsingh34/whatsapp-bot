"""
FastAPI application entry point.
Handles lifespan events, middleware, and router registration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database.connection import init_db, dispose_db
from app.database.redis import init_redis, close_redis
from app.routes import webhook, health, appointments

# ---- Logging Setup ----
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---- Lifespan (startup / shutdown) ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    logger.info("🚀 Starting My Pain Clinic Global WhatsApp Bot...")

    # Startup
    await init_db()
    logger.info("✅ Database initialized")

    await init_redis()
    logger.info("✅ Redis connected")

    logger.info("✅ Application ready — listening for WhatsApp messages")
    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    await close_redis()
    await dispose_db()
    logger.info("👋 Shutdown complete")


# ---- FastAPI App ----
app = FastAPI(
    title="My Pain Clinic Global — WhatsApp AI Assistant",
    description=(
        "AI-powered WhatsApp assistant for My Pain Clinic Global, Bandra. "
        "Automatically responds to patient queries during non-working hours."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---- Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Register Routers ----
app.include_router(webhook.router)
app.include_router(health.router)
app.include_router(appointments.router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint — basic info."""
    return {
        "service": "My Pain Clinic Global WhatsApp AI Assistant",
        "version": "1.0.0",
        "status": "running",
    }
