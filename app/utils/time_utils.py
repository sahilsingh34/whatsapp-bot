"""
Time-based utilities for determining clinic working hours.
All times are in Asia/Kolkata (IST) timezone.

Real clinic hours from mypainclinicglobal.com:
  Monday–Saturday: 8:30 AM – 8:00 PM IST
  Sunday: Closed
"""

from datetime import datetime

import pytz

from app.config import get_settings

settings = get_settings()


def get_ist_now() -> datetime:
    """Get the current time in IST (Asia/Kolkata)."""
    ist = pytz.timezone(settings.TIMEZONE)
    return datetime.now(ist)


def is_within_working_hours() -> bool:
    """
    Check if the current time is within clinic working hours.

    Working hours (from website):
        Monday-Saturday: 8:30 AM to 8:00 PM IST
        Sunday: CLOSED (all day)

    Returns:
        True if currently within working hours.
        False if after hours, before hours, or Sunday.
    """
    now = get_ist_now()

    # Sunday = 6 in Python's weekday() (Monday=0, Sunday=6)
    if now.weekday() == 6:
        return False

    current_hour = now.hour
    current_minute = now.minute

    # Before 8:30 AM
    if current_hour < settings.WORKING_HOUR_START:
        return False
    if current_hour == settings.WORKING_HOUR_START and current_minute < settings.WORKING_HOUR_START_MINUTE:
        return False

    # At or after 8:00 PM (20:00)
    if current_hour >= settings.WORKING_HOUR_END:
        return False

    return True


def get_working_hours_message() -> str:
    """
    Returns a friendly message about clinic working hours.
    Used when the bot is active during non-working hours.
    """
    now = get_ist_now()

    if now.weekday() == 6:
        return (
            "Our clinic is closed on Sundays. "
            "We are open Monday to Saturday, 8:30 AM to 8:00 PM. "
            "Our AI assistant is here to help you in the meantime!"
        )

    current_hour = now.hour
    if current_hour >= settings.WORKING_HOUR_END:
        return (
            "Our clinic is currently closed for the day. "
            "We reopen tomorrow at 8:30 AM. "
            "Our AI assistant is here to help you in the meantime!"
        )

    if current_hour < settings.WORKING_HOUR_START or (
        current_hour == settings.WORKING_HOUR_START
        and now.minute < settings.WORKING_HOUR_START_MINUTE
    ):
        return (
            "Our clinic hasn't opened yet today. "
            "We open at 8:30 AM. "
            "Our AI assistant is here to help you in the meantime!"
        )

    return ""
