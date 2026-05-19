"""
Insights API — Admin endpoints to view and manage self-learned knowledge.
Lets clinic admins see what the bot has learned from patient conversations.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services import learning_service

router = APIRouter(prefix="/insights", tags=["insights"])
logger = logging.getLogger(__name__)


class InsightResponse(BaseModel):
    id: str
    category: str
    insight_text: str
    source_pattern: str
    frequency: int
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None


class ToggleRequest(BaseModel):
    is_active: bool


@router.get("/")
async def list_insights(
    category: Optional[str] = Query(None, description="Filter by category: faq, treatment_insight, conversation_pattern"),
    active_only: bool = Query(False, description="Only show active insights"),
    db: AsyncSession = Depends(get_db),
):
    """List all learned insights with optional filters."""
    insights = await learning_service.get_all_insights(
        db, category=category, active_only=active_only
    )
    return {
        "count": len(insights),
        "insights": [
            InsightResponse(
                id=str(i.id),
                category=i.category,
                insight_text=i.insight_text,
                source_pattern=i.source_pattern,
                frequency=i.frequency,
                is_active=i.is_active,
                created_at=i.created_at.isoformat() if i.created_at else "",
                updated_at=i.updated_at.isoformat() if i.updated_at else None,
            )
            for i in insights
        ],
    }


@router.get("/stats")
async def insight_stats(db: AsyncSession = Depends(get_db)):
    """Get summary statistics about learned insights."""
    stats = await learning_service.get_insight_stats(db)
    return stats


@router.patch("/{insight_id}")
async def toggle_insight(
    insight_id: str,
    req: ToggleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a specific learned insight."""
    insight = await learning_service.toggle_insight(
        db, UUID(insight_id), req.is_active
    )
    if not insight:
        return {"error": "Insight not found"}

    return {
        "id": str(insight.id),
        "is_active": insight.is_active,
        "message": f"Insight {'activated' if insight.is_active else 'deactivated'} successfully",
    }
