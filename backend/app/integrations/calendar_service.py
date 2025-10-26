"""Google Calendar API service layer.

This module provides functions for interacting with the Google Calendar API,
including availability checking and free/busy slot generation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import httpx
from fastapi import HTTPException

from app.core.tracing import get_tracer, safe_span_attributes
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class CalendarServiceError(Exception):
    """Base exception for Calendar service errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "calendar_service_error"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class CalendarNotFoundError(CalendarServiceError):
    """Raised when a calendar is not found."""

    def __init__(self, message: str = "Calendar not found"):
        super().__init__(
            message=message,
            status_code=404,
            error_code="calendar_not_found"
        )


def generate_time_slots(
    busy_periods: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    timezone: str,
    slot_duration_minutes: int = 30,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
    max_slots: int = 3
) -> list[dict[str, str]]:
    """Generate available time slots from free/busy data.

    This function analyzes busy periods and generates available meeting slots
    within working hours.

    Args:
        busy_periods: List of busy time ranges from Calendar API
        start_time: Start of the search window (timezone-aware)
        end_time: End of the search window (timezone-aware)
        timezone: Timezone for working hours calculation (e.g., "America/New_York")
        slot_duration_minutes: Duration of each slot in minutes (default 30)
        working_hours_start: Start of working hours in 24h format (default 9 = 9 AM)
        working_hours_end: End of working hours in 24h format (default 17 = 5 PM)
        max_slots: Maximum number of slots to return (default 3)

    Returns:
        List of available time slots with start and end times in ISO format

    Example:
        >>> busy = [{"start": "2025-01-15T14:00:00Z", "end": "2025-01-15T15:00:00Z"}]
        >>> slots = generate_time_slots(
        ...     busy_periods=busy,
        ...     start_time=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("UTC")),
        ...     end_time=datetime(2025, 1, 16, 8, 0, tzinfo=ZoneInfo("UTC")),
        ...     timezone="America/New_York",
        ...     slot_duration_minutes=30,
        ...     working_hours_start=9,
        ...     working_hours_end=17
        ... )
        >>> print(slots[0])
        {"start": "2025-01-15T09:00:00-05:00", "end": "2025-01-15T09:30:00-05:00"}
    """
    with tracer.start_as_current_span("calendar.generate_time_slots") as span:
        span.set_attributes(safe_span_attributes(
            timezone=timezone,
            slot_duration_minutes=slot_duration_minutes,
            working_hours_start=working_hours_start,
            working_hours_end=working_hours_end,
            busy_periods_count=len(busy_periods)
        ))

        try:
            tz = ZoneInfo(timezone)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone}', falling back to UTC: {e}")
            tz = ZoneInfo("UTC")
            timezone = "UTC"

        # Parse busy periods
        busy_ranges = []
        for period in busy_periods:
            try:
                busy_start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))
                busy_ranges.append((busy_start, busy_end))
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid busy period: {period}, error: {e}")
                continue

        # Sort busy periods by start time
        busy_ranges.sort(key=lambda x: x[0])

        available_slots = []
        current_time = start_time.astimezone(tz)
        search_end = end_time.astimezone(tz)

        logger.info(
            "Generating time slots",
            extra={
                "start": current_time.isoformat(),
                "end": search_end.isoformat(),
                "timezone": timezone,
                "busy_periods": len(busy_ranges)
            }
        )

        # Iterate through each day in the search window
        while current_time < search_end and len(available_slots) < max_slots:
            # Set working hours for this day
            day_start = current_time.replace(
                hour=working_hours_start,
                minute=0,
                second=0,
                microsecond=0
            )
            day_end = current_time.replace(
                hour=working_hours_end,
                minute=0,
                second=0,
                microsecond=0
            )

            # Skip weekends (Saturday=5, Sunday=6)
            if current_time.weekday() >= 5:
                current_time = (current_time + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                continue

            # Start from the later of current_time or day_start
            slot_start = max(current_time, day_start)

            # Find free slots within this day's working hours
            while slot_start + timedelta(minutes=slot_duration_minutes) <= day_end:
                slot_end = slot_start + timedelta(minutes=slot_duration_minutes)

                # Check if this slot overlaps with any busy period
                is_available = True
                for busy_start, busy_end in busy_ranges:
                    # Convert to same timezone for comparison
                    busy_start_tz = busy_start.astimezone(tz)
                    busy_end_tz = busy_end.astimezone(tz)

                    # Check for overlap
                    if not (slot_end <= busy_start_tz or slot_start >= busy_end_tz):
                        is_available = False
                        break

                if is_available:
                    available_slots.append({
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat()
                    })
                    logger.debug(f"Found available slot: {slot_start.isoformat()} - {slot_end.isoformat()}")

                    if len(available_slots) >= max_slots:
                        break

                # Move to next potential slot (advance by 15 minutes for finer granularity)
                slot_start += timedelta(minutes=15)

            # Move to next day
            current_time = (current_time + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        logger.info(f"Generated {len(available_slots)} available slots")
        span.set_attribute("slots_generated", len(available_slots))
        span.set_status(Status(StatusCode.OK))

        return available_slots


async def get_freebusy(
    user_token: str,
    time_min: datetime,
    time_max: datetime,
    timezone: str = "UTC",
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Get free/busy information from Google Calendar.

    Args:
        user_token: Valid Google access token
        time_min: Start of the time range (timezone-aware)
        time_max: End of the time range (timezone-aware)
        timezone: Timezone for the query (default "UTC")
        calendar_id: Calendar ID to query (default "primary")

    Returns:
        dict containing free/busy data from Calendar API

    Raises:
        CalendarNotFoundError: If calendar doesn't exist
        CalendarServiceError: For other API errors
        HTTPException: For network errors

    Example response:
        {
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
    """
    with tracer.start_as_current_span("calendar.get_freebusy") as span:
        span.set_attributes(safe_span_attributes(
            calendar_id=calendar_id,
            timezone=timezone,
            operation="get_freebusy"
        ))

        # Format times as RFC3339
        time_min_str = time_min.isoformat()
        time_max_str = time_max.isoformat()

        logger.info(
            "Fetching Calendar free/busy data",
            extra={
                "calendar_id": calendar_id,
                "time_min": time_min_str,
                "time_max": time_max_str,
                "timezone": timezone
            }
        )

        # Prepare request payload
        payload = {
            "timeMin": time_min_str,
            "timeMax": time_max_str,
            "timeZone": timezone,
            "items": [{"id": calendar_id}]
        }

        calendar_api_url = "https://www.googleapis.com/calendar/v3/freeBusy"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    calendar_api_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json=payload,
                    timeout=15.0
                )

                # Handle specific error cases
                if response.status_code == 404:
                    logger.warning(
                        "Calendar not found",
                        extra={"calendar_id": calendar_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Calendar not found"))
                    raise CalendarNotFoundError(f"Calendar {calendar_id} not found")

                elif response.status_code == 401:
                    logger.warning(
                        "Calendar API returned 401 for free/busy query",
                        extra={"calendar_id": calendar_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Unauthorized"))
                    raise HTTPException(
                        status_code=401,
                        detail="Calendar authorization expired. Please reconnect your Google account."
                    )

                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "")
                    logger.warning(
                        "Calendar API returned 403 for free/busy query",
                        extra={"calendar_id": calendar_id, "error_message": error_message}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Forbidden"))
                    raise HTTPException(
                        status_code=403,
                        detail=f"Calendar access denied: {error_message or 'Permission denied'}"
                    )

                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Calendar API error fetching free/busy",
                        extra={
                            "calendar_id": calendar_id,
                            "status_code": response.status_code,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                    raise CalendarServiceError(
                        message=f"Failed to fetch calendar availability: {error_message}",
                        status_code=response.status_code,
                        error_code="freebusy_error"
                    )

                response.raise_for_status()
                freebusy_data = response.json()

                logger.info(
                    "Calendar free/busy data fetched successfully",
                    extra={
                        "calendar_id": calendar_id,
                        "calendars_count": len(freebusy_data.get("calendars", {}))
                    }
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("calendars_count", len(freebusy_data.get("calendars", {})))

                return freebusy_data

        except httpx.TimeoutException:
            logger.error("Calendar API timeout fetching free/busy", extra={"calendar_id": calendar_id})
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            raise HTTPException(
                status_code=504,
                detail="Calendar API request timeout. Please try again."
            )

        except httpx.RequestError as e:
            logger.error(
                "Calendar API network error fetching free/busy",
                extra={"calendar_id": calendar_id, "error": str(e)}
            )
            span.set_status(Status(StatusCode.ERROR, "Network error"))
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to Calendar API. Please try again later."
            )

        except (CalendarNotFoundError, CalendarServiceError, HTTPException):
            # Re-raise our custom exceptions (span status already set)
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error fetching Calendar free/busy",
                extra={"calendar_id": calendar_id, "error_type": type(e).__name__}
            )
            span.set_status(Status(StatusCode.ERROR, f"Unexpected: {type(e).__name__}"))
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again or contact support."
            )


async def get_availability_slots(
    user_token: str,
    window_days: int = 7,
    timezone: str = "UTC",
    slot_duration_minutes: int = 30,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
    max_slots: int = 3
) -> list[dict[str, str]]:
    """Get available meeting slots for the next N days.

    This is a convenience function that combines free/busy fetching with
    slot generation.

    Args:
        user_token: Valid Google access token
        window_days: Number of days to search ahead (default 7)
        timezone: Timezone for working hours (default "UTC")
        slot_duration_minutes: Duration of each slot (default 30)
        working_hours_start: Start of working hours in 24h format (default 9)
        working_hours_end: End of working hours in 24h format (default 17)
        max_slots: Maximum number of slots to return (default 3)

    Returns:
        List of available time slots with start and end times

    Raises:
        CalendarServiceError: For API errors
        HTTPException: For network or auth errors

    Example:
        >>> slots = await get_availability_slots(
        ...     user_token="ya29.xxx",
        ...     window_days=7,
        ...     timezone="America/New_York",
        ...     slot_duration_minutes=30
        ... )
        >>> print(slots)
        [
            {"start": "2025-01-15T09:00:00-05:00", "end": "2025-01-15T09:30:00-05:00"},
            {"start": "2025-01-15T10:00:00-05:00", "end": "2025-01-15T10:30:00-05:00"}
        ]
    """
    with tracer.start_as_current_span("calendar.get_availability_slots") as span:
        span.set_attributes(safe_span_attributes(
            window_days=window_days,
            timezone=timezone,
            slot_duration_minutes=slot_duration_minutes,
            max_slots=max_slots
        ))

        # Calculate time window
        try:
            tz = ZoneInfo(timezone)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone}', falling back to UTC: {e}")
            tz = ZoneInfo("UTC")
            timezone = "UTC"

        now = datetime.now(tz)
        time_min = now
        time_max = now + timedelta(days=window_days)

        logger.info(
            "Getting availability slots",
            extra={
                "window_days": window_days,
                "timezone": timezone,
                "time_min": time_min.isoformat(),
                "time_max": time_max.isoformat()
            }
        )

        # Fetch free/busy data
        freebusy_data = await get_freebusy(
            user_token=user_token,
            time_min=time_min,
            time_max=time_max,
            timezone=timezone
        )

        # Extract busy periods
        calendars = freebusy_data.get("calendars", {})
        primary_cal = calendars.get("primary", {})
        busy_periods = primary_cal.get("busy", [])

        logger.info(f"Found {len(busy_periods)} busy periods")

        # Generate available slots
        slots = generate_time_slots(
            busy_periods=busy_periods,
            start_time=time_min,
            end_time=time_max,
            timezone=timezone,
            slot_duration_minutes=slot_duration_minutes,
            working_hours_start=working_hours_start,
            working_hours_end=working_hours_end,
            max_slots=max_slots
        )

        span.set_attribute("slots_found", len(slots))
        span.set_status(Status(StatusCode.OK))

        return slots
