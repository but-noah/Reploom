# Analytics Feature Documentation

## Overview

This feature adds minimal analytics capabilities to track key metrics for draft review performance and email processing patterns.

## Implementation Details

### Backend Components

#### 1. Analytics API Endpoint
**File:** `backend/app/api/routes/analytics.py`

**Endpoint:** `GET /api/analytics/summary`

**Query Parameters:**
- `window` (required): Time window for analytics (`7d` or `30d`)
- `workspace_id` (optional): Filter by workspace ID
- `sla_threshold_seconds` (optional): SLA threshold in seconds (default: 300 = 5 minutes)

**Response Structure:**
```json
{
  "window": "7d",
  "workspace_id": "ws-123",
  "period_start": "2025-10-19T00:00:00Z",
  "period_end": "2025-10-26T00:00:00Z",
  "metrics": {
    "intents_count": { "support": 45, "cs": 30, "exec": 15, "other": 10 },
    "review_rate": {
      "total": 100,
      "approved": 60,
      "rejected": 20,
      "editing": 10,
      "pending": 10,
      "approved_rate": 60.0,
      "rejected_rate": 20.0,
      "editing_rate": 10.0,
      "pending_rate": 10.0
    },
    "frt": {
      "avg_seconds": 180.5,
      "median_seconds": 150.0,
      "min_seconds": 30.0,
      "max_seconds": 450.0,
      "sla_threshold_seconds": 300,
      "sla_met_count": 75,
      "sla_met_percentage": 83.33,
      "total_with_frt": 90
    }
  },
  "trend": {
    "intents_count_previous": {...},
    "review_rate_previous": {...},
    "frt_previous": {...}
  }
}
```

#### 2. Metrics Calculation
**Function:** `calculate_metrics(reviews, sla_threshold_seconds)`

**Metrics Calculated:**

1. **Intents Count:** Distribution of draft entries by detected intent (support, cs, exec, other, unknown)
2. **Review Rate:** Breakdown of review statuses
   - Total count
   - Counts by status (approved, rejected, editing, pending)
   - Percentage rates for each status
3. **First Response Time (FRT):**
   - Average FRT in seconds
   - Median FRT
   - Min/Max FRT
   - SLA compliance (count and percentage of reviews meeting threshold)
   - Total reviews with FRT data

**FRT Calculation Logic:**
- Uses `reviewed_at` timestamp when available
- Falls back to `updated_at` if `reviewed_at` is null
- Only includes non-pending reviews (approved, rejected, editing)
- FRT = time from `created_at` to first review action

#### 3. Tests
**File:** `backend/tests/unit/test_analytics.py`

**Test Coverage:**
- Window parsing (7d, 30d, invalid)
- Empty data handling
- Intent counting (including null values)
- Review rate calculations across all statuses
- FRT calculations with various scenarios
- SLA threshold compliance
- Custom SLA thresholds
- Comprehensive metrics with realistic data

### Frontend Components

#### 1. Analytics Page
**File:** `frontend/src/pages/AnalyticsPage.tsx`

**Features:**
- Time window selector (7d / 30d)
- Three metric cards:
  1. **Entries by Intent** - Distribution chart with trend indicators
  2. **Human Review Rate** - Status breakdown with counts and percentages
  3. **First Response Time & SLA** - FRT metrics and SLA compliance gauge

**Visual Elements:**
- Color-coded intent bars (support: blue, cs: green, exec: purple, other: gray)
- Status icons (CheckCircle2, XCircle, Edit3, AlertCircle)
- Trend indicators (TrendingUp, TrendingDown) showing percentage changes vs previous period
- SLA compliance bar with color coding:
  - Green: ≥80%
  - Yellow: 60-79%
  - Red: <60%

#### 2. API Client
**File:** `frontend/src/lib/analytics.ts`

**Functions:**
- `getAnalyticsSummary(params)`: Fetch analytics data
- `formatDuration(seconds)`: Convert seconds to human-readable format (e.g., "2m 30s")
- `calculatePercentageChange(current, previous)`: Calculate trend percentage
- `formatPercentage(value, decimals)`: Format percentage with decimal places

**TypeScript Interfaces:**
- `IntentsCount`
- `ReviewRate`
- `FRTMetrics`
- `AnalyticsMetrics`
- `AnalyticsTrend`
- `AnalyticsSummary`
- `GetAnalyticsSummaryParams`

#### 3. Tests
**File:** `frontend/src/lib/__tests__/analytics.test.ts`

**Test Coverage:**
- API function calls with default and custom parameters
- Error handling
- Duration formatting (seconds, minutes with/without seconds)
- Percentage change calculations (positive, negative, zero cases)
- Percentage formatting with various decimal places

#### 4. UI Components
**File:** `frontend/src/components/ui/skeleton.tsx`

Added loading skeleton component for better UX during data fetching.

### Database Schema

The analytics feature uses the existing `DraftReview` model from `backend/app/models/draft_reviews.py`:

**Relevant Fields:**
- `intent`: Detected intent classification
- `status`: Review status (pending, approved, rejected, editing)
- `created_at`: Draft creation timestamp
- `updated_at`: Last update timestamp
- `reviewed_at`: First review action timestamp
- `workspace_id`: Workspace association

No schema changes were required.

## Usage

### Backend

```bash
# Run analytics endpoint
curl "http://localhost:8000/api/analytics/summary?window=7d&sla_threshold_seconds=300"

# With workspace filter
curl "http://localhost:8000/api/analytics/summary?window=30d&workspace_id=ws-123"
```

### Frontend

Navigate to `/analytics` in the application to view the analytics dashboard.

Use the time window selector to switch between 7-day and 30-day views.

### Running Tests

**Backend:**
```bash
cd backend
pytest tests/unit/test_analytics.py -v
```

**Frontend:**
```bash
cd frontend
vitest src/lib/__tests__/analytics.test.ts
```

## Design Decisions

1. **Minimal Schema:** No new tables or migrations required; uses existing DraftReview model
2. **Server-side Aggregation:** All metrics calculated on backend for consistency and performance
3. **Trend Comparison:** Automatically compares current period to previous period of same length
4. **Configurable SLA:** SLA threshold is configurable per request (default 5 minutes)
5. **Simple UI:** Three focused cards without heavy charting libraries
6. **Type Safety:** Full TypeScript typing for all frontend data structures

## Performance Considerations

- Queries filter by `created_at` timestamp with appropriate indexing
- Aggregations performed in-memory after fetching filtered dataset
- Results cached on frontend via TanStack React Query
- No real-time updates; data refreshes on page load or window change

## Future Enhancements

Potential improvements for future iterations:
- Charts/graphs for time series data
- Export to CSV/JSON
- Custom date range selection
- Per-user or per-team breakdowns
- Real-time updates via WebSocket
- Additional metrics (response quality scores, edit counts, etc.)
- Dashboard widgets for other pages

## Sample Response

See `analytics-sample-response.json` for a complete example API response.

## Files Changed

### Backend
- ✅ `backend/app/api/routes/analytics.py` (new)
- ✅ `backend/app/api/api_router.py` (modified)
- ✅ `backend/tests/unit/test_analytics.py` (new)

### Frontend
- ✅ `frontend/src/pages/AnalyticsPage.tsx` (new)
- ✅ `frontend/src/lib/analytics.ts` (new)
- ✅ `frontend/src/lib/__tests__/analytics.test.ts` (new)
- ✅ `frontend/src/components/ui/skeleton.tsx` (new)
- ✅ `frontend/src/components/layout.tsx` (modified)

### Documentation
- ✅ `ANALYTICS_FEATURE.md` (new)
- ✅ `analytics-sample-response.json` (new)

## Acceptance Criteria

✅ **Backend metrics:** Aggregations over 7/30 days for intents_count, review_rate, FRT/SLA
✅ **API endpoint:** GET /analytics/summary with window and workspace_id filters
✅ **Frontend:** /analytics page with 3 cards showing metrics
✅ **Tests:** Unit tests for aggregation calculations and edge cases
✅ **Endpoint correctness:** Returns proper aggregates structure
✅ **UI rendering:** Displays metrics without errors, includes trend indicators

## Time Spent

Estimated implementation time: ~30 minutes
- Backend API + metrics: ~10 min
- Frontend page + API client: ~10 min
- Tests: ~5 min
- Documentation: ~5 min
