# Setup the backend

```bash
cd backend
```

You'll need to set up environment variables in your repo's `.env` file. Copy the `.env.example` file to `.env`.

To start with the basic examples, you'll just need to add your OpenAI API key and Auth0 credentials.

- To start with the examples, you'll just need to add your OpenAI API key and Auth0 credentials for the Web app.
  - You can setup a new Auth0 tenant with an Auth0 Web App and Token Vault following the Prerequisites instructions [here](https://auth0.com/ai/docs/call-others-apis-on-users-behalf).
  - An Auth0 FGA account, you can create one [here](https://dashboard.fga.dev). Add the FGA store ID, client ID, client secret, and API URL to the `.env` file.

Next, install the required packages using your preferred package manager, e.g. uv:

```bash
uv sync
```

Now you're ready to start and migrate the database:

```bash
# start the postgres database
docker compose up -d
```

Initialize FGA store:

```bash
source .venv/bin/activate
python -m app.core.fga_init
```

Now you're ready to run the development server:

```bash
source .venv/bin/activate
fastapi dev app/main.py
```

Next, you'll need to start an in-memory LangGraph server on port 54367, to do so open a new terminal and run:

```bash
source .venv/bin/activate
uv pip install -U langgraph-api
langgraph dev --port 54367 --allow-blocking
```

## Observability

The Reploom backend includes OpenTelemetry tracing to provide visibility into the critical path:
- **Token Exchange**: Auth0 Token Vault integration for Google API access
- **Gmail Operations**: List labels, fetch threads, create drafts
- **LangGraph Runs**: Draft generation with intent classification and confidence scoring

### Tracing Modes

The application supports multiple tracing export modes via the `OTEL_TRACES_EXPORTER` environment variable:

#### 1. Console Mode (Default - Development)
Traces are printed to stdout for local debugging:

```bash
# In your .env file or environment
OTEL_TRACES_EXPORTER=console
```

Then run your backend and trigger a draft generation. You'll see trace output in the console with:
- Span names (e.g., `token_exchange.get_google_access_token`, `gmail.create_reply_draft`, `langgraph.run_draft`)
- Attributes (e.g., `draft.intent=support`, `draft.confidence=0.95`)
- Status and timing information

#### 2. OTLP Mode (Production - Jaeger/Tempo)
Export traces to an OTLP collector for visualization:

```bash
# In your .env file
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**Enable Jaeger UI** (easiest option for local development):
1. Uncomment the `jaeger` service in `docker-compose.yml`
2. Restart docker compose: `docker compose up -d`
3. View traces at http://localhost:16686

**Using Jaeger:**
1. Open http://localhost:16686 in your browser
2. Select "reploom-backend" from the Service dropdown
3. Click "Find Traces" to see recent traces
4. Click on a trace to see the full span tree with:
   - Token exchange → Gmail operations → LangGraph execution
   - Intent and confidence attributes on draft generation spans
   - Error details if operations failed

#### 3. Disable Tracing
```bash
OTEL_TRACES_EXPORTER=none
```

### Key Trace Attributes

The following business-level attributes are captured in traces:

**LangGraph Draft Generation** (`langgraph.run_draft`):
- `draft.intent`: Detected intent (support, cs, exec, other)
- `draft.confidence`: Classification confidence score (0.0 - 1.0)
- `draft.has_violations`: Boolean indicating policy violations
- `thread_id`: Unique thread identifier
- `run_id`: Unique run identifier

**Gmail Operations**:
- `thread_id`: Gmail thread ID
- `draft_id`: Created draft ID
- `message_count`: Number of messages in thread

**Token Exchange**:
- `scopes_count`: Number of OAuth scopes requested
- `provider`: API provider (e.g., "google")
- `token_type`: Token type (e.g., "Bearer")
- `expires_in_seconds`: Token expiration time

### Security & Privacy

All traces are sanitized to prevent PII exposure:
- **Tokens & Secrets**: Automatically masked (shows first 8 and last 4 chars only)
- **Email Addresses**: Masked to show only first char and domain
- **Message Bodies**: Truncated and sanitized (max 100 chars)

### Example Trace Flow

A typical draft generation request creates this trace hierarchy:

```
langgraph.run_draft (root span)
├── token_exchange.get_google_access_token
│   └── HTTP POST to auth0.com/oauth/token
├── gmail.get_thread
│   └── HTTP GET to gmail.googleapis.com/gmail/v1/users/me/threads/{id}
├── gmail.create_reply_draft
│   ├── HTTP GET to gmail.googleapis.com/gmail/v1/users/me/messages/{id}
│   └── HTTP POST to gmail.googleapis.com/gmail/v1/users/me/drafts
└── HTTP POST to langgraph-server (draft generation)
```

### Troubleshooting

**No traces appearing in Jaeger:**
- Verify `OTEL_TRACES_EXPORTER=otlp` is set
- Check Jaeger is running: `docker ps | grep jaeger`
- Ensure endpoint is correct: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`

**Traces in console but not in Jaeger:**
- Check the OTLP endpoint is reachable
- Look for connection errors in backend logs

**Missing span attributes:**
- Ensure you're using the latest code with full tracing implementation
- Check that the operation completed successfully (failed ops may have incomplete attributes)
