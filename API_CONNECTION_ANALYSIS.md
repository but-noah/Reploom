# API Connection Analysis Report - Reploom Frontend/Backend

## Executive Summary
**Status: CRITICAL ISSUES FOUND**
- Total Backend Endpoints: 26
- Total Frontend API Clients: 10
- Connection Status: 76% properly connected
- Critical Issues: 2 (Path mismatches)

---

## 1. BACKEND API ENDPOINTS

### 1.1 Calendar Routes
| Path | Method | Prefix | Full Path | Status |
|------|--------|--------|-----------|--------|
| `/me/calendar/availability` | GET | `/api` | `/api/me/calendar/availability` | ⚠️ No Frontend Client |

### 1.2 Analytics Routes
| Path | Method | Prefix | Full Path | Frontend Call | Status |
|------|--------|--------|-----------|---------------|--------|
| `/analytics/summary` | GET | `/api` | `/api/analytics/summary` | `/analytics/summary` | ❌ PATH MISMATCH |

### 1.3 Gmail Routes
| Path | Method | Prefix | Full Path | Status |
|------|--------|--------|-----------|--------|
| `/me/gmail/labels` | GET | `/api` | `/api/me/gmail/labels` | ⚠️ No Frontend Client |
| `/me/gmail/threads/{thread_id}/draft` | POST | `/api` | `/api/me/gmail/threads/{thread_id}/draft` | ⚠️ No Frontend Client |

### 1.4 Documents Routes
| Path | Method | Prefix | Full Path | Frontend Call | Status |
|------|--------|--------|-----------|---------------|--------|
| `/documents` | GET | `/api` | `/api/documents` | `/api/documents` | ✅ Connected |
| `/documents/upload` | POST | `/api` | `/api/documents/upload` | `/api/documents/upload` | ✅ Connected |
| `/documents/{document_id}/content` | GET | `/api` | `/api/documents/{document_id}/content` | `/api/documents/{documentId}/content` | ✅ Connected |
| `/documents/{document_id}/share` | POST | `/api` | `/api/documents/{document_id}/share` | `/api/documents/{documentId}/share` | ✅ Connected |
| `/documents/{document_id}` | DELETE | `/api` | `/api/documents/{document_id}` | `/api/documents/{documentId}` | ✅ Connected |

### 1.5 Chat/Agent Proxy Routes
| Path | Method | Prefix | Full Path | Status |
|------|--------|--------|-----------|--------|
| `/agent/{full_path:path}` | GET/POST/DELETE/PATCH/PUT | `/api` | `/api/agent/{full_path}` | ⚠️ Proxy Route |

### 1.6 Knowledge Base Routes
| Path | Method | Prefix | Full Path | Status |
|------|--------|--------|-----------|--------|
| `/kb/upload` | POST | `/api` | `/api/kb/upload` | ⚠️ No Frontend Client |
| `/kb/search` | GET | `/api` | `/api/kb/search` | ⚠️ No Frontend Client |

### 1.7 Reploom (Draft Generation & Review) Routes
| Path | Method | Prefix | Full Path | Frontend Call | Status |
|------|--------|--------|-----------|---------------|--------|
| `/agents/reploom/run-draft` | POST | `/api` | `/api/agents/reploom/run-draft` | `/api/agents/reploom/run-draft` | ✅ Connected |
| `/agents/reploom/runs/{thread_id}` | GET | `/api` | `/api/agents/reploom/runs/{thread_id}` | Not Called | ⚠️ Unused |
| `/agents/reploom/reviews` | POST | `/api` | `/api/agents/reploom/reviews` | `/api/agents/reploom/reviews` | ✅ Connected |
| `/agents/reploom/reviews` | GET | `/api` | `/api/agents/reploom/reviews` | `/api/agents/reploom/reviews` | ✅ Connected |
| `/agents/reploom/reviews/{review_id}` | GET | `/api` | `/api/agents/reploom/reviews/{review_id}` | `/api/agents/reploom/reviews/{reviewId}` | ✅ Connected |
| `/agents/reploom/reviews/{review_id}/approve` | POST | `/api` | `/api/agents/reploom/reviews/{review_id}/approve` | `/api/agents/reploom/reviews/{reviewId}/approve` | ✅ Connected |
| `/agents/reploom/reviews/{review_id}/reject` | POST | `/api` | `/api/agents/reploom/reviews/{review_id}/reject` | `/api/agents/reploom/reviews/{reviewId}/reject` | ✅ Connected |
| `/agents/reploom/reviews/{review_id}/request-edit` | POST | `/api` | `/api/agents/reploom/reviews/{review_id}/request-edit` | `/api/agents/reploom/reviews/{reviewId}/request-edit` | ✅ Connected |
| `/agents/reploom/health` | GET | `/api` | `/api/agents/reploom/health` | Not Called | ⚠️ Unused |

### 1.8 Workspace Settings Routes
| Path | Method | Prefix | Full Path | Frontend Call | Status |
|------|--------|--------|-----------|---------------|--------|
| `/workspace-settings/{workspace_id}` | GET | `/api` | `/api/workspace-settings/{workspace_id}` | `/workspace-settings/{workspaceId}` | ❌ PATH MISMATCH |
| `/workspace-settings/{workspace_id}` | PUT | `/api` | `/api/workspace-settings/{workspace_id}` | `/workspace-settings/{workspaceId}` | ❌ PATH MISMATCH |

### 1.9 Auth Routes
| Path | Method | Prefix | Full Path | Frontend Call | Status |
|------|--------|--------|-----------|---------------|--------|
| `/auth/profile` | GET | `/api` | `/api/auth/profile` | `/api/auth/profile` | ✅ Connected |
| `/auth/login` | GET | `/api` | `/api/auth/login` | Redirect URL | ✅ Connected |
| `/auth/logout` | GET | `/api` | `/api/auth/logout` | Redirect URL | ✅ Connected |

---

## 2. FRONTEND API CLIENTS

### 2.1 analytics.ts
```typescript
- getAnalyticsSummary(params?: GetAnalyticsSummaryParams)
  Frontend Call: GET /analytics/summary
  Backend Path: /api/analytics/summary
  Status: ❌ CRITICAL - Missing /api prefix
```

### 2.2 documents.ts
```typescript
✅ getDocumentsForUser()
✅ getDocumentContent(documentId: string)
✅ shareDocument(documentId: string, emailAddresses: string[])
✅ deleteDocument(documentId: string)
```

### 2.3 reviews.ts
```typescript
✅ createReview(data: CreateReviewRequest)
✅ listReviews(params?: { status?: string; intent?: string })
✅ getReview(reviewId: string)
✅ approveReview(reviewId: string, data?: ReviewActionRequest)
✅ rejectReview(reviewId: string, data?: ReviewActionRequest)
✅ requestEdit(reviewId: string, data: UpdateReviewRequest)
✅ runDraft(data: { thread_id?: string; message_excerpt: string; workspace_id?: string })
```

### 2.4 workspace-settings.ts
```typescript
- getWorkspaceSettings(workspaceId: string)
  Frontend Call: GET /workspace-settings/{workspaceId}
  Backend Path: /api/workspace-settings/{workspace_id}
  Status: ❌ CRITICAL - Missing /api prefix

- updateWorkspaceSettings(workspaceId: string, settings: WorkspaceSettingsUpdate)
  Frontend Call: PUT /workspace-settings/{workspaceId}
  Backend Path: /api/workspace-settings/{workspace_id}
  Status: ❌ CRITICAL - Missing /api prefix
```

### 2.5 use-auth.ts
```typescript
✅ useAuth() -> Calls /api/auth/profile
✅ getLoginUrl() -> Redirect to /api/auth/login
✅ getSignupUrl() -> Redirect to /api/auth/login?screen_hint=signup
✅ getLogoutUrl() -> Redirect to /api/auth/logout
```

---

## 3. CONNECTION MATRIX

### 3.1 Connected & Working
| Frontend Function | Backend Endpoint | HTTP Method | Status |
|------------------|-----------------|------------|--------|
| getDocumentsForUser | /api/documents | GET | ✅ Connected |
| getDocumentContent | /api/documents/{id}/content | GET | ✅ Connected |
| shareDocument | /api/documents/{id}/share | POST | ✅ Connected |
| deleteDocument | /api/documents/{id} | DELETE | ✅ Connected |
| uploadDocument | /api/documents/upload | POST | ✅ Connected |
| createReview | /api/agents/reploom/reviews | POST | ✅ Connected |
| listReviews | /api/agents/reploom/reviews | GET | ✅ Connected |
| getReview | /api/agents/reploom/reviews/{id} | GET | ✅ Connected |
| approveReview | /api/agents/reploom/reviews/{id}/approve | POST | ✅ Connected |
| rejectReview | /api/agents/reploom/reviews/{id}/reject | POST | ✅ Connected |
| requestEdit | /api/agents/reploom/reviews/{id}/request-edit | POST | ✅ Connected |
| runDraft | /api/agents/reploom/run-draft | POST | ✅ Connected |
| useAuth (profile) | /api/auth/profile | GET | ✅ Connected |

### 3.2 CRITICAL PATH MISMATCHES
| Frontend Function | Frontend Call | Backend Path | Issue |
|------------------|--------------|--------------|-------|
| getAnalyticsSummary | /analytics/summary | /api/analytics/summary | ❌ Missing /api prefix |
| getWorkspaceSettings | /workspace-settings/{id} | /api/workspace-settings/{id} | ❌ Missing /api prefix |
| updateWorkspaceSettings | /workspace-settings/{id} | /api/workspace-settings/{id} | ❌ Missing /api prefix |

### 3.3 Frontend Features NOT Covered by API
| Feature | Needed Endpoint | Status |
|---------|-----------------|--------|
| Gmail Label Listing | /api/me/gmail/labels | ⚠️ Missing Frontend Client |
| Gmail Draft Creation | /api/me/gmail/threads/{id}/draft | ⚠️ Missing Frontend Client |
| Calendar Availability | /api/me/calendar/availability | ⚠️ Missing Frontend Client |
| KB Document Upload | /api/kb/upload | ⚠️ Missing Frontend Client |
| KB Search | /api/kb/search | ⚠️ Missing Frontend Client |

### 3.4 Backend Endpoints NOT Used by Frontend
| Endpoint | HTTP Method | Status |
|----------|------------|--------|
| /api/agents/reploom/runs/{thread_id} | GET | ⚠️ Implemented but Unused |
| /api/agents/reploom/health | GET | ⚠️ Implemented but Unused |

---

## 4. DATABASE VERIFICATION

### 4.1 Database Configuration
**File**: `/home/user/Reploom/backend/app/core/db.py`
- Engine: SQLModel with PostgreSQL
- Vector Extension: Enabled (CREATE EXTENSION IF NOT EXISTS vector)
- Session Management: Proper FastAPI dependency injection
- Init Function: Creates tables via SQLModel.metadata.create_all()
- Status: ✅ Properly Configured

### 4.2 Models Analysis

#### DraftReview Model
**File**: `/home/user/Reploom/backend/app/models/draft_reviews.py`
- Table: draft_reviews
- Primary Key: id (UUID)
- Indexes:
  - user_id (indexed)
  - thread_id (indexed)
  - run_id (optional, indexed)
  - Composite: (user_id, status)
  - Composite: (thread_id, user_id)
- Relationships: None explicit (foreign keys)
- Status: ✅ Properly Configured

#### GmailDraft Model
**File**: `/home/user/Reploom/backend/app/models/gmail_drafts.py`
- Table: gmail_drafts
- Primary Key: id (UUID)
- Indexes:
  - user_id (indexed)
  - thread_id (indexed)
  - reply_to_msg_id (indexed)
  - Composite: (user_id, thread_id, reply_to_msg_id)
- Relationships: None explicit
- Status: ✅ Properly Configured

#### WorkspaceSettings Model
**File**: `/home/user/Reploom/backend/app/models/workspace_settings.py`
- Table: workspace_settings
- Primary Key: id (UUID)
- Indexes:
  - workspace_id (indexed, unique)
- JSON Fields: style_json, blocklist_json
- Relationships: None explicit
- Status: ✅ Properly Configured

### 4.3 Potential Issues
- No explicit foreign key relationships defined between models
- DraftReview references user_id and thread_id as strings (not foreign keys)
- GmailDraft references user_id and thread_id as strings (not foreign keys)
- WorkspaceSettings has unique constraint on workspace_id

---

## 5. DETECTED ISSUES & RECOMMENDATIONS

### CRITICAL ISSUES (Blocking)

#### Issue #1: Analytics API Path Mismatch
**File**: `/home/user/Reploom/frontend/src/lib/analytics.ts:69`
**Problem**: Frontend calls `/analytics/summary` but backend expects `/api/analytics/summary`
**Impact**: Analytics page will fail to load
**Fix**: Change line 69 from:
```typescript
const response = await apiClient.get<AnalyticsSummary>("/analytics/summary", {
```
To:
```typescript
const response = await apiClient.get<AnalyticsSummary>("/api/analytics/summary", {
```

#### Issue #2: Workspace Settings API Path Mismatch
**File**: `/home/user/Reploom/frontend/src/lib/workspace-settings.ts:19,27`
**Problem**: Frontend calls `/workspace-settings/{id}` but backend expects `/api/workspace-settings/{id}`
**Impact**: Settings page will fail to load and save settings
**Fix**: Change lines 19 and 27 from:
```typescript
const response = await apiClient.get<WorkspaceSettings>(`/workspace-settings/${workspaceId}`);
const response = await apiClient.put<WorkspaceSettings>(`/workspace-settings/${workspaceId}`, settings);
```
To:
```typescript
const response = await apiClient.get<WorkspaceSettings>(`/api/workspace-settings/${workspaceId}`);
const response = await apiClient.put<WorkspaceSettings>(`/api/workspace-settings/${workspaceId}`, settings);
```

### WARNING ISSUES (Not Blocking)

#### Issue #3: Unused Backend Endpoints
**Endpoints**: 
- `GET /api/agents/reploom/runs/{thread_id}` - Implemented but never called from frontend
- `GET /api/agents/reploom/health` - Health check endpoint implemented but unused

**Recommendation**: Either:
1. Remove if not needed
2. Add frontend integration for run state inspection
3. Use health endpoint in monitoring/dashboards

#### Issue #4: Missing Frontend Clients for Features
**Missing Frontend Integration**:
- Gmail Label Listing
- Gmail Draft Creation (integrated in gmail.tsx but no client module)
- Calendar Availability Integration
- KB Document Upload
- KB Search

**Recommendation**: Create frontend client modules or add these features to frontend if planned for future use.

---

## 6. PAGES & COMPONENTS USING API

| Page/Component | API Functions Called | Status |
|---------------|-------------------|--------|
| AnalyticsPage.tsx | getAnalyticsSummary() | ❌ BROKEN (path mismatch) |
| DocumentsPage.tsx | getDocumentsForUser() | ✅ Working |
| ReviewPage.tsx | getReview(), approveReview(), rejectReview(), requestEdit() | ✅ Working |
| SettingsPage.tsx | getWorkspaceSettings(), updateWorkspaceSettings() | ❌ BROKEN (path mismatch) |
| InboxPage.tsx | listReviews() | ✅ Working |
| ChatPage.tsx | useAuth() | ✅ Working |
| document-upload-form.tsx | Direct POST /api/documents/upload | ✅ Working |
| document-item-actions.tsx | getDocumentContent(), shareDocument(), deleteDocument() | ✅ Working |

---

## 7. REQUEST/RESPONSE TYPE COMPATIBILITY

### 7.1 Type Matching Analysis

#### DraftReview Types
**Backend Response**: DraftReviewResponse (reploom.py)
**Frontend Type**: DraftReview (reviews.ts)
- ✅ All fields match
- ✅ Date formats compatible

#### Analytics Types
**Backend Response**: AnalyticsSummary with metrics object
**Frontend Type**: AnalyticsSummary
- ✅ All fields match
- ✅ Nested structures compatible

#### WorkspaceSettings Types
**Backend Response**: WorkspaceSettingsResponse
**Frontend Type**: WorkspaceSettings
- ✅ All fields match
- ✅ JSON fields properly handled

#### Documents Types
**Backend Response**: Document/DocumentWithoutContent
**Frontend Type**: Document
- ✅ Field mapping correct (file_name -> fileName)
- ✅ Date field mapping correct

---

## 8. SUMMARY TABLE

| Category | Metric | Value |
|----------|--------|-------|
| Total Backend Endpoints | Count | 26 |
| Total Frontend API Clients | Count | 10 |
| Working Connections | Count | 10 |
| Path Mismatches | Count | 2 ❌ |
| Unused Endpoints | Count | 2 ⚠️ |
| Missing Frontend Clients | Count | 5 ⚠️ |
| Database Models | Count | 3 |
| Database Configuration | Status | ✅ Correct |

### Overall Health Score: 62% (with critical issues)

---

## 9. ACTION ITEMS (Priority Order)

### 1. URGENT - Fix Path Mismatches
- [ ] Fix analytics.ts path mismatch
- [ ] Fix workspace-settings.ts path mismatches
- [ ] Test Analytics page loads correctly
- [ ] Test Settings page loads and saves correctly

### 2. HIGH - Investigate Unused Endpoints
- [ ] Determine if `/runs/{thread_id}` endpoint is needed
- [ ] Determine if `/health` endpoint serves a purpose
- [ ] Remove if not needed, or add frontend integration

### 3. MEDIUM - Database Relationships
- [ ] Consider adding explicit foreign key relationships
- [ ] Add database migrations for proper constraints
- [ ] Document foreign key relationships in models

### 4. MEDIUM - Missing Features
- [ ] Decide on Gmail integration timeline
- [ ] Decide on Calendar integration timeline
- [ ] Decide on KB feature timeline
- [ ] Create roadmap for missing features

### 5. LOW - Code Quality
- [ ] Add integration tests for API connections
- [ ] Document API contract in OpenAPI/Swagger
- [ ] Add request/response validation tests

