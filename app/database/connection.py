"""
Async PostgreSQL database connection using SQLAlchemy 2.0.
Provides session factory and initialization utilities.
"""

import logging
from typing import AsyncGenerator
from urllib.parse import urlparse

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

# ---- Async Engine ----
# Supabase uses PgBouncer (transaction mode) which rejects prepared statements.
# Solution: NullPool (let PgBouncer handle pooling) + disable ALL prepared statement caches.
_base_url = settings.DATABASE_URL.split("?")[0]
_db_url = f"{_base_url}?prepared_statement_cache_size=0"

engine = create_async_engine(
    _db_url,
    echo=(settings.APP_ENV == "development"),
    poolclass=NullPool,  # PgBouncer handles pooling — no SQLAlchemy pool needed
    connect_args={
        "statement_cache_size": 0,
    },
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
    from app.models import user, conversation, appointment, escalation  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def dispose_db():
    """Dispose database engine on shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed")
