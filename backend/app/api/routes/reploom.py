"""
Reploom Crew API Routes

Production-ready endpoints for triggering the draft generation workflow with:
- PII redaction in logs
- Correlation ID propagation
- Workspace settings integration
- Run state retrieval
"""
import httpx
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.auth import auth_client
from app.agents.reploom_crew import prepare_initial_state

logger = logging.getLogger(__name__)

reploom_router = APIRouter(prefix="/agents/reploom", tags=["reploom"])


def get_correlation_id(request: Request) -> str:
    """Extract or generate correlation ID for request tracking."""
    correlation_id = request.headers.get("x-correlation-id")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    return correlation_id


def redact_user_info(user: dict) -> dict:
    """Redact PII from user info for logging."""
    if not user:
        return {}
    return {
        "sub": user.get("sub", "")[:12] + "...",  # Truncate user ID
        "email": "***@***",  # Fully redact email
    }


class RunDraftRequest(BaseModel):
    """Request model for running draft generation."""
    thread_id: str | None = Field(None, description="Thread ID for resumable execution")
    message_excerpt: str = Field(..., description="Summary or excerpt of the incoming message")
    workspace_id: str | None = Field(None, description="Workspace identifier")


class RunDraftResponse(BaseModel):
    """Response model for draft generation."""
    draft_html: str | None = Field(None, description="Generated HTML draft")
    confidence: float | None = Field(None, description="Confidence score for intent classification")
    intent: str | None = Field(None, description="Detected intent: support, cs, exec, or other")
    violations: list[str] = Field(default_factory=list, description="Policy violations if any")
    thread_id: str = Field(..., description="Thread ID used for this run")
    run_id: str = Field(..., description="Unique run identifier")


class RunStateResponse(BaseModel):
    """Response model for fetching run state."""
    state: dict = Field(..., description="Current state of the run")
    status: str = Field(..., description="Run status: completed, failed, or running")
    thread_id: str = Field(..., description="Thread ID")


@reploom_router.post("/run-draft", response_model=RunDraftResponse)
async def run_draft(
    request_body: RunDraftRequest,
    request: Request,
    auth_session=Depends(auth_client.require_session)
):
    """
    Trigger the Reploom draft generation workflow.

    This endpoint calls the LangGraph server to run the reploom-crew workflow
    which includes:
    1. Intent classification
    2. Context building (stub)
    3. Draft generation with tone control
    4. Policy enforcement (blocklist checking from workspace settings)

    The workflow is resumable via the thread_id parameter, allowing for
    human-in-the-loop interventions.

    Security:
    - PII is redacted from logs
    - Correlation ID is propagated for request tracking
    - Workspace settings are loaded from database

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/reploom/run-draft \\
          -H "Content-Type: application/json" \\
          -H "Cookie: auth0_session=..." \\
          -H "x-correlation-id: req-12345" \\
          -d '{
            "thread_id": "customer-123-msg-456",
            "message_excerpt": "I need help resetting my password",
            "workspace_id": "ws-acme-corp"
          }'
        ```
    """
    # Generate correlation ID
    correlation_id = get_correlation_id(request)

    # Extract user info with PII redaction
    user = auth_session.get("user", {})
    user_sub = user.get("sub", "unknown")

    # Log request with PII redaction
    logger.info(
        f"Draft generation requested",
        extra={
            "correlation_id": correlation_id,
            "user": redact_user_info(user),
            "workspace_id": request_body.workspace_id or "default",
            "message_length": len(request_body.message_excerpt),
        }
    )

    try:
        # Generate thread ID if not provided
        thread_id = request_body.thread_id or f"thread-{user_sub[:8]}-{uuid.uuid4().hex[:8]}"

        # Prepare initial state (loads workspace settings)
        initial_state = prepare_initial_state(
            message_summary=request_body.message_excerpt,
            workspace_id=request_body.workspace_id,
            thread_id=thread_id,
        )

        # Build the LangGraph API request
        langgraph_url = f"{settings.LANGGRAPH_API_URL}/threads/{thread_id}/runs/wait"

        # Prepare headers with correlation ID
        headers = {
            "Content-Type": "application/json",
            "x-correlation-id": correlation_id,
        }
        if settings.LANGGRAPH_API_KEY:
            headers["x-api-key"] = settings.LANGGRAPH_API_KEY

        # Make the request to LangGraph server
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                langgraph_url,
                json={
                    "assistant_id": "reploom-crew",
                    "input": initial_state,
                    "config": {
                        "configurable": {
                            "thread_id": thread_id,
                            "_credentials": {
                                "access_token": auth_session.get("token_sets", [{}])[0].get("access_token"),
                                "refresh_token": auth_session.get("refresh_token"),
                                "user": user,
                            }
                        }
                    },
                    "stream_mode": "values",
                },
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(
                    f"LangGraph server error",
                    extra={
                        "correlation_id": correlation_id,
                        "status_code": response.status_code,
                        "error": response.text[:200],  # Truncate error
                    }
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LangGraph server error: {response.status_code}"
                )

            # Parse the response
            result = response.json()

            # Extract run ID from response
            run_id = str(uuid.uuid4())  # Fallback
            if isinstance(result, dict):
                run_id = result.get("run_id", run_id)

            # Log successful completion
            logger.info(
                f"Draft generation completed",
                extra={
                    "correlation_id": correlation_id,
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "intent": result.get("intent"),
                    "confidence": result.get("confidence"),
                    "has_violations": bool(result.get("violations")),
                }
            )

            return RunDraftResponse(
                draft_html=result.get("draft_html"),
                confidence=result.get("confidence"),
                intent=result.get("intent"),
                violations=result.get("violations", []),
                thread_id=thread_id,
                run_id=run_id,
            )

    except httpx.RequestError as e:
        logger.error(
            f"Failed to connect to LangGraph server",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to LangGraph server: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Internal server error",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@reploom_router.get("/runs/{thread_id}", response_model=RunStateResponse)
async def get_run_state(
    thread_id: str,
    request: Request,
    auth_session=Depends(auth_client.require_session)
):
    """
    Fetch the current state of a run by thread ID.

    This endpoint retrieves the saved state from the checkpointer,
    allowing for inspection of draft generation progress and results.

    Useful for:
    - Review UI to display draft details
    - Debugging workflow execution
    - Human-in-the-loop decision points

    Example:
        ```bash
        curl http://localhost:8000/api/agents/reploom/runs/thread-abc123 \\
          -H "Cookie: auth0_session=..." \\
          -H "x-correlation-id: req-12345"
        ```
    """
    correlation_id = get_correlation_id(request)

    logger.info(
        f"Fetching run state",
        extra={
            "correlation_id": correlation_id,
            "thread_id": thread_id,
        }
    )

    try:
        # Build the LangGraph API request to fetch state
        langgraph_url = f"{settings.LANGGRAPH_API_URL}/threads/{thread_id}/state"

        headers = {
            "x-correlation-id": correlation_id,
        }
        if settings.LANGGRAPH_API_KEY:
            headers["x-api-key"] = settings.LANGGRAPH_API_KEY

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(langgraph_url, headers=headers)

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Run not found for thread_id: {thread_id}"
                )

            if response.status_code != 200:
                logger.error(
                    f"LangGraph server error",
                    extra={
                        "correlation_id": correlation_id,
                        "status_code": response.status_code,
                    }
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LangGraph server error: {response.status_code}"
                )

            # Parse the response
            result = response.json()

            # Determine status from state
            state = result.get("values", {})
            violations = state.get("violations", [])
            draft_html = state.get("draft_html")

            if violations:
                status = "failed"
            elif draft_html:
                status = "completed"
            else:
                status = "running"

            logger.info(
                f"Fetched run state",
                extra={
                    "correlation_id": correlation_id,
                    "thread_id": thread_id,
                    "status": status,
                }
            )

            return RunStateResponse(
                state=state,
                status=status,
                thread_id=thread_id,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to fetch run state",
            extra={
                "correlation_id": correlation_id,
                "thread_id": thread_id,
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch run state: {str(e)}"
        )


@reploom_router.get("/health")
async def health_check():
    """
    Health check endpoint to verify the reploom crew is available.

    Returns:
        Status of LangGraph server and checkpointer configuration
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.LANGGRAPH_API_URL}/ok")

            checkpointer_status = settings.GRAPH_CHECKPOINTER

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "langgraph_server": "connected",
                    "checkpointer": checkpointer_status,
                }
            else:
                return {
                    "status": "degraded",
                    "langgraph_server": "error",
                    "checkpointer": checkpointer_status,
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "checkpointer": settings.GRAPH_CHECKPOINTER,
        }
