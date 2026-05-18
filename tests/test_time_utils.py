"""
Tests for time-based working hours logic.
Real clinic hours: Monday-Saturday 8:30 AM - 8:00 PM IST
"""

from datetime import datetime
from unittest.mock import patch

import pytz
import pytest


IST = pytz.timezone("Asia/Kolkata")


def _make_ist_datetime(year, month, day, hour, minute=0):
    """Create an IST-aware datetime."""
    return IST.localize(datetime(year, month, day, hour, minute))


class TestIsWithinWorkingHours:
    """Test the is_within_working_hours function against real clinic hours."""

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_10am_is_working_hours(self, mock_now):
        """Monday 10 AM should be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 10)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is True

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_830am_is_working_hours(self, mock_now):
        """Monday 8:30 AM (exact start) should be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 8, 30)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is True

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_829am_is_not_working_hours(self, mock_now):
        """Monday 8:29 AM (before start) should NOT be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 8, 29)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_759pm_is_working_hours(self, mock_now):
        """Monday 7:59 PM should be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 19, 59)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is True

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_8pm_is_not_working_hours(self, mock_now):
        """Monday 8:00 PM (end of hours) should NOT be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 20)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_11pm_is_not_working_hours(self, mock_now):
        """Monday 11 PM should NOT be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 23)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_3am_is_not_working_hours(self, mock_now):
        """Monday 3 AM should NOT be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 3)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_monday_7am_is_not_working_hours(self, mock_now):
        """Monday 7 AM (before 8:30) should NOT be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 18, 7)  # Monday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_sunday_noon_is_not_working_hours(self, mock_now):
        """Sunday at noon should NOT be within working hours (clinic closed)."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 17, 12)  # Sunday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_sunday_9am_is_not_working_hours(self, mock_now):
        """Sunday 9 AM should NOT be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 17, 9)  # Sunday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_saturday_5pm_is_working_hours(self, mock_now):
        """Saturday 5 PM should be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 16, 17)  # Saturday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is True

    @patch("app.utils.time_utils.get_ist_now")
    def test_saturday_8pm_is_not_working_hours(self, mock_now):
        """Saturday 8 PM should NOT be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 16, 20)  # Saturday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is False

    @patch("app.utils.time_utils.get_ist_now")
    def test_wednesday_noon_is_working_hours(self, mock_now):
        """Wednesday 12 PM should be within working hours."""
        mock_now.return_value = _make_ist_datetime(2026, 5, 20, 12)  # Wednesday
        from app.utils.time_utils import is_within_working_hours
        assert is_within_working_hours() is True
