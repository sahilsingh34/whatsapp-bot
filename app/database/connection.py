"""
Async PostgreSQL database connection using SQLAlchemy 2.0.
Provides session factory and initialization utilities.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---- Async Engine ----
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
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
