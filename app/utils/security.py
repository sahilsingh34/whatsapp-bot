"""
Security utilities for webhook verification and API key authentication.
"""

import hashlib
import hmac
import logging
from typing import Optional

from fastapi import HTTPException, Header, Request

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    app_secret: Optional[str] = None,
) -> bool:
    """
    Verify the HMAC-SHA256 signature of an incoming Meta webhook payload.

    Args:
        payload: Raw request body bytes.
        signature: The X-Hub-Signature-256 header value (sha256=...).
        app_secret: Meta App Secret for HMAC verification.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected_signature = signature.split("sha256=")[1]

    if not app_secret:
        # If no app secret configured, skip verification (development mode)
        logger.warning("Webhook signature verification skipped — no app secret configured")
        return True

    computed_hash = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_hash, expected_signature)


async def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    FastAPI dependency to require a valid API key for protected endpoints.

    Usage:
        @router.get("/protected", dependencies=[Depends(require_api_key)])
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return x_api_key
