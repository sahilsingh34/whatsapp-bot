"""
WhatsApp Cloud API service.
Handles all communication with the Meta WhatsApp Business API.
"""

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Meta Graph API base URL
GRAPH_API_URL = "https://graph.facebook.com/v21.0"


def verify_webhook(mode: str, token: str, challenge: str) -> Optional[str]:
    """
    Handle Meta webhook verification handshake.

    Args:
        mode: hub.mode parameter (should be "subscribe")
        token: hub.verify_token parameter
        challenge: hub.challenge parameter

    Returns:
        The challenge string if verification succeeds, None otherwise.
    """
    if mode == "subscribe" and token == settings.VERIFY_TOKEN:
        logger.info("✅ Webhook verification successful")
        return challenge

    logger.warning("❌ Webhook verification failed — token mismatch")
    return None


def parse_incoming_message(payload: dict) -> Optional[dict]:
    """
    Extract message details from a WhatsApp webhook payload.

    Args:
        payload: Raw webhook JSON payload from Meta.

    Returns:
        Dict with keys: phone, text, message_id, name
        or None if payload doesn't contain a valid text message.
    """
    try:
        entry = payload.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None

        message = messages[0]

        # Only handle text messages for MVP
        if message.get("type") != "text":
            logger.info(f"Skipping non-text message type: {message.get('type')}")
            return None

        # Extract sender info
        contacts = value.get("contacts", [])
        sender_name = contacts[0].get("profile", {}).get("name", "Unknown") if contacts else "Unknown"

        return {
            "phone": message["from"],
            "text": message["text"]["body"],
            "message_id": message["id"],
            "name": sender_name,
        }

    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return None


async def send_text_message(to: str, text: str) -> bool:
    """
    Send a text message via WhatsApp Cloud API.

    Args:
        to: Recipient phone number (with country code, no +).
        text: Message text to send.

    Returns:
        True if message was sent successfully, False otherwise.
    """
    url = f"{GRAPH_API_URL}/{settings.PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                logger.info(f"✅ Message sent to {to[:6]}***")
                return True
            else:
                logger.error(
                    f"❌ Failed to send message to {to}: "
                    f"status={response.status_code}, body={response.text}"
                )
                return False

    except httpx.RequestError as e:
        logger.error(f"❌ Network error sending message to {to}: {e}")
        return False


async def mark_as_read(message_id: str) -> bool:
    """
    Mark a received message as read (blue ticks).

    Args:
        message_id: The WhatsApp message ID to mark as read.

    Returns:
        True if successful, False otherwise.
    """
    url = f"{GRAPH_API_URL}/{settings.PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code == 200

    except httpx.RequestError as e:
        logger.error(f"Failed to mark message as read: {e}")
        return False
