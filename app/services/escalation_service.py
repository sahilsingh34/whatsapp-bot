"""
Escalation Service — parses and detects emergency/escalation contexts in chats.
"""

import re

ESCALATE_KEYWORDS = [
    r"\bemergency\b",
    r"\bsevere pain\b",
    r"\bbleeding\b",
    r"\bchest pain\b",
    r"\baccident\b",
    r"\bhospital\b",
]


def detect_escalation(response: str) -> bool:
    """Check if the AI response explicitly contains the escalate tag."""
    return "[ESCALATE]" in response


def detect_escalation_keywords(message: str) -> bool:
    """Check if the user message contains emergency keywords."""
    msg_lower = message.lower()
    for kw_pattern in ESCALATE_KEYWORDS:
        if re.search(kw_pattern, msg_lower):
            return True
    return False
