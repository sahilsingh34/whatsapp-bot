"""
Memory Service — conversation history management.
Uses Redis for hot cache, PostgreSQL for durable storage.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.redis import get_redis
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
    Save a message to the conversation history.

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

    # Save session event in Redis Agent Memory (bypassed in development to eliminate US-East network latency)
    if settings.APP_ENV != "development":
        try:
            from redis_agent_memory import AgentMemory, models
            import time
            
            role_enum = models.MessageRole.USER if role == "user" else models.MessageRole.ASSISTANT
            
            with AgentMemory(
                server_url=settings.REDIS_MEMORY_ENDPOINT,
                api_key=settings.REDIS_MEMORY_API_KEY,
                store_id=settings.REDIS_MEMORY_STORE_ID,
            ) as agent_memory:
                agent_memory.add_session_event(
                    session_id=str(user_id),
                    actor_id=str(user_id),
                    role=role_enum,
                    content=[{"text": message}],
                    created_at=int(time.time() * 1000),
                )
                logger.info(f"💾 Session event appended to Redis Agent Memory for: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to append to Redis Agent Memory: {e}")

    return conversation


async def get_conversation_history(
    db: AsyncSession,
    user_id: UUID,
) -> List[Dict[str, str]]:
    """
    Get recent conversation history for a user.
    Checks Redis Agent Memory first, falls back to PostgreSQL.

    Args:
        db: Database session.
        user_id: UUID of the user.

    Returns:
        List of message dicts with 'role' and 'content' keys,
        ordered chronologically (oldest first).
    """
    # ---- Try Redis Agent Memory first (bypassed in development to eliminate US-East network latency) ----
    if settings.APP_ENV != "development":
        try:
            from redis_agent_memory import AgentMemory
            
            with AgentMemory(
                server_url=settings.REDIS_MEMORY_ENDPOINT,
                api_key=settings.REDIS_MEMORY_API_KEY,
                store_id=settings.REDIS_MEMORY_STORE_ID,
            ) as agent_memory:
                session_mem = agent_memory.get_session_memory(session_id=str(user_id))
                if session_mem and hasattr(session_mem, "events") and session_mem.events:
                    logger.info(f"🏆 Cache hit from Redis Agent Memory for user {user_id}")
                    history = []
                    for event in session_mem.events:
                        # Map enum to role string
                        role_str = "user" if event.role.value == "user" else "assistant"
                        msg_text = ""
                        if event.content:
                            for chunk in event.content:
                                if hasattr(chunk, "text") and chunk.text:
                                    msg_text += chunk.text
                                elif isinstance(chunk, dict) and "text" in chunk:
                                    msg_text += chunk["text"]
                        if msg_text:
                            history.append({"role": role_str, "content": msg_text})
                    
                    if history:
                        return history[-settings.CONVERSATION_HISTORY_LIMIT:]
        except Exception as e:
            # Log 404/not found as a clean info block instead of a warning
            err_str = str(e)
            if "404" in err_str or "not found" in err_str.lower():
                logger.info(f"ℹ️ Redis Agent Memory: session not found (expected for new chat) for {user_id}")
            else:
                logger.warning(f"Redis Agent Memory session read failed: {e}")

    # ---- Fall back to PostgreSQL ----
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

    # ---- Cache in Redis Agent Memory (bypassed in development) ----
    if settings.APP_ENV != "development":
        try:
            from redis_agent_memory import AgentMemory, models
            import time
            
            with AgentMemory(
                server_url=settings.REDIS_MEMORY_ENDPOINT,
                api_key=settings.REDIS_MEMORY_API_KEY,
                store_id=settings.REDIS_MEMORY_STORE_ID,
            ) as agent_memory:
                for i, h in enumerate(history):
                    role_enum = models.MessageRole.USER if h["role"] == "user" else models.MessageRole.ASSISTANT
                    agent_memory.add_session_event(
                        session_id=str(user_id),
                        actor_id=str(user_id),
                        role=role_enum,
                        content=[{"text": h["content"]}],
                        created_at=int((time.time() - len(history) + i) * 1000),
                    )
                logger.info(f"Cached {len(history)} messages in Redis Agent Memory for user {user_id}")
        except Exception as e:
            logger.warning(f"Redis Agent Memory cache write failed: {e}")

    return history


# ---- Redis Agent Memory Long-Term Semantic Storage ----

async def save_long_term_memory(memory_id: str, text: str):
    """
    Save a fact or learned insight to Redis Agent Memory's long-term semantic memory.
    """
    try:
        from redis_agent_memory import AgentMemory
        
        with AgentMemory(
            server_url=settings.REDIS_MEMORY_ENDPOINT,
            api_key=settings.REDIS_MEMORY_API_KEY,
            store_id=settings.REDIS_MEMORY_STORE_ID,
        ) as agent_memory:
            agent_memory.bulk_create_long_term_memories(memories=[
                {"id": memory_id, "text": text}
            ])
            logger.info(f"🧠 Saved long-term semantic memory in Redis: {memory_id}")
    except Exception as e:
        logger.warning(f"Failed to save long-term semantic memory: {e}")


async def search_long_term_memory(query_text: str) -> List[str]:
    """
    Search Redis Agent Memory's long-term semantic memory for matching facts.
    """
    try:
        from redis_agent_memory import AgentMemory
        
        with AgentMemory(
            server_url=settings.REDIS_MEMORY_ENDPOINT,
            api_key=settings.REDIS_MEMORY_API_KEY,
            store_id=settings.REDIS_MEMORY_STORE_ID,
        ) as agent_memory:
            results = agent_memory.search_long_term_memory(request={"text": query_text})
            matched_texts = []
            if results and hasattr(results, "memories") and results.memories:
                for mem in results.memories:
                    # Inspect both dictionary and object formats
                    if hasattr(mem, "text") and mem.text:
                        matched_texts.append(mem.text)
                    elif isinstance(mem, dict) and "text" in mem:
                        matched_texts.append(mem["text"])
            return matched_texts
    except Exception as e:
        logger.warning(f"Semantic search failed on Redis Agent Memory: {e}")
        return []


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
