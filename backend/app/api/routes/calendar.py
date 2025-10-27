"""Google Calendar API integration routes.

This module provides endpoints for interacting with Google Calendar via Auth0 Token Vault.
Access tokens are obtained securely without storing provider refresh tokens.
"""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import auth_client
from app.core.config import settings
from app.auth.token_exchange import (
    get_google_access_token,
    TokenExchangeError,
    InsufficientScopeError,
    InvalidGrantError,
)
from app.integrations.calendar_service import (
    get_availability_slots,
    CalendarServiceError,
    CalendarNotFoundError,
)

logger = logging.getLogger(__name__)

calendar_router = APIRouter(prefix="/me/calendar", tags=["calendar"])


class TimeSlot(BaseModel):
    """Time slot model."""
    start: str
    end: str


class AvailabilityResponse(BaseModel):
    """Response model for calendar availability endpoint."""
    slots: list[TimeSlot]
    timezone: str
    window_days: int
    slot_duration_minutes: int


@calendar_router.get("/availability", response_model=AvailabilityResponse)
async def get_calendar_availability(
    auth_session=Depends(auth_client.require_session),
    window: str = Query("7d", description="Time window (e.g., '7d' for 7 days)"),
    tz: str = Query("UTC", description="Timezone (e.g., 'America/New_York')"),
    slot_duration: int = Query(30, description="Slot duration in minutes (30 or 45)"),
    working_hours_start: int = Query(9, description="Start of working hours (0-23)"),
    working_hours_end: int = Query(17, description="End of working hours (0-23)"),
    max_slots: int = Query(3, description="Maximum number of slots to return (1-10)")
) -> AvailabilityResponse:
    """Get available meeting slots from user's Google Calendar.

    This endpoint returns 2-3 available time slots within the specified time window,
    respecting working hours and existing calendar events. It uses the Calendar API's
    free/busy endpoint for read-only access.

    **Read-only operation** - No calendar invites are created or sent.

    If the user hasn't granted calendar permissions, this endpoint will return a 403
    error, allowing the calling code to gracefully handle the absence of calendar data.

    Required setup:
    - User must have connected Google Calendar via Auth0 Social Connection
    - Required scope: calendar.readonly
    - Auth0 Token Vault must be configured

    Args:
        auth_session: Authenticated user session (injected)
        window: Time window to search (format: "Nd" where N is number of days)
        tz: Timezone for working hours calculation (IANA timezone name)
        slot_duration: Duration of each slot in minutes (30 or 45 recommended)
        working_hours_start: Start of working hours in 24h format (0-23)
        working_hours_end: End of working hours in 24h format (0-23)
        max_slots: Maximum number of slots to return (1-10)

    Returns:
        AvailabilityResponse: Contains available time slots and metadata

    Raises:
        HTTPException 400: Invalid parameters
        HTTPException 401: Invalid or expired authorization
        HTTPException 403: Insufficient calendar permissions (can be handled gracefully)
        HTTPException 404: Calendar not found
        HTTPException 500: Configuration or unexpected errors
        HTTPException 503: Calendar API unavailable
        HTTPException 504: Request timeout

    Example request:
        GET /api/me/calendar/availability?window=7d&tz=America/New_York&slot_duration=30

    Example response:
        {
            "slots": [
                {
                    "start": "2025-01-15T09:00:00-05:00",
                    "end": "2025-01-15T09:30:00-05:00"
                },
                {
                    "start": "2025-01-15T14:00:00-05:00",
                    "end": "2025-01-15T14:30:00-05:00"
                }
            ],
            "timezone": "America/New_York",
            "window_days": 7,
            "slot_duration_minutes": 30
        }
    """
    user = auth_session.get("user")
    user_sub = user.get("sub")
    user_email = user.get("email", "unknown")

    logger.info(
        "Calendar availability request initiated",
        extra={
            "user_sub": user_sub[:8] + "..." if user_sub and len(user_sub) > 8 else "[redacted]",
            "user_email": user_email if user_email != "unknown" else "[redacted]",
            "window": window,
            "timezone": tz
        }
    )

    # Parse window parameter (e.g., "7d" -> 7 days)
    try:
        if not window.endswith("d"):
            raise ValueError("Window must end with 'd' (e.g., '7d')")
        window_days = int(window[:-1])
        if window_days < 1 or window_days > 30:
            raise ValueError("Window must be between 1 and 30 days")
    except ValueError as e:
        logger.warning(
            "Invalid window parameter",
            extra={"window": window, "error": str(e)}
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window parameter: {e}. Use format like '7d' for 7 days (1-30 days allowed)."
        )

    # Validate slot_duration
    if slot_duration not in [15, 30, 45, 60]:
        logger.warning(
            "Invalid slot_duration parameter",
            extra={"slot_duration": slot_duration}
        )
        raise HTTPException(
            status_code=400,
            detail="slot_duration must be 15, 30, 45, or 60 minutes"
        )

    # Validate working hours
    if not (0 <= working_hours_start < 24 and 0 <= working_hours_end <= 24):
        raise HTTPException(
            status_code=400,
            detail="working_hours_start and working_hours_end must be between 0 and 23"
        )

    if working_hours_start >= working_hours_end:
        raise HTTPException(
            status_code=400,
            detail="working_hours_start must be less than working_hours_end"
        )

    # Validate max_slots
    if not (1 <= max_slots <= 10):
        raise HTTPException(
            status_code=400,
            detail="max_slots must be between 1 and 10"
        )

    try:
        # Exchange Auth0 session for Google access token with calendar.readonly scope
        access_token = await get_google_access_token(
            user_sub=user_sub,
            scopes=settings.CALENDAR_SCOPES_LIST
        )

        # Get availability slots
        slots = await get_availability_slots(
            user_token=access_token,
            window_days=window_days,
            timezone=tz,
            slot_duration_minutes=slot_duration,
            working_hours_start=working_hours_start,
            working_hours_end=working_hours_end,
            max_slots=max_slots
        )

        logger.info(
            "Calendar availability retrieved successfully",
            extra={
                "user_sub": user_sub[:8] + "...",
                "slots_count": len(slots),
                "timezone": tz
            }
        )

        # Return structured response
        return AvailabilityResponse(
            slots=[TimeSlot(**slot) for slot in slots],
            timezone=tz,
            window_days=window_days,
            slot_duration_minutes=slot_duration
        )

    except InsufficientScopeError as e:
        logger.warning(
            "Insufficient calendar scope",
            extra={"user_sub": user_sub[:8] + "...", "error": e.message}
        )
        # Return 403 so calling code can gracefully handle absence of calendar permissions
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except InvalidGrantError as e:
        logger.warning(
            "Invalid calendar grant",
            extra={"user_sub": user_sub[:8] + "...", "error": e.message}
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except TokenExchangeError as e:
        logger.error(
            "Token exchange error for calendar",
            extra={
                "user_sub": user_sub[:8] + "...",
                "error_code": e.error_code,
                "error": e.message
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except CalendarNotFoundError as e:
        logger.warning(
            "Calendar not found",
            extra={"user_sub": user_sub[:8] + "...", "error": e.message}
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except CalendarServiceError as e:
        logger.error(
            "Calendar service error",
            extra={
                "user_sub": user_sub[:8] + "...",
                "error_code": e.error_code,
                "error": e.message
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise

    except Exception as e:
        logger.exception(
            "Unexpected error in calendar availability endpoint",
            extra={
                "user_sub": user_sub[:8] + "...",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again or contact support."
        )
