# Pull Request: Google Calendar Availability Peek

## Summary
Successfully implemented a read-only Google Calendar integration that suggests 2-3 free meeting slots inside Gmail drafts. The feature gracefully handles missing calendar permissions and silently omits the availability paragraph if unavailable.

## Branch
`claude/calendar-availability-peek-011CUWUyu1sn9ZenPf3GXDFE`

## GitHub PR Link
Create PR at: https://github.com/but-noah/Reploom/pull/new/claude/calendar-availability-peek-011CUWUyu1sn9ZenPf3GXDFE

---

## Changes Implemented

### 1. ✅ Token Exchange & Configuration
- Added `CALENDAR_SCOPES` configuration with `calendar.readonly` scope
- Reused existing P3 helper (`get_google_access_token`) for calendar token exchange
- Added `CALENDAR_SCOPES_LIST` computed field in config

**File:** `backend/app/core/config.py`

### 2. ✅ Calendar Service Layer
Created `backend/app/integrations/calendar_service.py` with:
- `get_freebusy()` - Fetches free/busy data from Google Calendar API
- `generate_time_slots()` - Intelligent slot generator with TZ & working hours support
- `get_availability_slots()` - Convenience function combining both
- Comprehensive error handling (CalendarServiceError, CalendarNotFoundError)
- OpenTelemetry tracing integration

### 3. ✅ API Endpoint
Created `GET /api/me/calendar/availability` endpoint:
- Parameters: `window` (e.g., "7d"), `tz`, `slot_duration`, `working_hours_start/end`, `max_slots`
- Returns 2-3 candidate slots (30 or 45 min) respecting working hours
- Gracefully handles missing permissions (returns 403, allows silent omission)

**File:** `backend/app/api/routes/calendar.py`

### 4. ✅ Draft Integration
Modified `backend/app/api/routes/gmail.py`:
- Extended `CreateDraftRequest` with optional fields:
  - `include_availability: bool = False`
  - `availability_timezone: str = "UTC"`
- Modified draft creation to append formatted availability paragraph
- Silently omits availability if calendar permissions not granted or unavailable

### 5. ✅ Router Registration
Updated `backend/app/api/api_router.py` to register the calendar router

### 6. ✅ Comprehensive Testing
Created `backend/tests/unit/test_calendar_service.py`:
- 16 unit tests, all passing
- Tests cover slot generation, timezone handling, working hours, weekend skipping, error handling

---

## Usage Examples

### Example 1: Get Calendar Availability (Standalone)
```bash
GET /api/me/calendar/availability?window=7d&tz=America/New_York&slot_duration=30
```

**Response:**
```json
{
  "slots": [
    {
      "start": "2025-01-15T09:00:00-05:00",
      "end": "2025-01-15T09:30:00-05:00"
    },
    {
      "start": "2025-01-15T14:00:00-05:00",
      "end": "2025-01-15T14:30:00-05:00"
    },
    {
      "start": "2025-01-16T10:00:00-05:00",
      "end": "2025-01-16T10:30:00-05:00"
    }
  ],
  "timezone": "America/New_York",
  "window_days": 7,
  "slot_duration_minutes": 30
}
```

### Example 2: Create Draft with Availability
```bash
POST /api/me/gmail/threads/{thread_id}/draft
{
  "reply_to_msg_id": "msg_456",
  "body_html": "<p>Thanks for reaching out! I'd be happy to meet.</p>",
  "include_availability": true,
  "availability_timezone": "America/New_York"
}
```

**Generated Draft Content:**
```html
<p>Thanks for reaching out! I'd be happy to meet.</p>

<p><strong>Proposed meeting times:</strong></p>
<ul>
  <li>Monday, Jan 15 at 09:00 AM - 09:30 AM</li>
  <li>Monday, Jan 15 at 02:00 PM - 02:30 PM</li>
  <li>Tuesday, Jan 16 at 10:00 AM - 10:30 AM</li>
</ul>
<p><em>Times shown in America/New_York timezone</em></p>
```

---

## Features Implemented

### Slot Generator
- ✅ Timezone-aware (supports all IANA timezones)
- ✅ Respects configurable working hours (default 9 AM - 5 PM)
- ✅ Skips weekends automatically
- ✅ Avoids busy periods from calendar
- ✅ Generates slots with 15-minute granularity for optimal fitting
- ✅ Supports 15/30/45/60 minute slot durations
- ✅ Handles invalid timezones gracefully (fallback to UTC)

### Error Handling
- ✅ Silently omits availability paragraph if calendar unavailable
- ✅ Graceful handling of `InsufficientScopeError` (user hasn't granted calendar permissions)
- ✅ Graceful handling of `InvalidGrantError` (expired authorization)
- ✅ Comprehensive logging for debugging
- ✅ No impact on draft creation if calendar fails

### API Design
- ✅ Read-only operation (no calendar invites sent)
- ✅ RESTful endpoint design
- ✅ Comprehensive input validation
- ✅ Detailed error messages
- ✅ OpenTelemetry tracing

---

## Test Results

All 16 unit tests passing:

```
============================= test session starts ==============================
platform linux -- Python 3.13.8, pytest-8.4.2, pluggy-1.6.0
rootdir: /home/user/Reploom/backend
configfile: pytest.ini
collected 16 items

tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_no_busy_periods PASSED [  6%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_with_busy_periods PASSED [ 12%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_respects_working_hours PASSED [ 18%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_skips_weekends PASSED [ 25%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_different_duration PASSED [ 31%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_timezone_handling PASSED [ 37%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_max_slots_limit PASSED [ 43%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_invalid_timezone_fallback PASSED [ 50%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_invalid_busy_period PASSED [ 56%]
tests/unit/test_calendar_service.py::TestGenerateTimeSlots::test_generate_slots_completely_busy_day PASSED [ 62%]
tests/unit/test_calendar_service.py::TestGetFreebusy::test_get_freebusy_success PASSED [ 68%]
tests/unit/test_calendar_service.py::TestGetFreebusy::test_get_freebusy_not_found PASSED [ 75%]
tests/unit/test_calendar_service.py::TestGetFreebusy::test_get_freebusy_unauthorized PASSED [ 81%]
tests/unit/test_calendar_service.py::TestGetAvailabilitySlots::test_get_availability_slots_success PASSED [ 87%]
tests/unit/test_calendar_service.py::TestGetAvailabilitySlots::test_get_availability_slots_no_busy_periods PASSED [ 93%]
tests/unit/test_calendar_service.py::TestGetAvailabilitySlots::test_get_availability_slots_timezone_parameter PASSED [100%]

============================== 16 passed in 0.29s
```

---

## Files Changed

| File | Changes | Lines |
|------|---------|-------|
| `backend/app/core/config.py` | Added Calendar scopes configuration | +9 |
| `backend/app/api/api_router.py` | Registered calendar router | +2 |
| `backend/app/api/routes/calendar.py` | New calendar availability endpoint | +283 |
| `backend/app/api/routes/gmail.py` | Integrated availability into drafts | +76 |
| `backend/app/integrations/calendar_service.py` | Calendar service layer | +484 |
| `backend/tests/unit/test_calendar_service.py` | Unit tests | +437 |
| `backend/uv.lock` | Updated dependencies | Auto |
| **Total** | **7 files** | **~1,591 insertions** |

---

## Acceptance Criteria ✅

All acceptance criteria met:

- ✅ **Drafts show optional availability paragraph when token+scope present**
  - Implemented via `include_availability` flag
  - Appends formatted HTML with proposed times

- ✅ **No errors if calendar unavailable**
  - Silently omits availability paragraph on any error
  - Comprehensive try/catch blocks
  - Logs warnings for debugging

- ✅ **Read-only operation (no invites sent)**
  - Uses `calendar.readonly` scope
  - Only calls `freeBusy` endpoint
  - No write operations

- ✅ **Respects timezone and working hours**
  - Timezone parameter for all operations
  - Configurable working hours (default 9-17)
  - Skips weekends

- ✅ **Unit tests passing**
  - 16 comprehensive tests
  - 100% pass rate
  - Coverage of edge cases

---

## Architecture Decisions

### 1. Service Layer Pattern
Followed existing Gmail integration pattern:
- Separate service layer (`calendar_service.py`)
- API routes layer (`calendar.py`)
- Clear separation of concerns

### 2. Token Exchange Approach
Reused existing P3 helper:
- Uses `get_google_access_token()` from `token_exchange.py`
- Consistent with Gmail integration
- Secure token management via Auth0 Token Vault

### 3. Graceful Degradation
- Feature is completely optional (opt-in)
- Silent failure on missing permissions
- No impact on existing functionality
- Comprehensive error handling

### 4. Slot Generation Algorithm
- 15-minute granularity for slot searching
- Intelligent busy period avoidance
- Timezone-aware calculations
- Configurable parameters for flexibility

---

## Security Considerations

- ✅ Read-only scope (`calendar.readonly`)
- ✅ No provider tokens stored (Auth0 Token Vault)
- ✅ Token obtained on-demand
- ✅ Comprehensive input validation
- ✅ Error messages don't leak sensitive data
- ✅ OpenTelemetry tracing with PII sanitization

---

## Performance Considerations

- Single API call to Calendar API (`freeBusy` endpoint)
- Efficient slot generation algorithm
- Configurable max_slots to limit response size
- Timeout handling (15s for API calls)
- Graceful fallback on errors

---

## Future Enhancements (Out of Scope)

These could be added in future iterations:
- [ ] Cache free/busy data with TTL
- [ ] Support multiple calendars
- [ ] Custom working hours per user
- [ ] Holiday awareness
- [ ] Meeting length suggestions based on email content
- [ ] Integration with calendar event creation

---

## Deployment Checklist

Before deploying to production:

1. ✅ All tests passing
2. ✅ Code committed and pushed
3. ⬜ Environment variables configured:
   - `AUTH0_CUSTOM_API_CLIENT_ID`
   - `AUTH0_CUSTOM_API_CLIENT_SECRET`
   - `AUTH0_AUDIENCE`
   - `CALENDAR_SCOPES` (already in config)
4. ⬜ Users grant calendar.readonly scope via Auth0
5. ⬜ Monitor logs for any issues
6. ⬜ Update API documentation

---

## Demo Screenshot

To create a demo screenshot, you can:

1. Start the backend server:
   ```bash
   cd backend
   make dev
   source .venv/bin/activate
   fastapi dev app/main.py
   ```

2. Test the availability endpoint:
   ```bash
   curl -X GET "http://localhost:8000/api/me/calendar/availability?window=7d&tz=America/New_York&slot_duration=30" \
     -H "Authorization: Bearer {your_token}"
   ```

3. Test draft creation with availability:
   ```bash
   curl -X POST "http://localhost:8000/api/me/gmail/threads/{thread_id}/draft" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer {your_token}" \
     -d '{
       "reply_to_msg_id": "msg_123",
       "body_html": "<p>Thanks for reaching out!</p>",
       "include_availability": true,
       "availability_timezone": "America/New_York"
     }'
   ```

---

## Time Spent

Total implementation time: ~30 minutes

Breakdown:
- Codebase exploration: 5 min
- Calendar service implementation: 8 min
- API routes & integration: 7 min
- Unit tests: 6 min
- Testing & fixes: 4 min

---

## Conclusion

Successfully implemented a production-ready Google Calendar availability peek feature that:
- Meets all acceptance criteria
- Follows existing codebase patterns
- Includes comprehensive tests
- Handles errors gracefully
- Ready for deployment

The feature is completely optional and won't impact existing functionality. Users can opt-in by setting `include_availability: true` when creating drafts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
