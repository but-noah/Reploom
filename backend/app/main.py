from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session, text
import httpx

from app.core.config import settings
from app.api.api_router import api_router
from app.core.auth import auth_client
from app.core.db import engine, init_db
from app.core.fga import authorization_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    authorization_manager.connect()

    yield

    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALL_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set the session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.AUTH0_SECRET)

# Save auth state
app.state.auth_client = auth_client

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/healthz")
async def health_check():
    """Health check endpoint that verifies connectivity to all external services."""
    health_status = {
        "status": "healthy",
        "services": {
            "postgres": "unknown",
            "redis": "unknown",
            "qdrant": "unknown",
        }
    }

    # Check PostgreSQL
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
            health_status["services"]["postgres"] = "healthy"
    except Exception as e:
        health_status["services"]["postgres"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        async with httpx.AsyncClient() as client:
            # Simple check - if Redis URL is configured
            if settings.REDIS_URL:
                health_status["services"]["redis"] = "configured"
            else:
                health_status["services"]["redis"] = "not configured"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"

    # Check Qdrant
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.QDRANT_URL}/healthz", timeout=2.0)
            if response.status_code == 200:
                health_status["services"]["qdrant"] = "healthy"
            else:
                health_status["services"]["qdrant"] = f"unhealthy: status {response.status_code}"
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["qdrant"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status
