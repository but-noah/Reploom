"""Unit tests for Calendar service layer."""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.integrations.calendar_service import (
    generate_time_slots,
    get_freebusy,
    get_availability_slots,
    CalendarServiceError,
    CalendarNotFoundError,
)


class TestGenerateTimeSlots:
    """Test generate_time_slots function with various scenarios."""

    def test_generate_slots_no_busy_periods(self):
        """Test slot generation when calendar is completely free."""
        # Test for Monday, Jan 15, 2025
        start_time = datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/New_York"))
        end_time = datetime(2025, 1, 16, 8, 0, tzinfo=ZoneInfo("America/New_York"))

        slots = generate_time_slots(
            busy_periods=[],
            start_time=start_time,
            end_time=end_time,
            timezone="America/New_York",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=3
        )

        # Should return 3 slots (max_slots)
        assert len(slots) == 3

        # First slot should start at 9:00 AM
        first_slot_start = datetime.fromisoformat(slots[0]["start"])
        assert first_slot_start.hour == 9
        assert first_slot_start.minute == 0

        # Each slot should be 30 minutes
        for slot in slots:
            start = datetime.fromisoformat(slot["start"])
            end = datetime.fromisoformat(slot["end"])
            duration = (end - start).total_seconds() / 60
            assert duration == 30

    def test_generate_slots_with_busy_periods(self):
        """Test slot generation avoiding busy periods."""
        start_time = datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 16, 8, 0, tzinfo=ZoneInfo("UTC"))

        # Busy from 10:00-11:00 and 14:00-15:00
        busy_periods = [
            {
                "start": "2025-01-15T10:00:00Z",
                "end": "2025-01-15T11:00:00Z"
            },
            {
                "start": "2025-01-15T14:00:00Z",
                "end": "2025-01-15T15:00:00Z"
            }
        ]

        slots = generate_time_slots(
            busy_periods=busy_periods,
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=5
        )

        # Verify no slots overlap with busy periods
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            slot_end = datetime.fromisoformat(slot["end"])

            for busy in busy_periods:
                busy_start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00"))

                # Ensure no overlap
                assert slot_end <= busy_start or slot_start >= busy_end

    def test_generate_slots_respects_working_hours(self):
        """Test that slots are only generated within working hours."""
        start_time = datetime(2025, 1, 15, 0, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 16, 23, 59, tzinfo=ZoneInfo("UTC"))

        slots = generate_time_slots(
            busy_periods=[],
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=10
        )

        # All slots should be between 9 AM and 5 PM
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            slot_end = datetime.fromisoformat(slot["end"])

            assert slot_start.hour >= 9
            assert slot_end.hour <= 17

    def test_generate_slots_skips_weekends(self):
        """Test that slots are not generated on weekends."""
        # Start on Friday, Jan 17, 2025
        start_time = datetime(2025, 1, 17, 8, 0, tzinfo=ZoneInfo("UTC"))
        # End on Tuesday, Jan 21, 2025 (includes Sat-Sun weekend)
        end_time = datetime(2025, 1, 21, 8, 0, tzinfo=ZoneInfo("UTC"))

        slots = generate_time_slots(
            busy_periods=[],
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=10
        )

        # Verify no slots are on Saturday (18th) or Sunday (19th)
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            # Saturday is 5, Sunday is 6
            assert slot_start.weekday() not in [5, 6]

    def test_generate_slots_different_duration(self):
        """Test slot generation with 45-minute slots."""
        start_time = datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 16, 8, 0, tzinfo=ZoneInfo("UTC"))

        slots = generate_time_slots(
            busy_periods=[],
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",
            slot_duration_minutes=45,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=3
        )

        # Each slot should be 45 minutes
        for slot in slots:
            start = datetime.fromisoformat(slot["start"])
            end = datetime.fromisoformat(slot["end"])
            duration = (end - start).total_seconds() / 60
            assert duration == 45

    def test_generate_slots_timezone_handling(self):
        """Test slot generation respects specified timezone."""
        # Start at midnight UTC
        start_time = datetime(2025, 1, 15, 0, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 16, 0, 0, tzinfo=ZoneInfo("UTC"))

        # Request slots in New York timezone (UTC-5)
        slots = generate_time_slots(
            busy_periods=[],
            start_time=start_time,
            end_time=end_time,
            timezone="America/New_York",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=3
        )

        # Verify slots are in the specified timezone
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            # Should have timezone info
            assert slot_start.tzinfo is not None

    def test_generate_slots_max_slots_limit(self):
        """Test that max_slots parameter is respected."""
        start_time = datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 20, 8, 0, tzinfo=ZoneInfo("UTC"))  # 5 days

        slots = generate_time_slots(
            busy_periods=[],
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=2
        )

        # Should return exactly 2 slots
        assert len(slots) == 2

    def test_generate_slots_invalid_timezone_fallback(self):
        """Test that invalid timezone falls back to UTC."""
        start_time = datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 16, 8, 0, tzinfo=ZoneInfo("UTC"))

        # Use invalid timezone
        slots = generate_time_slots(
            busy_periods=[],
            start_time=start_time,
            end_time=end_time,
            timezone="Invalid/Timezone",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=3
        )

        # Should still generate slots (using UTC fallback)
        assert len(slots) > 0

    def test_generate_slots_invalid_busy_period(self):
        """Test that invalid busy periods are skipped."""
        start_time = datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 16, 8, 0, tzinfo=ZoneInfo("UTC"))

        # Include one valid and one invalid busy period
        busy_periods = [
            {"start": "2025-01-15T10:00:00Z", "end": "2025-01-15T11:00:00Z"},
            {"invalid": "data"},  # Invalid format
            {"start": "not-a-date", "end": "also-not-a-date"}  # Invalid dates
        ]

        # Should not crash, just skip invalid periods
        slots = generate_time_slots(
            busy_periods=busy_periods,
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=3
        )

        # Should still generate slots
        assert len(slots) > 0

    def test_generate_slots_completely_busy_day(self):
        """Test when entire working day is busy."""
        # Test a single day that's completely busy
        start_time = datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("UTC"))
        end_time = datetime(2025, 1, 15, 18, 0, tzinfo=ZoneInfo("UTC"))  # Same day

        # Busy all day (9 AM - 5 PM)
        busy_periods = [
            {
                "start": "2025-01-15T09:00:00Z",
                "end": "2025-01-15T17:00:00Z"
            }
        ]

        slots = generate_time_slots(
            busy_periods=busy_periods,
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",
            slot_duration_minutes=30,
            working_hours_start=9,
            working_hours_end=17,
            max_slots=3
        )

        # Should return 0 slots since the entire day is busy
        assert len(slots) == 0


@pytest.mark.asyncio
class TestGetFreebusy:
    """Test get_freebusy function."""

    async def test_get_freebusy_success(self):
        """Test successful free/busy data retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calendars": {
                "primary": {
                    "busy": [
                        {
                            "start": "2025-01-15T14:00:00Z",
                            "end": "2025-01-15T15:00:00Z"
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.calendar_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            time_min = datetime(2025, 1, 15, 0, 0, tzinfo=ZoneInfo("UTC"))
            time_max = datetime(2025, 1, 16, 0, 0, tzinfo=ZoneInfo("UTC"))

            result = await get_freebusy("fake_token", time_min, time_max, "UTC")

            assert "calendars" in result
            assert "primary" in result["calendars"]
            assert len(result["calendars"]["primary"]["busy"]) == 1

    async def test_get_freebusy_not_found(self):
        """Test 404 error when calendar doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{"error": {"message": "Not found"}}'

        with patch("app.integrations.calendar_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            time_min = datetime(2025, 1, 15, 0, 0, tzinfo=ZoneInfo("UTC"))
            time_max = datetime(2025, 1, 16, 0, 0, tzinfo=ZoneInfo("UTC"))

            with pytest.raises(CalendarNotFoundError) as exc_info:
                await get_freebusy("fake_token", time_min, time_max, "UTC", "nonexistent")

            assert exc_info.value.status_code == 404

    async def test_get_freebusy_unauthorized(self):
        """Test 401 error for expired token."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b'{"error": {"message": "Unauthorized"}}'

        with patch("app.integrations.calendar_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            time_min = datetime(2025, 1, 15, 0, 0, tzinfo=ZoneInfo("UTC"))
            time_max = datetime(2025, 1, 16, 0, 0, tzinfo=ZoneInfo("UTC"))

            with pytest.raises(HTTPException) as exc_info:
                await get_freebusy("fake_token", time_min, time_max, "UTC")

            assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestGetAvailabilitySlots:
    """Test get_availability_slots function."""

    async def test_get_availability_slots_success(self):
        """Test successful availability slot generation."""
        mock_freebusy_response = MagicMock()
        mock_freebusy_response.status_code = 200
        mock_freebusy_response.json.return_value = {
            "calendars": {
                "primary": {
                    "busy": [
                        {
                            "start": "2025-01-15T14:00:00Z",
                            "end": "2025-01-15T15:00:00Z"
                        }
                    ]
                }
            }
        }
        mock_freebusy_response.raise_for_status = MagicMock()

        with patch("app.integrations.calendar_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_freebusy_response)
            mock_client.return_value = mock_async_client

            slots = await get_availability_slots(
                user_token="fake_token",
                window_days=7,
                timezone="UTC",
                slot_duration_minutes=30,
                working_hours_start=9,
                working_hours_end=17,
                max_slots=3
            )

            # Should return some slots
            assert isinstance(slots, list)
            # Each slot should have start and end
            for slot in slots:
                assert "start" in slot
                assert "end" in slot

    async def test_get_availability_slots_no_busy_periods(self):
        """Test availability when calendar is completely free."""
        mock_freebusy_response = MagicMock()
        mock_freebusy_response.status_code = 200
        mock_freebusy_response.json.return_value = {
            "calendars": {
                "primary": {
                    "busy": []  # No busy periods
                }
            }
        }
        mock_freebusy_response.raise_for_status = MagicMock()

        with patch("app.integrations.calendar_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_freebusy_response)
            mock_client.return_value = mock_async_client

            slots = await get_availability_slots(
                user_token="fake_token",
                window_days=7,
                timezone="UTC",
                slot_duration_minutes=30,
                max_slots=3
            )

            # Should return max_slots
            assert len(slots) <= 3

    async def test_get_availability_slots_timezone_parameter(self):
        """Test that timezone parameter is used correctly."""
        mock_freebusy_response = MagicMock()
        mock_freebusy_response.status_code = 200
        mock_freebusy_response.json.return_value = {
            "calendars": {"primary": {"busy": []}}
        }
        mock_freebusy_response.raise_for_status = MagicMock()

        with patch("app.integrations.calendar_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_freebusy_response)
            mock_client.return_value = mock_async_client

            await get_availability_slots(
                user_token="fake_token",
                window_days=7,
                timezone="America/New_York",
                slot_duration_minutes=30,
                max_slots=3
            )

            # Verify the API was called with correct timezone
            call_args = mock_async_client.post.call_args
            json_payload = call_args[1]["json"]
            assert json_payload["timeZone"] == "America/New_York"
