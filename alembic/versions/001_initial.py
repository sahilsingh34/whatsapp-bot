"""Initial migration - create all tables

Revision ID: 001_initial
Revises: None
Create Date: 2026-05-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- Users Table ----
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_phone_number", "users", ["phone_number"])

    # ---- Conversations Table ----
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_timestamp", "conversations", ["timestamp"])
    op.create_index(
        "ix_conversations_user_timestamp",
        "conversations",
        ["user_id", "timestamp"],
    )

    # ---- Appointments Table ----
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("patient_name", sa.String(255), nullable=True),
        sa.Column("pain_type", sa.String(255), nullable=True),
        sa.Column("preferred_date", sa.String(100), nullable=True),
        sa.Column("preferred_time", sa.String(100), nullable=True),
        sa.Column("contact_number", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("is_urgent", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ---- Escalations Table ----
    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("message_excerpt", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("escalations")
    op.drop_table("appointments")
    op.drop_table("conversations")
    op.drop_table("users")
