# Reploom Safety & Security Documentation

This document outlines the safety measures, security practices, and compliance considerations for Reploom.

## Table of Contents
1. [No Auto-Send Policy](#no-auto-send-policy)
2. [Gmail Scopes & Permissions](#gmail-scopes--permissions)
3. [Data Residency & Storage](#data-residency--storage)
4. [Security Features](#security-features)
5. [Privacy & PII Handling](#privacy--pii-handling)
6. [Compliance Considerations](#compliance-considerations)

---

## No Auto-Send Policy

**Reploom never automatically sends emails on behalf of users.**

### Human-in-the-Loop Workflow
- All AI-generated drafts require explicit human review and approval
- Drafts are created in Gmail's "Drafts" folder and remain there until manually sent
- Users can:
  - **Approve**: Mark draft as ready to send (user must still manually send from Gmail)
  - **Reject**: Discard the draft
  - **Request Edit**: Provide feedback for regeneration (future feature)

### Why Draft-Only Mode?
1. **Safety**: Prevents accidental or inappropriate automated emails
2. **Quality Control**: Humans verify accuracy, tone, and appropriateness
3. **Compliance**: Meets requirements for human oversight in sensitive communications
4. **Trust**: Users maintain full control over what gets sent

### Confidence Gates
- Each draft includes a confidence score (0.0-1.0) from the classifier
- Workspaces can set `approval_threshold` for flagging low-confidence drafts
- Low-confidence drafts are highlighted in the review UI
- **Note**: Even high-confidence drafts require human approval

---

## Gmail Scopes & Permissions

Reploom requests minimal Gmail API scopes necessary for core functionality.

### Required Scopes

| Scope | Purpose | Why We Need It |
|-------|---------|----------------|
| `openid` | Basic authentication | Standard OAuth 2.0 requirement |
| `profile` | User profile information | Display user name in UI |
| `email` | User email address | Identify the connected Gmail account |
| `https://www.googleapis.com/auth/gmail.readonly` | Read emails and labels | Fetch thread context for draft generation |
| `https://www.googleapis.com/auth/gmail.modify` | Modify drafts and labels | Create and update drafts in Gmail |
| `https://www.googleapis.com/auth/gmail.compose` | Create new messages | Generate draft replies |

### What We DON'T Request
- ❌ `gmail.send` - We cannot send emails on your behalf
- ❌ `gmail.settings.basic` - We cannot modify Gmail settings
- ❌ `gmail.settings.sharing` - We cannot change forwarding rules
- ❌ Full drive access - We only access Gmail

### Scope Limitations
- **Read-only thread access**: We fetch message content only when generating drafts
- **Draft modification only**: We create/update drafts but cannot send them
- **No permanent deletion**: We don't delete emails, only work with drafts

### Revoking Access
Users can revoke Reploom's Gmail access at any time:
1. Visit Google Account Settings: https://myaccount.google.com/permissions
2. Find "Reploom" or your Auth0 application
3. Click "Remove Access"

---

## Data Residency & Storage

### What Data We Store

| Data Type | Location | Retention | Purpose |
|-----------|----------|-----------|---------|
| Draft reviews | PostgreSQL (your instance) | Indefinite (user-controlled) | Track review workflow and analytics |
| Original message excerpts | PostgreSQL | Indefinite (user-controlled) | Provide context in review UI |
| AI-generated drafts | PostgreSQL + Gmail Drafts | Until approved/rejected | Allow review and editing |
| Workspace settings | PostgreSQL | Indefinite | Store tone level, blocklist, style preferences |
| User metadata | PostgreSQL | While account active | Link reviews to users |
| Uploaded documents | PostgreSQL + Qdrant | Until deleted | RAG context for draft generation |
| Document embeddings | Qdrant vector DB | Until document deleted | Semantic search for KB retrieval |

### What Data We DON'T Store
- ❌ Full email content (only excerpts needed for context)
- ❌ Gmail refresh tokens (using Auth0 Token Vault)
- ❌ Raw OAuth access tokens in application database
- ❌ Email attachments (unless explicitly uploaded as documents)
- ❌ Complete Gmail mailbox archives

### Data Residency Configuration

**Current Status**: 🚧 Placeholder - Not yet implemented

**Future Implementation**:
```python
# Environment variable to control data residency
DATA_RESIDENCY_REGION = "us-east-1"  # Options: us-east-1, eu-west-1, ap-southeast-2

# Database endpoint configuration
POSTGRES_HOST = f"reploom-db-{DATA_RESIDENCY_REGION}.example.com"
QDRANT_HOST = f"reploom-vector-{DATA_RESIDENCY_REGION}.example.com"

# Compliance mode flags
GDPR_MODE = True  # Enable GDPR-compliant data handling
CCPA_MODE = True  # Enable CCPA-compliant data handling
DATA_RETENTION_DAYS = 90  # Auto-delete old reviews after N days
```

**Planned Features**:
- Regional database deployment options
- Automatic data retention policies
- User-initiated data export (GDPR Article 20)
- User-initiated data deletion (GDPR Article 17 - Right to be forgotten)

**For Enterprise Deployments**:
- Self-hosted option: Deploy Reploom entirely in your infrastructure
- No data leaves your environment
- Full control over data residency and retention
- Bring your own databases (PostgreSQL, Qdrant)

---

## Security Features

### 1. Auth0 Token Vault
**Problem**: Storing OAuth refresh tokens is risky and complicates compliance.

**Solution**: Auth0 Token Vault provides credential-free API access.

**How it works**:
```
User → Auth0 Login → Token Vault stores refresh token
↓
Reploom Backend needs Gmail access
↓
Auth0 Token Vault exchanges federated token for access token
↓
Reploom uses access token (short-lived, never stored)
```

**Benefits**:
- No refresh tokens in application database
- Short-lived access tokens (1 hour expiry)
- Automatic token rotation
- Revocation via Auth0 dashboard
- Audit logs for all token exchanges

### 2. PII Redaction in Logs
All logs automatically redact sensitive information:

```python
# User IDs truncated
"auth0|1234567890abcdef" → "auth0|123..."

# Email addresses masked
"user@example.com" → "***@***"

# Draft content not logged
# Only metadata (thread_id, run_id, confidence) appears in logs
```

### 3. OpenTelemetry Observability
Distributed tracing tracks all operations without exposing sensitive data:

**Traced operations**:
- Gmail API calls (without email content)
- Agent workflow execution
- Database queries (parameterized, no data in logs)
- API endpoint requests (user IDs redacted)

**Security context attributes**:
- `user.id`: Redacted user identifier
- `workspace.id`: Workspace identifier
- `operation.type`: Operation category (classify, draft, retrieve)
- `auth.method`: Authentication method used

**NOT traced**:
- Email message bodies
- Draft HTML content
- User passwords or tokens
- PII from uploaded documents

### 4. Fine-Grained Authorization (Auth0 FGA)
Every operation checks user permissions:

```
User → API Request → Auth0 FGA checks:
  - Can user access this workspace?
  - Can user read this draft?
  - Can user modify workspace settings?
  - Can user upload documents to this workspace?
```

**Permission model**:
- `workspace:admin` - Full workspace control
- `workspace:member` - Create and review drafts
- `workspace:viewer` - Read-only access
- `document:owner` - Created the document
- `document:shared` - Document shared with user

### 5. Database Security
- Passwords stored with bcrypt hashing
- Parameterized queries (SQLModel ORM prevents SQL injection)
- Database connection over TLS (production)
- Row-level security (future enhancement)

---

## Privacy & PII Handling

### What Qualifies as PII?
- Email addresses
- User names
- Phone numbers
- Physical addresses
- Credit card numbers
- Social Security Numbers
- Any government-issued IDs

### How We Protect PII

#### 1. Minimize Collection
- Only extract message excerpts (first 500 characters) for context
- Don't store full email threads
- Don't store email metadata (headers, sender details beyond what's needed)

#### 2. Access Controls
- Users can only see their own drafts (unless shared via workspace)
- Workspace isolation prevents cross-workspace data access
- API endpoints filter by `user_id` automatically

#### 3. Redaction in Logs
- Automatic PII redaction in application logs
- OpenTelemetry traces exclude sensitive attributes
- Error messages don't expose data (only generic errors to users)

#### 4. Document Sharing Controls
- Documents default to private (only uploader can access)
- Explicit sharing required to grant access
- Sharing scoped to workspace members
- Document deletion cascades to embeddings

#### 5. Data Export & Deletion
**Current**: Manual via database queries

**Future**: Self-service via UI
- Export all my data (JSON format)
- Delete my account and all associated data
- Download all draft reviews and settings

---

## Compliance Considerations

### GDPR (General Data Protection Regulation)
**Status**: 🚧 Partial compliance - gaps identified below

**What we support**:
- ✅ Minimal data collection (Article 5)
- ✅ Purpose limitation (drafts only, no marketing)
- ✅ Access controls (user can access own data)
- ✅ Data security (encryption in transit, access controls)

**Gaps to address**:
- ⚠️ No automated data export (Article 20 - Right to data portability)
- ⚠️ No automated data deletion (Article 17 - Right to be forgotten)
- ⚠️ No consent management UI (Article 7)
- ⚠️ No Data Processing Agreement for sub-processors (Article 28)
- ⚠️ No Data Protection Impact Assessment (Article 35)

### CCPA (California Consumer Privacy Act)
**Status**: 🚧 Partial compliance

**What we support**:
- ✅ Data minimization
- ✅ Security safeguards
- ✅ No sale of personal information

**Gaps to address**:
- ⚠️ No "Do Not Sell My Personal Information" link
- ⚠️ No automated data disclosure (user request required)
- ⚠️ No automated deletion process

### SOC 2 Type II
**Status**: ❌ Not certified

**For enterprise deployments**:
- Self-host in your SOC 2 compliant infrastructure
- Inherit your organization's controls
- No third-party data processing

### HIPAA (Health Insurance Portability and Accountability Act)
**Status**: ❌ Not HIPAA compliant

**Warning**: Do NOT use Reploom for protected health information (PHI) until:
- Business Associate Agreement (BAA) is signed
- HIPAA-compliant infrastructure is deployed
- Access logging and audit trails are implemented
- Encryption at rest is enabled
- Backup and disaster recovery meets HIPAA requirements

### ISO 27001
**Status**: ❌ Not certified

**Recommended for production**:
- Use encrypted database connections (TLS)
- Enable disk encryption for data at rest
- Implement key rotation policies
- Deploy in ISO 27001 certified cloud environments

---

## Roadmap: Planned Safety Features

### Short-term (Next 3 months)
- [ ] User-initiated data export (GDPR Article 20)
- [ ] User-initiated data deletion (GDPR Article 17)
- [ ] Configurable data retention policies
- [ ] Enhanced PII detection and redaction
- [ ] Audit log for all data access events

### Medium-term (3-6 months)
- [ ] Regional data residency selection (US, EU, APAC)
- [ ] End-to-end encryption for draft content at rest
- [ ] Advanced permission roles (read-only, draft-only, admin)
- [ ] Consent management UI (cookie consent, data processing consent)
- [ ] Sub-processor disclosure and DPA templates

### Long-term (6-12 months)
- [ ] SOC 2 Type II certification
- [ ] ISO 27001 certification
- [ ] HIPAA compliance mode (for healthcare customers)
- [ ] Zero-knowledge encryption option
- [ ] Federated deployment (customer-hosted agents)

---

## Contact & Responsible Disclosure

### Security Issues
If you discover a security vulnerability, please email:
- **Security Team**: security@reploom.example.com (placeholder)

**Do NOT** open a public GitHub issue for security vulnerabilities.

### Privacy Questions
For questions about data handling and privacy:
- **Privacy Team**: privacy@reploom.example.com (placeholder)

### Bug Bounty Program
**Status**: 🚧 Coming soon

We're planning to launch a bug bounty program for security researchers. Stay tuned!

---

## Disclaimer

Reploom is provided "as-is" for demonstration and development purposes. For production use with sensitive data:

1. Review this safety documentation thoroughly
2. Conduct your own security audit
3. Ensure compliance with applicable regulations in your jurisdiction
4. Consider self-hosting for maximum control
5. Implement additional security measures as needed for your use case

**Use in production at your own risk. Reploom maintainers are not liable for data breaches, compliance violations, or damages arising from use of this software.**

---

Last updated: 2025-10-27
