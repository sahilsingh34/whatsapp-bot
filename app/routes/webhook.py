"""
WhatsApp Webhook routes.
Handles Meta webhook verification and incoming message processing.
"""

import logging

from fastapi import APIRouter, Request, Query, BackgroundTasks, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services.whatsapp_service import verify_webhook, parse_incoming_message
from app.services.message_handler import handle_incoming_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


@router.get("/webhook")
async def webhook_verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """
    Meta Webhook Verification Endpoint.

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge
    to verify the webhook URL. We must return the challenge value if the token matches.
    """
    challenge = verify_webhook(hub_mode, hub_token, hub_challenge)

    if challenge:
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse(content="Verification failed", status_code=403)


@router.post("/webhook")
async def webhook_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive incoming WhatsApp messages.

    Returns 200 immediately to Meta (required within 5 seconds),
    then processes the message asynchronously in the background.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(content={"error": "Invalid JSON"}, status_code=400)

    # Verify this is a WhatsApp Business Account event
    if payload.get("object") != "whatsapp_business_account":
        return JSONResponse(content={"status": "ignored"}, status_code=200)

    # Parse the incoming message
    message_data = parse_incoming_message(payload)

    if message_data:
        logger.info(
            f"📩 Incoming message from {message_data['phone'][:6]}***: "
            f"\"{message_data['text'][:50]}\""
        )

        # Process message in background to return 200 quickly
        background_tasks.add_task(
            handle_incoming_message,
            db=db,
            phone=message_data["phone"],
            text=message_data["text"],
            message_id=message_data["message_id"],
            sender_name=message_data["name"],
        )
    else:
        logger.debug("Webhook received but no actionable message found")

    # Always return 200 to Meta
    return JSONResponse(content={"status": "received"}, status_code=200)
