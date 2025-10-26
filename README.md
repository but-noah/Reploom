# Reploom: AI-Powered Multi-Agent Email Responder

Reploom is an intelligent email response system built with React (Vite) + LangGraph that generates high-quality email drafts using AI agents. With Gmail integration, human-in-the-loop workflows, and workspace-based brand voice management, Reploom helps teams respond faster while maintaining quality and control.

## Features

- **Gmail Integration:** Automated inbox scanning, email summarization, priority detection, and draft generation
- **Multi-Agent Architecture:** LangGraph-powered agent crews with workspace-specific configurations
- **Human-in-the-Loop:** Draft-only mode with confidence gates and review UI for safe, controlled responses
- **Calendar Management:** Smart scheduling, conflict detection, and meeting optimization
- **Document Intelligence:** PDF/text upload with RAG-powered context retrieval and sharing
- **Fine-Grained Authorization:** Auth0 FGA integration for workspace and tool-level access control
- **Secure API Access:** Auth0 Token Vault for credential-free tool calling
- **User Management:** Complete authentication with profile retrieval and workspace organization

## Quick Start (2 minutes)

### Prerequisites

- Node.js 18+ and npm/bun
- Python 3.12+
- Docker and Docker Compose
- Auth0 account ([sign up](https://auth0.com/signup))
- OpenAI API key ([get one](https://platform.openai.com/api-keys))

### 1. Clone and Install

```bash
git clone https://github.com/but-noah/Reploom.git
cd Reploom
```

### 2. Configure Backend

```bash
cd backend
cp .env.example .env
# Edit .env and add your Auth0 credentials and OpenAI API key
uv sync
docker compose up -d
source .venv/bin/activate
python -m app.core.fga_init
```

### 3. Start Services

```bash
# Terminal 1: FastAPI backend
fastapi dev app/main.py

# Terminal 2: LangGraph server
langgraph dev --port 54367 --allow-blocking

# Terminal 3: React frontend
cd frontend
cp .env.example .env
npm install && npm run dev
```

### 4. Access

Open http://localhost:5173 and start managing your emails with AI!

## Local Dev (Compose)

For a streamlined development experience, use the new one-command setup with Docker Compose and Make:

### Quick Setup

```bash
cd backend
make up          # Start postgres, redis, and qdrant with health checks
make migrate     # Initialize database schema
make dev         # Show dev server command
```

### Available Make Commands

```bash
make up          # Start all services (postgres, redis, qdrant)
make down        # Stop all services
make psql        # Connect to PostgreSQL database
make migrate     # Run database migrations
make seed        # Seed database with sample data (placeholder)
make logs        # Show logs from all services
make status      # Show status of all services
make restart     # Restart all services
make clean       # Stop services and remove volumes (deletes data!)
make help        # Show all available commands
```

### Services

The docker-compose stack includes:

- **PostgreSQL (pgvector)**: Main database with vector extension on port 5432
- **Redis**: Cache and session storage on port 6379
- **Qdrant**: Vector database for semantic search on ports 6333 (HTTP) and 6334 (gRPC)

All services include health checks and named volumes for data persistence.

### Health Check

Verify all services are running:

```bash
curl http://localhost:8000/healthz
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "postgres": "healthy",
    "redis": "configured",
    "qdrant": "healthy"
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                    │
│                   http://localhost:5173                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────┴────────────────────────────────────┐
│                 FastAPI Backend Server                      │
│                   http://localhost:8000                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Auth0 FGA  │  │  Auth Routes │  │  API Routes  │     │
│  │ Authorization│  │   & Session  │  │   (Agents)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│              LangGraph Agent Server                         │
│                   http://localhost:54367                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Email Agent  │  │ Calendar Agt │  │  RAG Agent   │     │
│  │   (Gmail)    │  │   (GCal)     │  │  (Qdrant)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────┬─────────────────────┬────────────────┬─────────────┘
        │                     │                │
┌───────┴────────┐   ┌────────┴──────┐   ┌────┴─────┐
│  Auth0 Token   │   │  PostgreSQL   │   │  Qdrant  │
│     Vault      │   │   Database    │   │  Vector  │
│ (OAuth Broker) │   │  + Redis      │   │    DB    │
└────────────────┘   └───────────────┘   └──────────┘
```

### Data Flow

1. **User Authentication:** Frontend → Auth0 → Backend (JWT verification)
2. **Agent Request:** Frontend → FastAPI → LangGraph Server
3. **Tool Execution:** Agent → Auth0 Token Vault → External APIs (Gmail, Calendar)
4. **Authorization:** Every action checked via Auth0 FGA policies
5. **Context Retrieval:** Agents query Qdrant for relevant documents

## Security with Auth0

Reploom leverages Auth0's modern identity platform for secure AI agent operations:

- **Token Vault:** Secure credential storage and scoped access token brokerage ([learn more](https://auth0.com/docs/secure/tokens/token-vault))
- **Federated Token Exchange:** Agents call tools via Auth0 without direct credential access
- **Fine-Grained Authorization (FGA):** Policy-based access control for workspaces, agents, and tools
- **OAuth 2.0 & OIDC:** Industry-standard authentication protocols

![Tool calling with Auth0 Token Vault](https://images.ctfassets.net/23aumh6u8s0i/1gY1jvDgZHSfRloc4qVumu/d44bb7102c1e858e5ac64dea324478fe/tool-calling-with-federated-api-token-exchange.jpg)

## Project Structure

```
Reploom/
├── backend/              # FastAPI + LangGraph Python backend
│   ├── app/
│   │   ├── agents/      # LangGraph agent definitions
│   │   ├── api/         # FastAPI route handlers
│   │   ├── core/        # Config, auth, database
│   │   └── tools/       # Agent tools (Gmail, Calendar, etc.)
│   ├── docker-compose.yml
│   └── pyproject.toml
├── frontend/            # React + Vite SPA
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── hooks/       # React hooks
│   │   └── lib/         # Utilities
│   └── package.json
└── public/              # Static assets
```

## Configuration

### Backend Environment Variables

See `backend/.env.example` for all configuration options including:
- Auth0 credentials (domain, client ID/secret)
- OpenAI API key
- Database URLs (PostgreSQL, Redis, Qdrant)
- FGA store configuration

### Frontend Environment Variables

See `frontend/.env.example` for frontend configuration (API host).

## Connect Gmail via Token Vault

Reploom uses **Auth0 Token Vault** to securely access Gmail on behalf of users without storing provider refresh tokens in the application database. This approach provides better security and compliance.

### Overview

The Gmail integration allows authenticated users to:
- List Gmail labels (`GET /api/me/gmail/labels`)
- Access Gmail data with proper scopes
- Maintain secure token management through Auth0

**Security Benefits:**
- ✅ No provider refresh tokens stored in your database
- ✅ Tokens obtained on-demand via Auth0's federated token exchange
- ✅ Automatic token rotation handled by Auth0
- ✅ Scoped access with minimal permissions (gmail.readonly, gmail.modify, gmail.compose)
- ✅ Comprehensive logging with PII redaction

### Required Auth0 Setup

#### 1. Enable Google Social Connection

1. Go to Auth0 Dashboard → **Authentication** → **Social**
2. Enable **Google** connection
3. Configure OAuth scopes:
   ```
   openid profile email
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/gmail.compose
   ```
4. Note your Google Client ID and Secret (from [Google Cloud Console](https://console.cloud.google.com/apis/credentials))

#### 2. Create Machine-to-Machine Application for Token Exchange

1. Go to Auth0 Dashboard → **Applications** → **Create Application**
2. Select **Machine to Machine Applications**
3. Name it "Reploom Token Exchange API"
4. Authorize it for **Auth0 Management API** with scope: `read:users`
5. Copy the **Client ID** and **Client Secret** (these are `AUTH0_CUSTOM_API_CLIENT_ID` and `AUTH0_CUSTOM_API_CLIENT_SECRET`)

#### 3. Configure Environment Variables

Add to your `backend/.env`:

```bash
# Auth0 Token Vault Configuration
AUTH0_CUSTOM_API_CLIENT_ID='your-m2m-client-id'
AUTH0_CUSTOM_API_CLIENT_SECRET='your-m2m-client-secret'
AUTH0_AUDIENCE='https://your-tenant.auth0.com/api/v2/'

# Gmail API Scopes (space-separated)
GMAIL_SCOPES='https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.compose'
```

### Testing the Integration

#### 1. Test Authentication Flow

```bash
# Start the backend
cd backend
fastapi dev app/main.py

# In another terminal, authenticate
curl http://localhost:8000/api/auth/login
```

Log in with a Google account and grant the requested Gmail permissions.

#### 2. Test Gmail Labels Endpoint

```bash
# After authentication, call the labels endpoint
curl http://localhost:8000/api/me/gmail/labels \
  -H "Cookie: auth0_session=..." \
  --cookie-jar cookies.txt --cookie cookies.txt
```

Expected response:

```json
{
  "labels": [
    {
      "id": "INBOX",
      "name": "INBOX",
      "type": "system",
      "messageListVisibility": "show",
      "labelListVisibility": "labelShow"
    },
    {
      "id": "SENT",
      "name": "SENT",
      "type": "system"
    }
  ],
  "scope": [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose"
  ],
  "user": {
    "sub": "google-oauth2|123456",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### Error Handling

The Gmail integration provides detailed error messages:

| Status Code | Error | Description |
|-------------|-------|-------------|
| 401 | `invalid_grant` | User's Google authorization expired or revoked. Reconnect Gmail. |
| 403 | `insufficient_scope` | User didn't grant required Gmail permissions. Re-authenticate. |
| 429 | `rate_limit_exceeded` | Gmail API quota exhausted. Wait and retry. |
| 500 | `token_exchange_error` | Auth0 configuration issue. Check logs. |
| 503 | `service_unavailable` | Gmail API temporarily down. Retry later. |
| 504 | `timeout` | Request took too long. Retry. |

### Security Considerations

1. **No Token Logging:** Access tokens are never logged or exposed in API responses
2. **Redacted Logs:** User identifiers are truncated in logs (e.g., `auth0|123...`)
3. **Minimal Scopes:** Only request the scopes your application actually needs
4. **Token Lifetime:** Tokens are short-lived and obtained on-demand
5. **Error Messages:** User-friendly messages don't leak sensitive information

### Architecture

```
User Request
     ↓
FastAPI (/api/me/gmail/labels)
     ↓
Token Exchange Helper (token_exchange.py)
     ↓
Auth0 Token Vault (OAuth Token Exchange)
     ↓
Google OAuth2 (Access Token)
     ↓
Gmail API (users.labels.list)
     ↓
Response to User
```

### Extending to Other Google APIs

To add more Google services:

1. Add required scopes to `GMAIL_SCOPES` in `.env`
2. Re-authenticate users to grant new permissions
3. Use the same `get_google_access_token()` helper
4. Create new route handlers in `app/api/routes/`

Example for Google Calendar:

```python
# In your route handler
from app.auth.token_exchange import get_google_access_token

access_token = await get_google_access_token(
    user_sub=user["sub"],
    scopes=["https://www.googleapis.com/auth/calendar.readonly"]
)

# Use token with Google Calendar API
```

### Troubleshooting

**Issue:** `Token exchange service is not configured`

**Solution:** Verify all required environment variables are set:
- `AUTH0_DOMAIN`
- `AUTH0_CUSTOM_API_CLIENT_ID`
- `AUTH0_CUSTOM_API_CLIENT_SECRET`
- `AUTH0_AUDIENCE`

**Issue:** `User has not granted required Gmail permissions`

**Solution:** User needs to:
1. Log out from Reploom
2. Log in again with Google
3. Grant all requested Gmail permissions on the consent screen

**Issue:** `Grant is invalid or expired`

**Solution:** User's Google connection expired. They need to reconnect their Google account via Auth0.

## Learn More

- [Auth0 Token Vault Concept](https://auth0.com/docs/secure/tokens/token-vault) - Secure credential management
- [Tool Calling in AI Agents](https://auth0.com/blog/genai-tool-calling-intro/) - Security best practices
- [Build an AI Assistant with LangGraph](https://auth0.com/blog/genai-tool-calling-build-agent-that-calls-gmail-securely-with-langgraph-vercelai-nextjs/)
- [Auth for GenAI Documentation](https://auth0.com/ai/docs)

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

This project uses pre-commit hooks for code quality:
- Python: ruff (linting) + black (formatting)
- TypeScript/JavaScript: eslint + prettier

## Roadmap

- [ ] Microsoft 365 / Outlook integration
- [ ] IMAP/SMTP support for custom email providers
- [ ] Advanced sequencing and workflow automation
- [ ] Multi-language support
- [ ] Mobile app (React Native)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors

Built by [Juan Cruz Martinez](https://github.com/jcmartinezdev), [Deepu K Sasidharan](https://github.com/deepu105), and contributors.

Rebranded and enhanced by the Reploom team.
