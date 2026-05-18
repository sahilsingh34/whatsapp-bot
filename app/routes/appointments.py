"""
Appointment management API routes.
Protected with API key authentication for admin use.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.utils.security import require_api_key
from app.services.appointment_service import (
    get_all_appointments,
    update_appointment_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/appointments",
    tags=["appointments"],
    dependencies=[Depends(require_api_key)],
)


class AppointmentResponse(BaseModel):
    """Appointment response schema."""
    id: str
    patient_name: Optional[str]
    pain_type: Optional[str]
    preferred_date: Optional[str]
    preferred_time: Optional[str]
    contact_number: Optional[str]
    status: str
    is_urgent: bool
    created_at: str


class StatusUpdateRequest(BaseModel):
    """Request body for updating appointment status."""
    status: str  # pending, confirmed, cancelled


@router.get("")
async def list_appointments(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all appointments with optional status filter."""
    appointments = await get_all_appointments(db, status=status, limit=limit)

    return JSONResponse(
        content={
            "count": len(appointments),
            "appointments": [
                {
                    "id": str(apt.id),
                    "patient_name": apt.patient_name,
                    "pain_type": apt.pain_type,
                    "preferred_date": apt.preferred_date,
                    "preferred_time": apt.preferred_time,
                    "contact_number": apt.contact_number,
                    "status": apt.status,
                    "is_urgent": apt.is_urgent,
                    "created_at": apt.created_at.isoformat(),
                }
                for apt in appointments
            ],
        }
    )


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single appointment by ID."""
    from sqlalchemy import select
    from app.models.appointment import Appointment

    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    apt = result.scalar_one_or_none()

    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return JSONResponse(
        content={
            "id": str(apt.id),
            "patient_name": apt.patient_name,
            "pain_type": apt.pain_type,
            "preferred_date": apt.preferred_date,
            "preferred_time": apt.preferred_time,
            "contact_number": apt.contact_number,
            "status": apt.status,
            "is_urgent": apt.is_urgent,
            "created_at": apt.created_at.isoformat(),
        }
    )


@router.patch("/{appointment_id}")
async def update_status(
    appointment_id: UUID,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an appointment's status (confirm/cancel)."""
    valid_statuses = ["pending", "confirmed", "cancelled"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    appointment = await update_appointment_status(db, appointment_id, body.status)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return JSONResponse(
        content={
            "message": f"Appointment updated to {body.status}",
            "id": str(appointment.id),
            "status": appointment.status,
        }
    )
