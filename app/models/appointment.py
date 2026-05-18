"""
Appointment model — stores appointment leads captured by AI.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Appointment(Base):
    __tablename__ = "appointments"

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
    patient_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    pain_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    preferred_date: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    preferred_time: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    contact_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="One of: pending, confirmed, cancelled",
    )
    is_urgent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    user = relationship("User", back_populates="appointments")

    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, patient={self.patient_name}, status={self.status})>"
