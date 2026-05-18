"""
Conversation model — stores chat history for context memory.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="One of: user, assistant, system",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationship
    user = relationship("User", back_populates="conversations")

    # Composite index for efficient history retrieval
    __table_args__ = (
        Index("ix_conversations_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, role={self.role}, user={self.user_id})>"
