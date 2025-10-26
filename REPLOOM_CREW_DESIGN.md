# Reploom Crew: Draft Generation Workflow

## Overview

The Reploom Crew is a minimal LangGraph-based multi-agent workflow for generating email drafts with intent classification, context retrieval, tone control, and policy enforcement.

## Architecture

### Workflow Graph

```
┌─────────────┐
│  classifier │  Predicts intent (support/cs/exec/other) and confidence
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ contextBuilder  │  Retrieves relevant context (stub for now)
└──────┬──────────┘
       │
       ▼
┌─────────────┐
│   drafter   │  Generates HTML draft with tone control
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ policyGuard │  Checks blocklist and compliance
└──────┬──────┘
       │
       ▼ (violations?)
    [halt/continue]
```

### State Schema

```typescript
interface DraftCrewState {
  // Input
  original_message_summary: string;
  workspace_id?: string;

  // Intermediate
  intent?: "support" | "cs" | "exec" | "other";
  confidence?: number;  // 0.0 - 1.0
  context_snippets: string[];

  // Output
  draft_html?: string;
  violations: string[];

  // Config
  tone_level?: "formal" | "friendly" | "casual";
  blocklist: string[];
}
```

## Nodes

### 1. Classifier Node

**Purpose:** Analyze incoming message and predict intent category.

**Input:** `original_message_summary`

**Output:** `intent`, `confidence`

**Categories:**
- `support`: Technical support or troubleshooting
- `cs`: Customer service, billing, account questions
- `exec`: Executive, partnership, press inquiries
- `other`: General or uncategorized

**Implementation:** Uses GPT-4o-mini with zero-shot classification.

### 2. Context Builder Node (Stub)

**Purpose:** Retrieve relevant context for draft generation.

**Input:** `original_message_summary`, `workspace_id`, `intent`

**Output:** `context_snippets`

**Current State:** Returns empty list.

**Future Enhancements:**
- RAG retrieval from Qdrant (workspace documents, KB articles)
- Past conversation history
- Workspace-specific templates
- User preferences

### 3. Drafter Node

**Purpose:** Generate HTML email draft with tone control.

**Input:** `original_message_summary`, `intent`, `tone_level`, `context_snippets`

**Output:** `draft_html`

**Tone Levels:**
- `formal`: Professional, no contractions, precise language
- `friendly`: Warm, professional, helpful tone (default)
- `casual`: Conversational, relaxed, personable

**Implementation:** Uses GPT-4o-mini with tone-specific system prompts.

### 4. Policy Guard Node

**Purpose:** Enforce workspace policies and prevent violations.

**Input:** `draft_html`, `blocklist`, `tone_level`

**Output:** `violations`

**Checks:**
1. **Blocklist Enforcement:** Detects disallowed phrases (case-insensitive)
2. **Tone Compliance:** (Future) Verifies tone matches workspace standards

**Behavior:** If violations detected, workflow halts and returns violations list.

## Persistence

### Checkpointer Implementation

**Current:** `MemorySaver` (in-memory checkpointer)

**Reason:** PostgreSQL checkpointer requires `langgraph-checkpoint-postgres` package which is not included in base dependencies.

**TODO:** Migrate to `PostgresCheckpointer` for production use.

```python
# TODO: Replace with PostgreSQL checkpointer
# from langgraph.checkpoint.postgres import PostgresCheckpointer
# checkpointer = PostgresCheckpointer.from_conn_string(settings.DATABASE_URL)
```

**Thread ID Support:** All runs support `thread_id` for resumable execution and human-in-the-loop workflows.

## API Endpoints

### POST `/api/agents/reploom/run-draft`

Trigger the draft generation workflow.

**Request:**
```json
{
  "thread_id": "customer-123-msg-456",
  "message_excerpt": "I need help resetting my password",
  "workspace_id": "ws-acme-corp",
  "tone_level": "friendly",
  "blocklist": ["free trial", "limited time offer"]
}
```

**Response:**
```json
{
  "draft_html": "<p>Hi there! I'd be happy to help...</p>",
  "confidence": 0.92,
  "intent": "support",
  "violations": [],
  "thread_id": "customer-123-msg-456"
}
```

**With Violations:**
```json
{
  "draft_html": "<p>Get your free trial now...</p>",
  "confidence": 0.85,
  "intent": "cs",
  "violations": ["Blocklisted phrase detected: 'free trial'"],
  "thread_id": "customer-123-msg-456"
}
```

### GET `/api/agents/reploom/health`

Check if the Reploom crew and LangGraph server are available.

**Response:**
```json
{
  "status": "healthy",
  "langgraph_server": "connected"
}
```

## Configuration

### Environment Variables

```bash
# Optional: Workspace-level defaults (can be overridden per request)
REPLOOM_BLOCKLIST="free trial,money back guarantee,limited time offer"
REPLOOM_DEFAULT_TONE="friendly"
```

### Workspace Configuration (Future)

Store in database:

```sql
CREATE TABLE workspace_config (
  workspace_id VARCHAR PRIMARY KEY,
  blocklist TEXT[],
  default_tone VARCHAR,
  approval_threshold FLOAT,  -- Confidence threshold for auto-send
  ...
);
```

## Testing

### Unit Tests

Located in `tests/unit/test_reploom_crew.py`.

**Coverage:**
- ✅ Policy guard blocklist detection (single phrase)
- ✅ Policy guard blocklist detection (multiple phrases)
- ✅ Policy guard case-insensitivity
- ✅ Policy guard clean drafts (no violations)
- ✅ Tone variations (formal vs friendly vs casual)
- ✅ Classifier intent detection
- ✅ Context builder (stub)
- ✅ Full workflow integration

**Run Tests:**
```bash
cd backend
pytest tests/unit/test_reploom_crew.py -v
```

### Manual Testing

```bash
# 1. Start the LangGraph server
cd backend
langgraph dev --port 54367 --allow-blocking

# 2. Start the FastAPI server
fastapi dev app/main.py

# 3. Authenticate
curl http://localhost:8000/api/auth/login
# Follow OAuth flow

# 4. Test draft generation
curl -X POST http://localhost:8000/api/agents/reploom/run-draft \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=..." \
  -d '{
    "message_excerpt": "I need help resetting my password",
    "workspace_id": "test-workspace",
    "tone_level": "friendly"
  }'
```

## Usage Examples

### Example 1: Support Request

```python
{
  "message_excerpt": "The app keeps crashing when I try to export data",
  "workspace_id": "ws-acme",
  "tone_level": "friendly"
}

# Response:
{
  "intent": "support",
  "confidence": 0.95,
  "draft_html": "<p>Hi there!</p><p>I'm sorry to hear you're experiencing crashes when exporting data. Let me help you troubleshoot this...</p>",
  "violations": []
}
```

### Example 2: Customer Service with Blocklist

```python
{
  "message_excerpt": "What's your refund policy?",
  "workspace_id": "ws-acme",
  "tone_level": "formal",
  "blocklist": ["money back guarantee", "100% refund"]
}

# Response (with violation):
{
  "intent": "cs",
  "confidence": 0.88,
  "draft_html": "<p>Thank you for your inquiry. We offer a 30-day money back guarantee...</p>",
  "violations": ["Blocklisted phrase detected: 'money back guarantee'"]
}
```

### Example 3: Executive Inquiry

```python
{
  "message_excerpt": "I'm interested in discussing a partnership opportunity",
  "workspace_id": "ws-acme",
  "tone_level": "formal"
}

# Response:
{
  "intent": "exec",
  "confidence": 0.91,
  "draft_html": "<p>Dear [Name],</p><p>Thank you for reaching out regarding partnership opportunities. We would be pleased to discuss this further...</p>",
  "violations": []
}
```

## Future Enhancements

### Short-term (v1.1)

1. **PostgreSQL Checkpointer**
   - Migrate from MemorySaver to PostgresCheckpointer
   - Add checkpoint management API
   - Support workflow pause/resume

2. **Context Builder Implementation**
   - RAG retrieval from Qdrant
   - Workspace document search
   - Past conversation history

3. **Tone Verification**
   - LLM-based tone compliance check in policy guard
   - Automatic tone adjustment suggestions

### Medium-term (v1.2)

4. **Human-in-the-Loop**
   - Approval gates for low-confidence drafts
   - Manual edit and resume workflow
   - Feedback collection

5. **Workspace Configuration UI**
   - Admin panel for blocklist management
   - Tone preference settings
   - Approval threshold configuration

6. **Analytics & Monitoring**
   - Intent classification accuracy
   - Draft acceptance rate
   - Policy violation tracking

### Long-term (v2.0)

7. **Advanced Context**
   - CRM integration
   - Ticket history
   - Customer sentiment analysis

8. **Multi-language Support**
   - Automatic language detection
   - Translation capabilities

9. **Custom Agents per Intent**
   - Specialized drafter for each intent type
   - Intent-specific tools and context

## Known Limitations

1. **In-memory Checkpointer:** Runs are not persisted across server restarts
2. **No Context:** Context builder is a stub; drafts lack workspace-specific context
3. **Simple Tone Detection:** Relies on LLM prompt engineering, not verified
4. **Synchronous Execution:** No async streaming or background processing
5. **Single-turn:** No multi-turn conversations or clarification questions

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
