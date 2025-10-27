# feat: Scaffold Microsoft 365/Outlook Integration

## Summary

This PR scaffolds the foundational structure for **Microsoft 365/Outlook integration** into Reploom, mirroring the existing Gmail implementation pattern. The integration provides a provider-agnostic service layer that will allow users to connect their Outlook accounts alongside Gmail.

**Status**: 🚧 **Scaffold Complete** - Core structure in place, pending Auth0 Token Vault configuration for full functionality.

---

## 📋 What's Included

### ✅ Completed in this PR

#### 1. **Environment & Configuration**
- ✨ Added Microsoft 365 environment variables (`MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`)
- 📝 Documented required OAuth scopes (Mail.Read, Mail.ReadWrite) in `.env.example`
- ⚙️ Added `OUTLOOK_SCOPES` configuration with computed field for scope parsing

#### 2. **Service Layer** (`backend/app/integrations/outlook_service.py`)
- 📧 **`list_messages()`**: List Outlook messages with pagination support
- 📬 **`get_message()`**: Retrieve specific message by ID with full details
- ✍️ **`create_reply_draft()`**: Create reply drafts using Microsoft Graph API's `createReply` action
- 🛡️ **Error Handling**: Custom exceptions (`OutlookServiceError`, `MessageNotFoundError`, `InvalidMessageError`)
- 📊 **OpenTelemetry Tracing**: Full observability for all operations
- 🎯 **Consistent Patterns**: Mirrors `GmailService` structure for maintainability

#### 3. **API Routes** (`backend/app/api/routes/outlook.py`)
- 🌐 **GET `/api/me/outlook/messages`**: List messages with folder, pagination, and filtering
- 📝 **POST `/api/me/outlook/draft`**: Create reply drafts with HTML body support
- ⏸️ **Current Status**: Returns `501 Not Implemented` until Auth0 Token Vault is configured
- 🔗 Registered `outlook_router` in main API router

#### 4. **Database Models**
- 🗂️ **Updated `DraftReview`**: Added `email_provider` field (default: `"gmail"`) for multi-provider support
- 🆕 **Created `OutlookDraft`** model: Idempotency tracking for Outlook drafts
  - Mirrors `GmailDraft` structure
  - Uses `conversation_id` instead of `thread_id` (Outlook terminology)
  - SHA256 content hashing for duplicate detection

#### 5. **Comprehensive Unit Tests** (`tests/unit/test_outlook_service.py`)
- ✅ **TestListMessages**: Success, unauthorized, folder not found, forbidden, pagination
- ✅ **TestGetMessage**: Success, not found, unauthorized
- ✅ **TestCreateReplyDraft**: Success, with comment, message not found, invalid request, rate limit, missing draft ID
- 🧪 All tests use mocked Microsoft Graph API responses
- 🔄 Mirrors Gmail test structure for consistency

---

## 🚀 Next Steps & TODOs

### 🔴 **High Priority - Required for Full Functionality**

#### Auth0 Token Vault Configuration
- [ ] **Implement `get_microsoft_access_token()`** in `token_exchange.py`
  - Pattern: Mirror `get_google_access_token()` structure
  - Exchange Auth0 session for Microsoft access token
  - Handle scope validation and error cases
- [ ] **Configure Auth0 Token Vault** for Microsoft 365
  - Add Microsoft as a social connection in Auth0
  - Configure token exchange in Auth0 settings
  - Set up required OAuth scopes
- [ ] **Test token exchange flow** end-to-end
  - Verify token acquisition works
  - Test scope validation
  - Confirm token refresh behavior

#### API Routes Activation
- [ ] **Uncomment token exchange code** in `outlook.py` routes
- [ ] **Remove `501 Not Implemented`** placeholders
- [ ] **Implement idempotency logic** using `OutlookDraft` model
- [ ] **Test routes** with real Microsoft access tokens
- [ ] **Add integration tests** for Outlook routes (similar to `test_gmail_routes.py`)

#### Database Migrations
- [ ] **Create Alembic migration** for `email_provider` field in `draft_reviews` table
  - Default value: `"gmail"` (backward compatible)
  - Index on `(user_id, email_provider)` for performance
- [ ] **Create Alembic migration** for `outlook_drafts` table
  - Indexes: `user_id`, `conversation_id`, `message_id`
  - Composite index: `(user_id, conversation_id, message_id)`
- [ ] **Test migrations** in development and staging environments

---

### 🟡 **Medium Priority - UI & User Experience**

#### Frontend Integration
- [ ] **Add email provider selector** in settings/preferences
  - Toggle between Gmail and Outlook
  - Display connected accounts
  - Show OAuth connection status
- [ ] **Update draft creation UI** to support Outlook
  - Detect active email provider
  - Show provider-specific icons/branding
  - Handle provider-specific features
- [ ] **Create Outlook-specific components**
  - Message list view (adapt for Outlook data structure)
  - Message detail view
  - Draft editor (reuse existing with provider awareness)
- [ ] **Update authentication flow**
  - Add "Connect Outlook" button alongside Gmail
  - Handle Microsoft login redirect
  - Display connection status in UI
  - Support multiple accounts per provider

#### Error Handling & User Feedback
- [ ] **Add user-friendly error messages** for Microsoft-specific errors
- [ ] **Implement retry logic** for transient Graph API errors
- [ ] **Show connection health** in UI (e.g., "Outlook connected", "Gmail disconnected")

---

### 🟢 **Low Priority - Nice to Have**

#### Documentation
- [ ] **Microsoft 365 Setup Guide**
  - How to register Azure AD application
  - Required API permissions
  - Redirect URI configuration
- [ ] **API Documentation**
  - OpenAPI/Swagger specs for Outlook endpoints
  - Example requests/responses
  - Error code reference
- [ ] **Troubleshooting Guide**
  - Common Microsoft Graph API errors
  - Token expiration handling
  - Scope permission issues

#### Additional Features
- [ ] **Outlook Calendar Integration** (similar to Google Calendar availability peek)
- [ ] **Outlook-specific features**
  - Categories (color-coded labels)
  - Flags (follow-up reminders)
  - Focused Inbox vs. Other
- [ ] **Shared Mailboxes** support (Graph API feature)
- [ ] **Attachment Handling** (upload/download via Graph API)
- [ ] **Conversation Threading** improvements (Outlook has richer threading)

---

## 🧪 Testing Strategy

### Unit Tests ✅ (Completed)
- `test_outlook_service.py` - All OutlookService functions with mocked Graph API
- Covers success cases, error cases, edge cases
- Mirrors Gmail test coverage

### Integration Tests 🚧 (TODO)
- [ ] `test_outlook_routes.py` - Full request/response flow with mocked token exchange
- [ ] End-to-end tests with real Auth0 token vault (staging environment)

### Manual Testing 📝 (TODO)
- [ ] Test with real Outlook account
- [ ] Verify draft creation in Outlook web/desktop client
- [ ] Test error scenarios (expired token, insufficient permissions)
- [ ] Verify idempotency (duplicate draft prevention)

---

## 📊 Architecture Decisions

### Why Mirror Gmail Structure?
- **Consistency**: Easier maintenance and debugging
- **Code Reuse**: Shared patterns for error handling, logging, tracing
- **Future-Proofing**: Easy to add more providers (Yahoo, iCloud, etc.)

### Why Separate `OutlookDraft` Model?
- **Provider-Specific IDs**: Outlook uses `conversationId` vs Gmail's `threadId`
- **Cleaner Queries**: Avoid complex conditionals in a single table
- **Future Flexibility**: Each provider can add custom fields without schema bloat

### Why Graph API `createReply`?
- **Automatic Threading**: Graph API handles In-Reply-To and References headers
- **Simpler Code**: No need to manually construct MIME messages (unlike Gmail)
- **Native Features**: Leverages Outlook's native reply semantics

---

## 🔐 Security Considerations

- ✅ **No Token Storage**: Access tokens obtained on-demand via Auth0 Token Vault
- ✅ **Scope Validation**: Only request necessary scopes (Mail.Read, Mail.ReadWrite)
- ✅ **Secure Logging**: Sanitize user identifiers in logs (first 8 chars + "...")
- ✅ **Error Sanitization**: Never expose tokens or sensitive data in error messages
- ⚠️ **TODO**: Implement rate limiting for Outlook API calls

---

## 📸 Preview (After Full Implementation)

### Expected User Flow:
1. User clicks **"Connect Outlook"** in settings
2. Redirects to Microsoft login (OAuth consent)
3. User grants Mail.Read and Mail.ReadWrite permissions
4. Auth0 stores Microsoft refresh token (in Token Vault)
5. User can now:
   - View Outlook messages in Reploom
   - Create draft replies
   - Switch between Gmail and Outlook seamlessly

---

## 🤝 Review Checklist

- [x] Code follows existing patterns (mirrors Gmail)
- [x] Comprehensive unit tests added
- [x] Environment variables documented
- [x] Error handling implemented
- [x] OpenTelemetry tracing added
- [ ] Integration tests (pending token exchange)
- [ ] Frontend UI updates (pending)
- [ ] Database migrations (pending)
- [ ] Documentation (pending)

---

## 🙏 Notes for Reviewers

This PR is a **scaffold/foundation** for Microsoft 365 integration. The core service layer and API routes are complete, but **full functionality requires**:

1. **Auth0 Token Vault configuration** for Microsoft
2. **Frontend UI** to connect Outlook accounts
3. **Database migrations** for new models

The code is structured to make these next steps straightforward. All TODOs are clearly marked with `# TODO:` comments in the code.

**Recommendation**: Merge this PR to establish the foundation, then tackle TODOs in separate PRs:
- PR #2: Auth0 Token Vault + Token Exchange
- PR #3: Database Migrations
- PR #4: Frontend Integration

---

## 📦 Files Changed

### Created Files:
- `backend/app/integrations/outlook_service.py` - Outlook service layer (646 lines)
- `backend/app/api/routes/outlook.py` - Outlook API routes (491 lines)
- `backend/app/models/outlook_drafts.py` - OutlookDraft model (51 lines)
- `backend/tests/unit/test_outlook_service.py` - Comprehensive unit tests (495 lines)

### Modified Files:
- `backend/.env.example` - Added Microsoft 365 environment variables
- `backend/app/core/config.py` - Added Outlook scope configuration
- `backend/app/api/api_router.py` - Registered outlook_router
- `backend/app/models/draft_reviews.py` - Added email_provider field

**Total**: 1,683 lines added across 8 files

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
