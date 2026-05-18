"""
Appointment Service — parses AI responses for appointment data
and manages appointment records.
"""

import json
import logging
import re
from typing import Optional, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment

logger = logging.getLogger(__name__)

# Regex to extract appointment JSON from AI response
APPOINTMENT_PATTERN = re.compile(
    r"\[APPOINTMENT_COLLECTED\]\s*(\{.*?\})",
    re.DOTALL,
)


def parse_appointment_from_response(ai_response: str) -> Optional[Dict[str, str]]:
    """
    Detect and extract appointment details from an AI response.

    The AI includes [APPOINTMENT_COLLECTED]{...json...} when it has
    collected all required appointment details.

    Args:
        ai_response: Raw AI response text.

    Returns:
        Dict with appointment details if found, None otherwise.
    """
    match = APPOINTMENT_PATTERN.search(ai_response)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
        logger.info(f"📅 Appointment details extracted: {data.get('name', 'Unknown')}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse appointment JSON: {e}")
        return None


def clean_appointment_tags(text: str) -> str:
    """
    Remove appointment tags from the response before sending to patient.

    Args:
        text: AI response with possible tags.

    Returns:
        Cleaned text without tags.
    """
    # Remove the entire [APPOINTMENT_COLLECTED]{...} block
    cleaned = APPOINTMENT_PATTERN.sub("", text)
    return cleaned.strip()


async def create_appointment(
    db: AsyncSession,
    user_id: UUID,
    details: Dict[str, str],
    contact_number: str,
    is_urgent: bool = False,
) -> Appointment:
    """
    Create a new appointment record from extracted details.

    Args:
        db: Database session.
        user_id: UUID of the user.
        details: Dict with name, pain_type, date, time.
        contact_number: Patient's phone number.
        is_urgent: Whether this is an urgent case.

    Returns:
        Created Appointment record.
    """
    appointment = Appointment(
        user_id=user_id,
        patient_name=details.get("name"),
        pain_type=details.get("pain_type"),
        preferred_date=details.get("date"),
        preferred_time=details.get("time"),
        contact_number=contact_number,
        is_urgent=is_urgent,
        status="pending",
    )
    db.add(appointment)
    await db.flush()

    logger.info(
        f"📅 Appointment created: {appointment.patient_name} — "
        f"{appointment.pain_type} on {appointment.preferred_date}"
    )
    return appointment


async def get_pending_appointments(db: AsyncSession) -> List[Appointment]:
    """Get all pending appointments, newest first."""
    result = await db.execute(
        select(Appointment)
        .where(Appointment.status == "pending")
        .order_by(Appointment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all_appointments(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Appointment]:
    """Get appointments with optional status filter."""
    query = select(Appointment).order_by(Appointment.created_at.desc()).limit(limit)

    if status:
        query = query.where(Appointment.status == status)

    result = await db.execute(query)
    return list(result.scalars().all())


async def update_appointment_status(
    db: AsyncSession,
    appointment_id: UUID,
    new_status: str,
) -> Optional[Appointment]:
    """Update an appointment's status."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if appointment:
        appointment.status = new_status
        await db.flush()
        logger.info(f"Appointment {appointment_id} updated to {new_status}")

    return appointment
