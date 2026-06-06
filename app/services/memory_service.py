"""
Memory Service — conversation history management.
Uses PostgreSQL for durable storage.
Redis is used only for global Q&A caching (handled in ai_service).
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.conversation import Conversation
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


# ---- User Management ----

async def get_or_create_user(
    db: AsyncSession,
    phone_number: str,
    name: Optional[str] = None,
) -> User:
    """
    Get an existing user by phone number, or create a new one.

    Args:
        db: Database session.
        phone_number: Patient's phone number.
        name: Patient's name (from WhatsApp profile).

    Returns:
        User model instance.
    """
    result = await db.execute(
        select(User).where(User.phone_number == phone_number)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update name if we have a newer one
        if name and name != "Unknown" and user.name != name:
            user.name = name
            await db.flush()
        return user

    # Create new user
    user = User(phone_number=phone_number, name=name)
    db.add(user)
    await db.flush()
    logger.info(f"New user created: {phone_number[:6]}***")
    return user


# ---- Conversation History ----

async def save_message(
    db: AsyncSession,
    user_id: UUID,
    role: str,
    message: str,
) -> Conversation:
    """
    Save a message to the conversation history in PostgreSQL.

    Args:
        db: Database session.
        user_id: UUID of the user.
        role: Message role ('user' or 'assistant').
        message: Message content.

    Returns:
        Created Conversation record.
    """
    conversation = Conversation(
        user_id=user_id,
        role=role,
        message=message,
    )
    db.add(conversation)
    
    # Update user's updated_at timestamp
    try:
        user = await db.get(User, user_id)
        if user:
            user.updated_at = datetime.now(timezone.utc)
    except Exception as e:
        logger.warning(f"Failed to update user's updated_at timestamp: {e}")
        
    await db.flush()

    return conversation


async def get_conversation_history(
    db: AsyncSession,
    user_id: UUID,
) -> List[Dict[str, str]]:
    """
    Get recent conversation history for a user from PostgreSQL.

    Args:
        db: Database session.
        user_id: UUID of the user.

    Returns:
        List of message dicts with 'role' and 'content' keys,
        ordered chronologically (oldest first).
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.timestamp.desc())
        .limit(settings.CONVERSATION_HISTORY_LIMIT)
    )
    conversations = result.scalars().all()

    # Reverse to chronological order (oldest first)
    history = [
        {"role": conv.role, "content": conv.message}
        for conv in reversed(conversations)
    ]

    return history


# ---- Cleanup ----

async def cleanup_old_conversations(db: AsyncSession) -> int:
    """
    Delete conversation records older than MEMORY_RETENTION_DAYS.

    Returns:
        Number of deleted records.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.MEMORY_RETENTION_DAYS)

    result = await db.execute(
        delete(Conversation).where(Conversation.timestamp < cutoff)
    )
    deleted_count = result.rowcount
    await db.commit()

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old conversation records")

    return deleted_count
