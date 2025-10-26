"""
Reploom Crew API Routes

Endpoints for triggering the draft generation workflow.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.auth import auth_client

reploom_router = APIRouter(prefix="/agents/reploom", tags=["reploom"])


class RunDraftRequest(BaseModel):
    """Request model for running draft generation."""
    thread_id: str | None = Field(None, description="Thread ID for resumable execution")
    message_excerpt: str = Field(..., description="Summary or excerpt of the incoming message")
    workspace_id: str | None = Field(None, description="Workspace identifier")
    tone_level: str = Field("friendly", description="Tone level: formal, friendly, or casual")
    blocklist: list[str] | None = Field(None, description="List of disallowed phrases")


class RunDraftResponse(BaseModel):
    """Response model for draft generation."""
    draft_html: str | None = Field(None, description="Generated HTML draft")
    confidence: float | None = Field(None, description="Confidence score for intent classification")
    intent: str | None = Field(None, description="Detected intent: support, cs, exec, or other")
    violations: list[str] = Field(default_factory=list, description="Policy violations if any")
    thread_id: str = Field(..., description="Thread ID used for this run")


@reploom_router.post("/run-draft", response_model=RunDraftResponse)
async def run_draft(
    request: RunDraftRequest,
    auth_session=Depends(auth_client.require_session)
):
    """
    Trigger the Reploom draft generation workflow.

    This endpoint calls the LangGraph server to run the reploom-crew workflow
    which includes:
    1. Intent classification
    2. Context building (stub)
    3. Draft generation with tone control
    4. Policy enforcement (blocklist checking)

    The workflow is resumable via the thread_id parameter, allowing for
    human-in-the-loop interventions.

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/reploom/run-draft \\
          -H "Content-Type: application/json" \\
          -H "Cookie: auth0_session=..." \\
          -d '{
            "thread_id": "customer-123-msg-456",
            "message_excerpt": "I need help resetting my password",
            "workspace_id": "ws-acme-corp",
            "tone_level": "friendly"
          }'
        ```
    """
    try:
        # Use provided thread_id or generate one
        thread_id = request.thread_id or f"thread-{auth_session.get('user', {}).get('sub', 'unknown')}-{hash(request.message_excerpt) % 10000}"

        # Build the LangGraph API request
        langgraph_url = f"{settings.LANGGRAPH_API_URL}/threads/{thread_id}/runs/wait"

        # Prepare the input for the reploom-crew graph
        input_data = {
            "original_message_summary": request.message_excerpt,
            "workspace_id": request.workspace_id,
            "tone_level": request.tone_level,
            "blocklist": request.blocklist,
            "intent": None,
            "confidence": None,
            "context_snippets": [],
            "draft_html": None,
            "violations": [],
        }

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
        }
        if settings.LANGGRAPH_API_KEY:
            headers["x-api-key"] = settings.LANGGRAPH_API_KEY

        # Make the request to LangGraph server
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                langgraph_url,
                json={
                    "assistant_id": "reploom-crew",
                    "input": input_data,
                    "config": {
                        "configurable": {
                            "_credentials": {
                                "access_token": auth_session.get("token_sets", [{}])[0].get("access_token"),
                                "refresh_token": auth_session.get("refresh_token"),
                                "user": auth_session.get("user"),
                            }
                        }
                    },
                    "stream_mode": "values",
                },
                headers=headers,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LangGraph server error: {response.text}"
                )

            # Parse the response
            result = response.json()

            # Extract the final state from the response
            # LangGraph returns the last state in the response
            final_state = result

            return RunDraftResponse(
                draft_html=final_state.get("draft_html"),
                confidence=final_state.get("confidence"),
                intent=final_state.get("intent"),
                violations=final_state.get("violations", []),
                thread_id=thread_id,
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to LangGraph server: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@reploom_router.get("/health")
async def health_check():
    """
    Health check endpoint to verify the reploom crew is available.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.LANGGRAPH_API_URL}/ok")
            if response.status_code == 200:
                return {"status": "healthy", "langgraph_server": "connected"}
            else:
                return {"status": "degraded", "langgraph_server": "error"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
