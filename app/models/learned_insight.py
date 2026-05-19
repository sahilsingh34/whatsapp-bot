"""
LearnedInsight model — stores knowledge extracted from patient conversations.
The self-learning system mines chat patterns and stores them here
so the AI can dynamically improve its responses over time.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class LearnedInsight(Base):
    __tablename__ = "learned_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="One of: faq, treatment_insight, conversation_pattern",
    )
    insight_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The learned knowledge in natural language for prompt injection",
    )
    source_pattern: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The original question/pattern that triggered this insight",
    )
    frequency: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="How many times this pattern has been observed",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Toggle to enable/disable injection into prompt",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # Index for fast retrieval of active insights
    __table_args__ = (
        Index("ix_learned_insights_active_category", "is_active", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<LearnedInsight(id={self.id}, category={self.category}, "
            f"freq={self.frequency}, active={self.is_active})>"
        )
