"""
Dashboard API — provides conversation data for the admin dashboard.
Returns customer conversations in a structured spreadsheet-like format.
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.connection import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.appointment import Appointment

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("/api/conversations")
async def get_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    updated_since: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get customer conversations with support for incremental syncing (updated_since).
    Eager loads relationships using selectinload to solve N+1 database queries.
    """
    # Build query prefetching conversations and appointments
    query = select(User).options(
        selectinload(User.conversations),
        selectinload(User.appointments)
    )

    # Filter by updated_since if provided
    if updated_since:
        try:
            # Parse ISO format datetime (accepting Z or +00:00)
            dt = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
            query = query.where(
                or_(
                    User.updated_at >= dt,
                    (User.updated_at == None) & (User.created_at >= dt)
                )
            )
        except Exception as e:
            logger.warning(f"Failed to parse updated_since timestamp '{updated_since}': {e}")

    # Order by updated_at descending or created_at descending
    query = query.order_by(desc(func.coalesce(User.updated_at, User.created_at))).limit(limit).offset(offset)
    
    users_result = await db.execute(query)
    users = users_result.scalars().all()

    conversations_data = []

    for user in users:
        # Sort user conversations in-memory
        messages = sorted(user.conversations, key=lambda c: c.timestamp)
        msg_count = len(messages)

        # Build message thread - take last 30 in-memory
        thread_slice = messages[-30:] if msg_count > 30 else messages
        thread = []
        for msg in thread_slice:
            thread.append({
                "role": msg.role,
                "message": msg.message,
                "time": msg.timestamp.strftime("%Y-%m-%d %H:%M") if msg.timestamp else "",
            })

        # Get latest appointment in-memory
        appointment = None
        if user.appointments:
            appointment = max(user.appointments, key=lambda a: a.created_at)

        # Extract key topics in-memory
        user_messages = [m.message for m in messages if m.role == "user"]
        key_topics = _extract_key_topics(user_messages)

        # Last activity
        last_msg = messages[-1] if messages else None
        
        # Last updated timestamp (ISO format) for the frontend to track
        last_updated_dt = user.updated_at or user.created_at
        last_updated_str = last_updated_dt.isoformat() if last_updated_dt else ""

        conversations_data.append({
            "user_id": str(user.id),
            "name": user.name or "Unknown",
            "phone": user.phone_number,
            "message_count": msg_count,
            "last_activity": last_msg.timestamp.strftime("%Y-%m-%d %H:%M") if last_msg else "",
            "appointment_status": appointment.status if appointment else "none",
            "patient_name": appointment.patient_name if appointment else None,
            "pain_type": appointment.pain_type if appointment else None,
            "key_topics": key_topics,
            "thread": thread,
            "updated_at": last_updated_str,
            "appointments": [
                {
                    "id": str(a.id),
                    "patient_name": a.patient_name,
                    "pain_type": a.pain_type,
                    "preferred_date": a.preferred_date,
                    "preferred_time": a.preferred_time,
                    "contact_number": a.contact_number,
                    "status": a.status,
                    "is_urgent": a.is_urgent,
                    "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
                }
                for a in sorted(user.appointments, key=lambda a: a.created_at, reverse=True)
            ] if user.appointments else [],
        })

    # Total user count
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar() or 0

    return {
        "total_customers": total,
        "showing": len(conversations_data),
        "offset": offset,
        "conversations": conversations_data,
    }


@router.get("/api/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get overall dashboard statistics."""
    # Total users
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # Total messages
    msgs_count = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0

    # Total appointments
    appts_count = (await db.execute(select(func.count(Appointment.id)))).scalar() or 0

    # Pending appointments
    pending = (await db.execute(
        select(func.count(Appointment.id))
        .where(Appointment.status == "pending")
    )).scalar() or 0

    return {
        "total_customers": users_count,
        "total_messages": msgs_count,
        "total_appointments": appts_count,
        "pending_appointments": pending,
        "avg_messages_per_customer": round(msgs_count / max(users_count, 1), 1),
    }


def _extract_key_topics(user_messages: List[str]) -> List[str]:
    """Extract key conversation topics from user messages."""
    topics = set()
    keywords = {
        "appointment": "Appointment Booking",
        "book": "Appointment Booking",
        "slot": "Appointment Booking",
        "ice bath": "Ice Bath",
        "cryotherapy": "Cryotherapy",
        "physiotherapy": "Physiotherapy",
        "spine": "Spine Treatment",
        "laser": "Laser Therapy",
        "pilates": "Pilates",
        "hbot": "HBOT",
        "hyperbaric": "HBOT",
        "pelvic": "Pelvic Chair",
        "red light": "Red Light Therapy",
        "consultation": "Consultation",
        "price": "Pricing Inquiry",
        "cost": "Pricing Inquiry",
        "charges": "Pricing Inquiry",
        "pain": "Pain Treatment",
        "knee": "Knee Pain",
        "back": "Back Pain",
        "neck": "Neck Pain",
        "shoulder": "Shoulder Pain",
        "address": "Location Inquiry",
        "timing": "Timing Inquiry",
        "hours": "Timing Inquiry",
    }

    combined = " ".join(user_messages).lower()
    for keyword, topic in keywords.items():
        if keyword in combined:
            topics.add(topic)

    return sorted(list(topics))[:5]  # Max 5 topics


from pydantic import BaseModel

class StatusUpdateRequest(BaseModel):
    status: str

@router.post("/api/appointments/{appt_id}/status")
async def update_appointment_status(
    appt_id: str,
    req: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    import uuid
    try:
        uid = uuid.UUID(appt_id)
    except ValueError:
        return {"success": False, "error": "Invalid appointment ID format"}
        
    # Get the appointment
    appt_query = select(Appointment).where(Appointment.id == uid)
    result = await db.execute(appt_query)
    appt = result.scalar_one_or_none()
    
    if not appt:
        return {"success": False, "error": "Appointment not found"}
        
    if req.status not in ["pending", "confirmed", "cancelled"]:
        return {"success": False, "error": "Invalid status value"}
        
    appt.status = req.status
    
    # Also update the user's updated_at timestamp to force cache invalidation / sync on the frontend
    user_query = select(User).where(User.id == appt.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if user:
        user.updated_at = datetime.utcnow()
        
    await db.commit()
    return {"success": True, "status": appt.status}
