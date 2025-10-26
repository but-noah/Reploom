# Draft Review UI - Demo & Testing Guide

## What Was Built

This PR implements a complete Review UI for approving/rejecting/editing generated drafts:

### Backend (FastAPI)
1. **New Model**: `DraftReview` in `backend/app/models/draft_reviews.py`
   - Tracks review state, versions, violations, feedback
   - Indexed by user_id, status, thread_id

2. **New API Endpoints** in `backend/app/api/routes/reploom.py`:
   - `POST /api/agents/reploom/reviews` - Create review
   - `GET /api/agents/reploom/reviews` - List reviews (filterable)
   - `GET /api/agents/reploom/reviews/{id}` - Get single review
   - `POST /api/agents/reploom/reviews/{id}/approve` - Approve draft
   - `POST /api/agents/reploom/reviews/{id}/reject` - Reject draft
   - `POST /api/agents/reploom/reviews/{id}/request-edit` - Edit draft

### Frontend (React + Vite)
1. **New Components**:
   - `Badge` - Status/intent indicators
   - `Table` - Data table with proper styling

2. **New Pages**:
   - `/inbox` - Table view with filters (status, intent)
   - `/review/:id` - Detail view with diff, actions, policy violations

3. **API Client**: `frontend/src/lib/reviews.ts`
   - Type-safe functions for all review endpoints

4. **Features**:
   - Filter by status (pending/approved/rejected/editing)
   - Filter by intent (support/cs/exec/other)
   - Inline editing with version tracking
   - Policy violation warnings (blocks approval)
   - Approve/Reject with feedback
   - Toast notifications
   - Responsive design

## Quick Start

### 1. Start Backend
```bash
cd backend
# Ensure database is running (docker-compose up -d postgres)
python -m uvicorn app.main:app --reload
```

### 2. Create Database Table
The `draft_reviews` table will be auto-created on first run due to SQLModel.

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. Test the Flow

#### Option A: Using the API
```bash
# 1. Generate a draft
curl -X POST http://localhost:8000/api/agents/reploom/run-draft \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=YOUR_SESSION" \
  -d '{
    "message_excerpt": "Customer needs password reset help",
    "workspace_id": "demo-workspace"
  }'

# 2. Create a review entry
curl -X POST http://localhost:8000/api/agents/reploom/reviews \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=YOUR_SESSION" \
  -d '{
    "thread_id": "demo-thread-001",
    "draft_html": "<p>Dear valued customer,</p><p>To reset your password, please visit our account recovery page...</p>",
    "original_message_summary": "Customer needs password reset help",
    "original_message_excerpt": "Hi, I forgot my password and need help resetting it.",
    "intent": "support",
    "confidence": 0.95,
    "violations": [],
    "workspace_id": "demo-workspace"
  }'

# 3. View in browser
# Navigate to http://localhost:5173/inbox
```

#### Option B: Manual Database Insert
```sql
INSERT INTO draft_reviews (
  id, user_id, user_email, thread_id,
  original_message_summary, draft_html,
  intent, confidence, violations, status,
  created_at, updated_at
) VALUES (
  gen_random_uuid(),
  'auth0|demo-user-123',
  'demo@example.com',
  'thread-demo-001',
  'Customer needs password reset help',
  '<p>Dear valued customer,</p><p>To reset your password, please visit our account recovery page at https://example.com/reset-password and follow the instructions.</p><p>Best regards,<br>Support Team</p>',
  'support',
  0.95,
  '[]'::jsonb,
  'pending',
  NOW(),
  NOW()
);
```

## Testing Checklist

### Inbox Page (/inbox)
- [ ] Page loads without errors
- [ ] Table displays reviews correctly
- [ ] Thread column shows message summary
- [ ] Intent badge displays correct color
- [ ] Confidence shows as percentage
- [ ] Status badge displays correct variant
- [ ] Violations count is accurate
- [ ] Updated timestamp is formatted correctly
- [ ] Filter by Status works (all, pending, approved, rejected, editing)
- [ ] Filter by Intent works (all, support, cs, exec, other)
- [ ] Refresh button updates data
- [ ] "Review" button navigates to detail page
- [ ] Empty state shows when no reviews exist

### Review Detail Page (/review/:id)
- [ ] Page loads with correct review data
- [ ] "Back to Inbox" button works
- [ ] Thread ID is displayed
- [ ] Version and status badges are correct
- [ ] Intent, Confidence, Violations cards show correct data
- [ ] Original message excerpt is displayed
- [ ] Draft HTML is rendered correctly
- [ ] Policy violations alert appears (if violations exist)
- [ ] Edit button appears for pending drafts
- [ ] Approve button is disabled when violations exist
- [ ] Approve button works (status → approved)
- [ ] Reject button opens dialog
- [ ] Reject dialog captures feedback
- [ ] Reject flow works (status → rejected)
- [ ] Edit mode shows textarea for HTML
- [ ] Edit mode shows textarea for notes
- [ ] Save Changes increments version
- [ ] Save Changes updates status to "editing"
- [ ] Cancel button exits edit mode
- [ ] Toast notifications appear for all actions
- [ ] Success/rejection banners display correctly

### API Endpoints
Test all endpoints with curl or Postman:

```bash
# List all reviews
curl -X GET "http://localhost:8000/api/agents/reploom/reviews" \
  -H "Cookie: auth0_session=YOUR_SESSION"

# List pending reviews
curl -X GET "http://localhost:8000/api/agents/reploom/reviews?status=pending" \
  -H "Cookie: auth0_session=YOUR_SESSION"

# Get specific review
curl -X GET "http://localhost:8000/api/agents/reploom/reviews/{review_id}" \
  -H "Cookie: auth0_session=YOUR_SESSION"

# Approve review
curl -X POST "http://localhost:8000/api/agents/reploom/reviews/{review_id}/approve" \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=YOUR_SESSION" \
  -d '{"feedback": "Looks great!"}'

# Reject review
curl -X POST "http://localhost:8000/api/agents/reploom/reviews/{review_id}/reject" \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=YOUR_SESSION" \
  -d '{"feedback": "Tone is too casual"}'

# Request edit
curl -X POST "http://localhost:8000/api/agents/reploom/reviews/{review_id}/request-edit" \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=YOUR_SESSION" \
  -d '{
    "draft_html": "<p>Updated draft content...</p>",
    "edit_notes": "Fixed grammar and tone"
  }'
```

## Screenshots / GIF

To create screenshots:
1. Navigate to http://localhost:5173/inbox
2. Take screenshot of inbox table
3. Click "Review" on a draft
4. Take screenshot of review detail page
5. Click "Edit", make changes
6. Take screenshot of edit mode
7. Click "Approve"
8. Take screenshot of success state

Optional: Use a tool like Kap (macOS), Peek (Linux), or ScreenToGif (Windows) to create an animated GIF of the full flow.

## Known Limitations

1. **No Send Action**: Approve only marks as approved, doesn't send email (as per requirements)
2. **Policy Guard**: Edit flow clears violations (simplified); full re-check not implemented
3. **Diff View**: Shows side-by-side, but not a true text-level diff (kept simple)
4. **Polling**: No real-time updates; uses manual refresh (SSE/streaming not implemented per constraints)

## Next Steps

1. Implement actual Gmail send after approval
2. Add real-time updates with SSE or WebSocket
3. Implement proper diff highlighting library (e.g., diff-match-patch)
4. Add bulk actions (approve multiple, etc.)
5. Add search functionality
6. Add pagination for large review lists
7. Implement proper policy guard re-check on edit
8. Add user permissions/roles for team review

## Files Changed

### Backend
- `backend/app/models/draft_reviews.py` (new)
- `backend/app/models/models.py` (updated)
- `backend/app/api/routes/reploom.py` (updated)

### Frontend
- `frontend/src/lib/reviews.ts` (new)
- `frontend/src/components/ui/badge.tsx` (new)
- `frontend/src/components/ui/table.tsx` (new)
- `frontend/src/pages/InboxPage.tsx` (new)
- `frontend/src/pages/ReviewPage.tsx` (new)
- `frontend/src/components/layout.tsx` (updated)

### Tests & Docs
- `frontend/src/lib/__tests__/reviews.test.ts` (new)
- `frontend/TESTING.md` (new)
- `DEMO.md` (new)

Total: 13 files (8 new, 3 updated, 2 docs)
