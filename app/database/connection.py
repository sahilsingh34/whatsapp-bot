"""
Async PostgreSQL database connection using SQLAlchemy 2.0.
Provides session factory and initialization utilities.

IMPORTANT: Supabase uses PgBouncer in transaction mode, which does NOT support
prepared statements. We use async_creator to create raw asyncpg connections
with statement_cache_size=0, which is the ONLY bulletproof way to disable
prepared statements at the driver level.
"""

import logging
from typing import AsyncGenerator

import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

import uuid

# ---- Async Engine ----
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
    },
    echo=False,  # Disabled: Windows cp1252 console crashes on Unicode (emojis/arrows in learned insights)
    pool_size=3,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# ---- Session Factory ----
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---- Base Model ----
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ---- Dependency Injection ----
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an async database session.
    Use as a FastAPI dependency: db = Depends(get_db)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---- Lifecycle ----
async def init_db():
    """Create all database tables on startup."""
    # Import models so they are registered with Base.metadata
    from app.models import user, conversation, appointment, escalation, learned_insight  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def dispose_db():
    """Dispose database engine on shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed")
