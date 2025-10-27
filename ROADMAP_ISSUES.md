# Reploom Roadmap Issues

This document contains detailed feature requests and enhancements for the next phase of Reploom development. These should be created as GitHub issues.

---

## Issue 1: Microsoft 365 / Outlook Integration

**Labels**: `enhancement`, `integration`, `high-priority`

**Title**: Add Microsoft 365 / Outlook Email Integration

### Problem Statement
Currently, Reploom only supports Gmail via Google OAuth. Many enterprise customers use Microsoft 365 and Outlook, which represents a significant portion of the email market. Without Outlook support, these users cannot benefit from Reploom's draft generation capabilities.

### Proposed Solution
Implement Microsoft Graph API integration to support Outlook email accounts:

**Technical Requirements:**
1. **OAuth 2.0 with Microsoft Identity Platform**
   - Add Microsoft social connection in Auth0
   - Request scopes: `Mail.Read`, `Mail.ReadWrite`, `Mail.Send` (draft-only initially)
   - Support both personal Microsoft accounts and Azure AD enterprise accounts

2. **Microsoft Graph API Integration**
   - Implement similar to `GmailService` → create `OutlookService`
   - Endpoints needed:
     - `GET /me/messages` - List inbox messages
     - `GET /me/messages/{id}` - Get single message
     - `POST /me/messages/{id}/createReply` - Create draft reply
     - `GET /me/mailFolders/drafts/messages` - List drafts
   - Handle message format conversion (Microsoft's MIME differs slightly from Gmail)

3. **Threading Support**
   - Use `conversationId` for thread grouping
   - Map to Gmail's thread_id concept in DraftReview model

4. **Backend Changes**
   - Add `email_provider` field to DraftReview model (`gmail` | `outlook`)
   - Create provider-agnostic interface for email operations
   - Detect provider from user's connected account

5. **Frontend Changes**
   - Add "Connect Outlook" button alongside "Connect Gmail"
   - Provider indicator in UI (Gmail icon vs. Outlook icon)
   - Handle provider-specific quirks (e.g., Outlook categories vs. Gmail labels)

### Alternative Solutions
1. **IMAP/SMTP Generic Integration** (see Issue 2) - would work for Outlook but less feature-rich
2. **Exchange Web Services (EWS)** - older API, being deprecated by Microsoft
3. **Outlook Add-in** - different deployment model, more complex

### Use Cases
1. Enterprise customers using Office 365
2. Users with @outlook.com, @hotmail.com, or @live.com addresses
3. Organizations with Azure AD authentication requirements
4. Hybrid setups (some users on Gmail, others on Outlook)

### Technical Considerations
- **Auth0 Token Vault**: Extend to support Microsoft refresh tokens
- **Message Format**: Outlook uses different HTML sanitization rules
- **Attachment Handling**: Microsoft Graph has different attachment API
- **Calendar Integration**: Already have Google Calendar - add Microsoft Calendar API
- **Rate Limits**: Microsoft Graph has different quota (30 requests/second for enterprise)

### Priority
- [x] High (critical for enterprise adoption)

### Estimated Effort
- Backend integration: 3-5 days
- Frontend UI updates: 1-2 days
- Testing and edge cases: 2-3 days
- Documentation: 1 day

**Total**: ~1.5-2 weeks

### Additional Context
- Microsoft Graph API docs: https://learn.microsoft.com/en-us/graph/api/overview
- Auth0 Microsoft connection guide: https://auth0.com/docs/connections/social/microsoft-account

---

## Issue 2: IMAP/SMTP Generic Email Integration

**Labels**: `enhancement`, `integration`, `medium-priority`

**Title**: Add IMAP/SMTP Support for Generic Email Providers

### Problem Statement
Gmail and Outlook cover most users, but many organizations use custom email servers (self-hosted Exchange, Zimbra, Dovecot, Postfix) or other providers (ProtonMail, FastMail, Zoho Mail). These users cannot use Reploom without OAuth-based API support.

### Proposed Solution
Implement IMAP/SMTP protocol support as a fallback for providers without OAuth APIs:

**Technical Requirements:**
1. **IMAP Integration (Read)**
   - Library: `imaplib` (Python stdlib) or `aioimaplib` (async)
   - Capabilities:
     - List mailboxes/folders
     - Fetch messages from INBOX
     - Search by criteria (unread, date range, sender)
     - Mark messages as read/unread
     - Move messages between folders

2. **SMTP Integration (Write)**
   - Library: `smtplib` (Python stdlib) or `aiosmtplib` (async)
   - Capabilities:
     - Send draft emails
     - Support TLS/SSL
     - Handle authentication (PLAIN, LOGIN, CRAM-MD5)

3. **Credential Storage**
   - **DO NOT store passwords in database** (security risk)
   - Use Auth0 Token Vault for IMAP/SMTP credentials
   - Encrypt passwords at rest using Fernet or similar
   - Allow app-specific passwords (for Gmail, Yahoo, etc.)

4. **Threading Detection**
   - Parse `In-Reply-To` and `References` headers to detect threads
   - Fallback to subject-based grouping if headers missing
   - Generate synthetic thread IDs for Reploom's internal tracking

5. **Draft Handling**
   - Store drafts in user's "Drafts" folder via IMAP
   - Use `\Draft` flag to mark as draft
   - Update draft if user edits (replace message)

6. **Backend Changes**
   - Add `ImapSmtpService` class
   - Store IMAP/SMTP connection settings per user:
     - `imap_host`, `imap_port`, `imap_use_ssl`
     - `smtp_host`, `smtp_port`, `smtp_use_ssl`
     - `username`, `encrypted_password`
   - Connection pooling to avoid login overhead

7. **Frontend Changes**
   - "Connect Email" form with manual configuration:
     - Email address
     - IMAP server and port
     - SMTP server and port
     - Username and password
   - Auto-detect common providers (Gmail: imap.gmail.com, Yahoo: imap.mail.yahoo.com)
   - Test connection button before saving

### Alternative Solutions
1. **Exchange Web Services (EWS)** - for older Exchange servers
2. **Email forwarding + webhook** - user forwards emails to Reploom, we process and reply
3. **Browser extension** - inject Reploom into webmail UIs (Gmail, Outlook web)

### Use Cases
1. Self-hosted email servers (Exchange, Zimbra, Dovecot)
2. Privacy-focused providers (ProtonMail Bridge via IMAP/SMTP)
3. Small providers without OAuth APIs (FastMail, Zoho Mail, GMX)
4. Organizations with strict security policies (no OAuth third-party apps)

### Technical Considerations
- **Security**: Passwords are sensitive - must encrypt at rest and in transit
- **Connection Pooling**: IMAP connections are slow to establish (TLS handshake)
- **IDLE Support**: IMAP IDLE allows real-time push notifications (vs. polling)
- **Message Parsing**: Email formats vary wildly (multipart MIME, encodings, etc.)
- **Rate Limiting**: No standard quota - provider-specific
- **Error Handling**: IMAP errors are cryptic and vary by server

### Priority
- [x] Medium (nice to have for broader adoption)

### Estimated Effort
- Backend IMAP/SMTP integration: 5-7 days
- Credential encryption and storage: 2-3 days
- Frontend connection UI: 2-3 days
- Testing across providers: 3-5 days
- Documentation: 1-2 days

**Total**: ~2.5-3 weeks

### Additional Context
- Python `imaplib` docs: https://docs.python.org/3/library/imaplib.html
- IMAP RFC 3501: https://www.rfc-editor.org/rfc/rfc3501
- SMTP RFC 5321: https://www.rfc-editor.org/rfc/rfc5321
- Auth0 Token Vault for custom credentials: https://auth0.com/docs/secure/tokens/token-vault

### Security Notes
- **Never log passwords** (not even encrypted ones)
- Use OAuth when available (Gmail, Outlook) - more secure than passwords
- Support 2FA via app-specific passwords
- Warn users about risks of password storage

---

## Issue 3: A/B Draft Testing and Multi-Variant Generation

**Labels**: `enhancement`, `ai-feature`, `high-priority`

**Title**: Generate Multiple Draft Variants for A/B Testing

### Problem Statement
Currently, Reploom generates a single draft per email. Users have no way to compare different tones, styles, or approaches. A/B testing is manual and time-consuming. Advanced users want options to choose from, and teams want to experiment with different messaging strategies.

### Proposed Solution
Implement multi-variant draft generation with A/B testing capabilities:

**Technical Requirements:**
1. **Multi-Variant Generation**
   - Generate 2-3 draft variants per email (configurable)
   - Variants differ by:
     - **Tone**: Formal (tone_level=2) vs. Casual (tone_level=4)
     - **Length**: Concise (50-100 words) vs. Detailed (200-300 words)
     - **Approach**: Direct vs. Empathetic vs. Solution-focused
   - Run agent workflow in parallel for efficiency (async)

2. **Draft Variants in Database**
   - Extend `DraftReview` model:
     - `draft_variant_id` (e.g., "A", "B", "C")
     - `draft_variant_config` (JSON: tone, length, approach)
     - `parent_thread_id` (group variants together)
   - Link variants: same `thread_id` + different `draft_variant_id`

3. **UI for Variant Selection**
   - Inbox: Show "3 variants" badge instead of single draft
   - Review page:
     - Tabs for each variant (Variant A | Variant B | Variant C)
     - Side-by-side comparison view (optional)
     - Quick switch between variants
   - Approve one variant → discard others

4. **A/B Testing Metrics**
   - Track which variants get approved more often
   - Aggregate stats by:
     - Tone level (which tone is preferred?)
     - Length (concise vs. detailed approval rates)
     - Approach (direct vs. empathetic)
   - Display in Analytics:
     - "Variant A approved 65% of the time"
     - "Concise drafts approved 20% faster"

5. **Workspace-Level Preferences**
   - Learn from A/B test results
   - Auto-adjust workspace settings:
     - "Support emails: prefer concise, tone_level=3"
     - "Executive emails: prefer detailed, tone_level=2"
   - Optional: User confirms before auto-adjusting

6. **Backend Changes**
   - New endpoint: `POST /api/agents/reploom/run-drafts-multi` (plural)
   - Response: `[{variant: "A", draft_html: "...", ...}, ...]`
   - Agent workflow:
     - Classifier runs once (shared intent)
     - Drafter runs N times (different prompts per variant)
     - PolicyGuard runs on all variants

7. **Frontend Changes**
   - Inbox: Badge showing "3 drafts" for multi-variant threads
   - Review page: Tabbed interface for variants
   - Analytics: New section "Variant Performance"

### Alternative Solutions
1. **Sequential Generation**: Generate one draft, then "Regenerate with different tone" button
2. **Post-Generation Editing**: Single draft + AI editing suggestions
3. **Manual A/B Test**: User creates variants manually (no automation)

### Use Cases
1. **Experimentation**: Teams testing different messaging strategies
2. **Personalization**: Choose tone based on customer profile (new vs. VIP customer)
3. **Training**: New hires see multiple examples to learn from
4. **Quality Assurance**: Compare drafts to catch edge cases (one variant might be better)
5. **Optimization**: Identify which tones/styles have highest approval rates

### Technical Considerations
- **Cost**: 3x OpenAI API calls per email (3 variants) - make it opt-in
- **Performance**: Run variants in parallel (async) to avoid 3x latency
- **UI Complexity**: Tabbed interface must be intuitive (not overwhelming)
- **Storage**: 3x database storage for drafts (minor cost increase)
- **Analytics Complexity**: Need to track variants separately

### Priority
- [x] High (differentiator vs. competitors)

### Estimated Effort
- Backend multi-variant generation: 3-4 days
- Database schema changes: 1 day
- Frontend tabbed UI: 3-4 days
- Analytics variant tracking: 2-3 days
- Testing and tuning: 2-3 days
- Documentation: 1 day

**Total**: ~2 weeks

### Additional Context
- Similar to how Grammarly shows multiple tone suggestions
- Could integrate with workspace learning (auto-improve tone over time)
- Future: ML model to predict which variant user will prefer (rank by likelihood)

---

## Issue 4: CRM Integration (Salesforce, HubSpot, Custom)

**Labels**: `enhancement`, `integration`, `high-priority`

**Title**: Integrate CRM Data for Context-Aware Draft Generation

### Problem Statement
Email responses often require customer context (past purchases, support tickets, account status, deal stage). Currently, Reploom has no access to CRM data, so drafts lack personalization. Sales and support teams manually look up customer info, reducing efficiency gains.

### Proposed Solution
Integrate with popular CRMs (Salesforce, HubSpot, custom REST APIs) to enrich draft generation with customer context:

**Technical Requirements:**
1. **CRM Connectors**
   - **Salesforce**: REST API + OAuth 2.0
     - Fetch account, contact, opportunity, case records
     - Use SOQL queries to get relevant data
   - **HubSpot**: REST API + OAuth 2.0
     - Fetch contacts, companies, deals, tickets
     - Use HubSpot's association API to link records
   - **Custom REST API**: Generic HTTP connector
     - User provides API endpoint, auth method (API key, OAuth)
     - Map response fields to Reploom's context schema

2. **Context Enrichment in Agent Workflow**
   - New LangGraph tool: `CrmLookupTool`
   - Input: Customer email address or name
   - Output: JSON with relevant fields:
     ```json
     {
       "customer_name": "Acme Corp",
       "account_status": "active",
       "subscription_tier": "enterprise",
       "last_purchase_date": "2025-09-15",
       "open_support_tickets": 2,
       "deal_stage": "negotiation",
       "account_owner": "Sarah Johnson"
     }
     ```
   - Inject into Drafter prompt:
     ```
     Context: Customer is Acme Corp (enterprise tier, active since 2024)
     They have 2 open support tickets. Draft accordingly.
     ```

3. **CRM Data Storage**
   - **Option A**: Cache CRM data in Reploom (faster, but stale data risk)
   - **Option B**: Real-time API calls (slower, always fresh)
   - **Hybrid**: Cache with TTL (e.g., 1 hour expiry)

4. **Backend Changes**
   - Add `CrmConnector` base class
   - Implement `SalesforceConnector`, `HubSpotConnector`, `CustomApiConnector`
   - Store CRM credentials in Auth0 Token Vault (OAuth tokens, API keys)
   - New endpoints:
     - `POST /api/crm/connect` - Start OAuth flow
     - `GET /api/crm/status` - Check if connected
     - `POST /api/crm/disconnect` - Revoke access
     - `GET /api/crm/lookup?email=user@example.com` - Test lookup

5. **Frontend Changes**
   - Settings page: "CRM Integration" section
   - Dropdown to select CRM provider (Salesforce, HubSpot, Custom API)
   - "Connect" button → OAuth flow or API key input
   - Test connection UI (validate before saving)
   - Review page: Show CRM context used (e.g., "Customer: Acme Corp, Tier: Enterprise")

6. **Agent Workflow Integration**
   - ContextBuilder node calls `CrmLookupTool`
   - Pass CRM data to Drafter node
   - If CRM lookup fails (not found, API error), continue without context (graceful degradation)

### Alternative Solutions
1. **Manual Context Upload**: User pastes CRM data into a text field (no automation)
2. **Email Signature Parsing**: Extract company info from email signature (limited data)
3. **Zapier/Make Integration**: Use third-party automation platform as glue
4. **Browser Extension**: Inject CRM sidebar into Reploom UI (technical complexity)

### Use Cases
1. **Sales**: Drafts reference deal stage, past conversations, pricing tier
2. **Support**: Drafts acknowledge open tickets, past issues, account status
3. **Customer Success**: Drafts personalized to renewal date, health score, usage metrics
4. **Executive Comms**: Drafts reference company size, industry, decision-maker role

### Technical Considerations
- **Rate Limits**: Salesforce (15,000 requests/day), HubSpot (10 requests/second)
- **Latency**: CRM API calls add 200-500ms per draft (acceptable if cached)
- **Data Privacy**: CRM data is sensitive - log redaction, access controls
- **Field Mapping**: CRMs have different schemas - normalize to common format
- **Multi-CRM Support**: Some orgs use multiple CRMs (Salesforce + Zendesk)

### Priority
- [x] High (critical for sales and support teams)

### Estimated Effort
- CRM connector framework: 3-4 days
- Salesforce connector: 2-3 days
- HubSpot connector: 2-3 days
- Custom API connector: 2-3 days
- LangGraph CrmLookupTool: 1-2 days
- Frontend integration UI: 2-3 days
- Testing and edge cases: 3-4 days
- Documentation: 1-2 days

**Total**: ~3-4 weeks

### Additional Context
- Salesforce REST API: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/
- HubSpot API: https://developers.hubspot.com/docs/api/overview
- Similar to how Lavender, Crystalknows, and other sales tools integrate CRM
- Could train a model to predict best CRM fields to include (relevance ranking)

---

## Implementation Priority Recommendation

Based on impact and effort:

1. **Phase 1 (MVP+)**: Essential for market fit
   - ✅ Issue 3: A/B Draft Testing (high impact, 2 weeks)
   - ✅ Issue 4: CRM Integration (high impact, 3-4 weeks)

2. **Phase 2 (Market Expansion)**: Broaden user base
   - Issue 1: Microsoft 365 / Outlook (critical for enterprise, 1.5-2 weeks)

3. **Phase 3 (Advanced Features)**: Long-tail support
   - Issue 2: IMAP/SMTP (lower priority, 2.5-3 weeks)

**Total estimated time for all features**: ~9-12 weeks (2-3 engineers, parallel work)

---

## How to Create These Issues

Run the following commands to create GitHub issues:

```bash
# Issue 1: Microsoft 365
gh issue create --title "Add Microsoft 365 / Outlook Email Integration" --body-file ROADMAP_ISSUES.md --label enhancement,integration,high-priority

# Issue 2: IMAP/SMTP
gh issue create --title "Add IMAP/SMTP Support for Generic Email Providers" --body-file ROADMAP_ISSUES.md --label enhancement,integration,medium-priority

# Issue 3: A/B Drafts
gh issue create --title "Generate Multiple Draft Variants for A/B Testing" --body-file ROADMAP_ISSUES.md --label enhancement,ai-feature,high-priority

# Issue 4: CRM Integration
gh issue create --title "Integrate CRM Data for Context-Aware Draft Generation" --body-file ROADMAP_ISSUES.md --label enhancement,integration,high-priority
```

Alternatively, manually create them via GitHub UI using the descriptions above.

---

Last updated: 2025-10-27
