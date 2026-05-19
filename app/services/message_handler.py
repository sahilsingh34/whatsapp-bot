"""
Message Handler — main orchestrator for incoming WhatsApp messages.
Ties together all services into a cohesive message processing pipeline.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    whatsapp_service,
    ai_service,
    memory_service,
    appointment_service,
)
from app.services import learning_service
from app.utils.time_utils import is_within_working_hours

logger = logging.getLogger(__name__)

# Message sent during working hours
WORKING_HOURS_REPLY = (
    "Thank you for reaching out to My Pain Clinic Global! 🏥\n\n"
    "Our clinic is currently open and our team has received your message. "
    "A staff member will respond to you shortly.\n\n"
    "⏰ Clinic Hours: Mon-Sat, 8:30 AM – 8:00 PM\n"
    "📍 Unit B-1, V. N. Sphere Mall, Linking Rd, Bandra West, Mumbai 400050\n"
    "📞 +91 81694 00907 / +91 81694 00903"
)


async def handle_incoming_message(
    db: AsyncSession,
    phone: str,
    text: str,
    message_id: str,
    sender_name: str = "Unknown",
) -> None:
    """
    Process an incoming WhatsApp message through the full pipeline.

    Flow:
    1. Get/create user
    2. Check working hours
    3. Load conversation history
    4. Generate AI response
    5. Parse for appointments/escalations
    6. Send reply
    7. Mark as read
    """
    try:
        # ---- 1. Get or create user ----
        user = await memory_service.get_or_create_user(db, phone, sender_name)
        logger.info(f"📨 Message from {phone[:6]}***: \"{text[:50]}...\"")

        # ---- 2. Check working hours ----
        if is_within_working_hours():
            logger.info("⏰ Within working hours — sending staff acknowledgment")
            await whatsapp_service.send_text_message(phone, WORKING_HOURS_REPLY)
            await whatsapp_service.mark_as_read(message_id)
            # Still save the message for context
            await memory_service.save_message(db, user.id, "user", text)
            return

        # ---- 3. Load conversation history ----
        history = await memory_service.get_conversation_history(db, user.id)

        # ---- 4. Save incoming message ----
        await memory_service.save_message(db, user.id, "user", text)

        # ---- 5. Build conversation for AI ----
        conversation = history + [{"role": "user", "content": text}]

        # ---- 6. Generate AI response (with dynamic prompt enrichment) ----
        ai_response = await ai_service.generate_response(conversation, db=db)

        # ---- 7. Check for appointment data ----
        appointment_data = appointment_service.parse_appointment_from_response(ai_response)
        if appointment_data:
            await appointment_service.create_appointment(
                db=db,
                user_id=user.id,
                details=appointment_data,
                contact_number=phone,
            )
            logger.info(f"📅 Appointment captured for {phone[:6]}***")

        # ---- 8. Check for escalation ----
        is_escalated = "[ESCALATE]" in ai_response
        if is_escalated:
            # Here you would typically notify staff or create an escalation record in the DB
            logger.warning(f"🚨 Escalation triggered for {phone[:6]}***")

        # ---- 9. Clean response (remove internal tags) ----
        clean_response = appointment_service.clean_appointment_tags(ai_response)
        clean_response = clean_response.replace("[ESCALATE]", "").strip()

        # Handle empty/blank responses gracefully (e.g. when AI only returns JSON tag)
        if not clean_response:
            if appointment_data:
                clean_response = (
                    f"Thank you, {appointment_data.get('name', 'there')}! I have registered your appointment details "
                    f"for {appointment_data.get('pain_type', 'treatment')} on {appointment_data.get('date', 'your requested date')} "
                    f"at {appointment_data.get('time', 'your requested time')}. Our team will review this and contact "
                    f"you shortly to confirm. 🙏"
                )
            else:
                clean_response = (
                    "Thank you! How can I help you today? If you have questions about "
                    "our treatments or want to book a consultation, just let me know. 🙏"
                )

        # ---- 10. Save AI response to memory ----
        await memory_service.save_message(db, user.id, "assistant", clean_response)

        # ---- 11. Send reply via WhatsApp ----
        await whatsapp_service.send_text_message(phone, clean_response)

        # ---- 12. Mark original message as read ----
        await whatsapp_service.mark_as_read(message_id)

        logger.info(f"✅ Response sent to {phone[:6]}***")

        # ---- 13. Background: analyze conversation for self-learning ----
        asyncio.create_task(
            _background_learn(user.id),
            name=f"learn-{str(user.id)[:8]}",
        )

    except Exception as e:
        logger.error(f"❌ Error handling message from {phone}: {e}", exc_info=True)
        # Send a fallback error message
        try:
            await whatsapp_service.send_text_message(
                phone,
                "We apologize for the inconvenience. Our system is experiencing "
                "a temporary issue. Please try again shortly, or contact us during "
                "clinic hours (Mon-Sat, 9 AM – 9 PM). 🙏"
            )
        except Exception:
            logger.error("Failed to send error fallback message")


async def _background_learn(user_id) -> None:
    """
    Background task: analyze conversation for self-learning.
    Uses its own database session so it doesn't block the response flow.
    """
    try:
        from app.database.connection import async_session_factory

        async with async_session_factory() as db:
            await learning_service.analyze_conversation(db, user_id)
            await db.commit()
    except Exception as e:
        logger.warning(f"🧠 Background learning failed (non-blocking): {e}")
