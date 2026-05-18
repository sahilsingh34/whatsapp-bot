"""
Tests for webhook payload parsing and verification.
"""

import pytest

from app.services.whatsapp_service import verify_webhook, parse_incoming_message


class TestWebhookVerification:
    """Test the webhook verification handshake."""

    def test_valid_verification(self):
        """Valid token should return challenge."""
        from unittest.mock import patch
        with patch("app.services.whatsapp_service.settings") as mock_settings:
            mock_settings.VERIFY_TOKEN = "test-token-123"
            result = verify_webhook("subscribe", "test-token-123", "challenge-abc")
            assert result == "challenge-abc"

    def test_invalid_token(self):
        """Invalid token should return None."""
        from unittest.mock import patch
        with patch("app.services.whatsapp_service.settings") as mock_settings:
            mock_settings.VERIFY_TOKEN = "test-token-123"
            result = verify_webhook("subscribe", "wrong-token", "challenge-abc")
            assert result is None

    def test_invalid_mode(self):
        """Non-subscribe mode should return None."""
        from unittest.mock import patch
        with patch("app.services.whatsapp_service.settings") as mock_settings:
            mock_settings.VERIFY_TOKEN = "test-token-123"
            result = verify_webhook("unsubscribe", "test-token-123", "challenge-abc")
            assert result is None


class TestMessageParsing:
    """Test incoming WhatsApp message payload parsing."""

    def test_valid_text_message(self):
        """Should correctly parse a standard text message payload."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "919876543210",
                                    "phone_number_id": "phone-id-123",
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Rahul Sharma"},
                                        "wa_id": "919876543210",
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "msg-id-abc",
                                        "timestamp": "1716000000",
                                        "text": {"body": "I have back pain"},
                                        "type": "text",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        result = parse_incoming_message(payload)
        assert result is not None
        assert result["phone"] == "919876543210"
        assert result["text"] == "I have back pain"
        assert result["message_id"] == "msg-id-abc"
        assert result["name"] == "Rahul Sharma"

    def test_non_text_message_returns_none(self):
        """Should return None for non-text messages (e.g., images)."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "msg-id-img",
                                        "type": "image",
                                        "image": {"id": "img-123"},
                                    }
                                ],
                                "contacts": [],
                            },
                        }
                    ],
                }
            ],
        }

        result = parse_incoming_message(payload)
        assert result is None

    def test_empty_payload_returns_none(self):
        """Should return None for empty payload."""
        result = parse_incoming_message({})
        assert result is None

    def test_no_messages_returns_none(self):
        """Should return None when no messages in payload."""
        payload = {
            "entry": [{"changes": [{"value": {"messages": []}}]}]
        }
        result = parse_incoming_message(payload)
        assert result is None


class TestAppointmentParsing:
    """Test appointment extraction from AI responses."""

    def test_valid_appointment_extraction(self):
        """Should extract appointment JSON from AI response."""
        from app.services.appointment_service import parse_appointment_from_response

        response = (
            "Great! I've noted your appointment details. "
            'Our team will confirm shortly. [APPOINTMENT_COLLECTED]'
            '{"name": "Rahul Sharma", "pain_type": "back pain", '
            '"date": "May 20", "time": "10 AM"}'
        )

        result = parse_appointment_from_response(response)
        assert result is not None
        assert result["name"] == "Rahul Sharma"
        assert result["pain_type"] == "back pain"
        assert result["date"] == "May 20"
        assert result["time"] == "10 AM"

    def test_no_appointment_returns_none(self):
        """Should return None when no appointment tag in response."""
        from app.services.appointment_service import parse_appointment_from_response

        response = "How can I help you today?"
        result = parse_appointment_from_response(response)
        assert result is None


class TestEscalationDetection:
    """Test escalation detection from AI responses and user messages."""

    def test_escalate_tag_detected(self):
        """Should detect [ESCALATE] tag in AI response."""
        from app.services.escalation_service import detect_escalation

        response = "I'm very concerned about your situation. Let me escalate this immediately. [ESCALATE]"
        assert detect_escalation(response) is True

    def test_no_escalate_tag(self):
        """Should not detect escalation when tag is absent."""
        from app.services.escalation_service import detect_escalation

        response = "How can I help you today?"
        assert detect_escalation(response) is False

    def test_keyword_detection_emergency(self):
        """Should detect 'emergency' keyword in user message."""
        from app.services.escalation_service import detect_escalation_keywords

        assert detect_escalation_keywords("This is an emergency!") is True

    def test_keyword_detection_severe_pain(self):
        """Should detect 'severe pain' in user message."""
        from app.services.escalation_service import detect_escalation_keywords

        assert detect_escalation_keywords("I have severe pain in my chest") is True

    def test_no_keywords(self):
        """Should not detect escalation for normal messages."""
        from app.services.escalation_service import detect_escalation_keywords

        assert detect_escalation_keywords("I want to book an appointment") is False
