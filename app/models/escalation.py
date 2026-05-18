"""
Escalation model — tracks urgent cases flagged for human intervention.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Escalation(Base):
    __tablename__ = "escalations"

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
    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Why escalation was triggered (e.g., emergency, surgery)",
    )
    message_excerpt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="One of: pending, acknowledged, resolved",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    user = relationship("User", back_populates="escalations")

    def __repr__(self) -> str:
        return f"<Escalation(id={self.id}, reason={self.reason}, status={self.status})>"
