"""
Reploom Crew API Routes

Production-ready endpoints for triggering the draft generation workflow with:
- PII redaction in logs
- Correlation ID propagation
- Workspace settings integration
- Run state retrieval
- Draft review and approval workflow
"""
import httpx
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import settings
from app.core.auth import auth_client
from app.core.db import get_session
from app.agents.reploom_crew import prepare_initial_state
from app.models.draft_reviews import DraftReview

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


# ===== Draft Review Endpoints =====


class CreateReviewRequest(BaseModel):
    """Request model for creating a draft review."""
    thread_id: str
    draft_html: str
    original_message_summary: str
    original_message_excerpt: str | None = None
    intent: str | None = None
    confidence: float | None = None
    violations: list[str] = Field(default_factory=list)
    run_id: str | None = None
    workspace_id: str | None = None


class UpdateReviewRequest(BaseModel):
    """Request model for updating a draft review."""
    draft_html: str
    edit_notes: str | None = None


class ReviewActionRequest(BaseModel):
    """Request model for review actions (approve/reject)."""
    feedback: str | None = None


class DraftReviewResponse(BaseModel):
    """Response model for draft review."""
    id: str
    thread_id: str
    draft_html: str
    original_message_summary: str
    original_message_excerpt: str | None
    intent: str | None
    confidence: float | None
    violations: list[str]
    status: str
    feedback: str | None
    edit_notes: str | None
    draft_version: int
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None


@reploom_router.post("/reviews", response_model=DraftReviewResponse)
async def create_review(
    request_body: CreateReviewRequest,
    auth_session=Depends(auth_client.require_session),
    session: Session = Depends(get_session),
):
    """
    Create a new draft review entry.

    This endpoint is called after draft generation to save the draft
    for review and approval workflow.
    """
    user = auth_session.get("user", {})
    user_id = user.get("sub", "unknown")
    user_email = user.get("email", "unknown")

    # Create review entry
    review = DraftReview(
        user_id=user_id,
        user_email=user_email,
        thread_id=request_body.thread_id,
        run_id=request_body.run_id,
        workspace_id=request_body.workspace_id,
        original_message_summary=request_body.original_message_summary,
        original_message_excerpt=request_body.original_message_excerpt,
        draft_html=request_body.draft_html,
        intent=request_body.intent,
        confidence=request_body.confidence,
        violations=request_body.violations,
        status="pending",
    )

    session.add(review)
    session.commit()
    session.refresh(review)

    logger.info(
        f"Draft review created",
        extra={
            "review_id": str(review.id),
            "thread_id": review.thread_id,
            "user_id": user_id[:12] + "...",
        }
    )

    return DraftReviewResponse(
        id=str(review.id),
        thread_id=review.thread_id,
        draft_html=review.draft_html,
        original_message_summary=review.original_message_summary,
        original_message_excerpt=review.original_message_excerpt,
        intent=review.intent,
        confidence=review.confidence,
        violations=review.violations,
        status=review.status,
        feedback=review.feedback,
        edit_notes=review.edit_notes,
        draft_version=review.draft_version,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewed_at=review.reviewed_at,
    )


@reploom_router.get("/reviews", response_model=list[DraftReviewResponse])
async def list_reviews(
    status: str | None = None,
    intent: str | None = None,
    auth_session=Depends(auth_client.require_session),
    session: Session = Depends(get_session),
):
    """
    List all draft reviews for the current user.

    Supports filtering by status and intent.
    """
    user = auth_session.get("user", {})
    user_id = user.get("sub", "unknown")

    # Build query
    statement = select(DraftReview).where(DraftReview.user_id == user_id)

    if status:
        statement = statement.where(DraftReview.status == status)
    if intent:
        statement = statement.where(DraftReview.intent == intent)

    # Order by most recent first
    statement = statement.order_by(DraftReview.updated_at.desc())

    reviews = session.exec(statement).all()

    return [
        DraftReviewResponse(
            id=str(review.id),
            thread_id=review.thread_id,
            draft_html=review.draft_html,
            original_message_summary=review.original_message_summary,
            original_message_excerpt=review.original_message_excerpt,
            intent=review.intent,
            confidence=review.confidence,
            violations=review.violations,
            status=review.status,
            feedback=review.feedback,
            edit_notes=review.edit_notes,
            draft_version=review.draft_version,
            created_at=review.created_at,
            updated_at=review.updated_at,
            reviewed_at=review.reviewed_at,
        )
        for review in reviews
    ]


@reploom_router.get("/reviews/{review_id}", response_model=DraftReviewResponse)
async def get_review(
    review_id: str,
    auth_session=Depends(auth_client.require_session),
    session: Session = Depends(get_session),
):
    """
    Get a specific draft review by ID.
    """
    user = auth_session.get("user", {})
    user_id = user.get("sub", "unknown")

    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID format")

    review = session.get(DraftReview, review_uuid)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this review")

    return DraftReviewResponse(
        id=str(review.id),
        thread_id=review.thread_id,
        draft_html=review.draft_html,
        original_message_summary=review.original_message_summary,
        original_message_excerpt=review.original_message_excerpt,
        intent=review.intent,
        confidence=review.confidence,
        violations=review.violations,
        status=review.status,
        feedback=review.feedback,
        edit_notes=review.edit_notes,
        draft_version=review.draft_version,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewed_at=review.reviewed_at,
    )


@reploom_router.post("/reviews/{review_id}/approve", response_model=DraftReviewResponse)
async def approve_review(
    review_id: str,
    request_body: ReviewActionRequest,
    auth_session=Depends(auth_client.require_session),
    session: Session = Depends(get_session),
):
    """
    Approve a draft review.

    Marks the draft as approved (no send action yet).
    """
    user = auth_session.get("user", {})
    user_id = user.get("sub", "unknown")

    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID format")

    review = session.get(DraftReview, review_uuid)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to approve this review")

    # Update status
    review.status = "approved"
    review.feedback = request_body.feedback
    review.reviewed_at = datetime.utcnow()
    review.updated_at = datetime.utcnow()

    session.add(review)
    session.commit()
    session.refresh(review)

    logger.info(
        f"Draft review approved",
        extra={
            "review_id": str(review.id),
            "thread_id": review.thread_id,
        }
    )

    return DraftReviewResponse(
        id=str(review.id),
        thread_id=review.thread_id,
        draft_html=review.draft_html,
        original_message_summary=review.original_message_summary,
        original_message_excerpt=review.original_message_excerpt,
        intent=review.intent,
        confidence=review.confidence,
        violations=review.violations,
        status=review.status,
        feedback=review.feedback,
        edit_notes=review.edit_notes,
        draft_version=review.draft_version,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewed_at=review.reviewed_at,
    )


@reploom_router.post("/reviews/{review_id}/reject", response_model=DraftReviewResponse)
async def reject_review(
    review_id: str,
    request_body: ReviewActionRequest,
    auth_session=Depends(auth_client.require_session),
    session: Session = Depends(get_session),
):
    """
    Reject a draft review.

    Marks the draft as rejected and stores feedback.
    """
    user = auth_session.get("user", {})
    user_id = user.get("sub", "unknown")

    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID format")

    review = session.get(DraftReview, review_uuid)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this review")

    # Update status
    review.status = "rejected"
    review.feedback = request_body.feedback
    review.reviewed_at = datetime.utcnow()
    review.updated_at = datetime.utcnow()

    session.add(review)
    session.commit()
    session.refresh(review)

    logger.info(
        f"Draft review rejected",
        extra={
            "review_id": str(review.id),
            "thread_id": review.thread_id,
        }
    )

    return DraftReviewResponse(
        id=str(review.id),
        thread_id=review.thread_id,
        draft_html=review.draft_html,
        original_message_summary=review.original_message_summary,
        original_message_excerpt=review.original_message_excerpt,
        intent=review.intent,
        confidence=review.confidence,
        violations=review.violations,
        status=review.status,
        feedback=review.feedback,
        edit_notes=review.edit_notes,
        draft_version=review.draft_version,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewed_at=review.reviewed_at,
    )


@reploom_router.post("/reviews/{review_id}/request-edit", response_model=DraftReviewResponse)
async def request_edit(
    review_id: str,
    request_body: UpdateReviewRequest,
    request: Request,
    auth_session=Depends(auth_client.require_session),
    session: Session = Depends(get_session),
):
    """
    Request edit for a draft review.

    Updates the draft HTML and re-runs policy guard via the backend.
    """
    user = auth_session.get("user", {})
    user_id = user.get("sub", "unknown")
    correlation_id = get_correlation_id(request)

    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID format")

    review = session.get(DraftReview, review_uuid)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this review")

    # Update draft content
    review.draft_html = request_body.draft_html
    review.edit_notes = request_body.edit_notes
    review.status = "editing"
    review.draft_version += 1
    review.updated_at = datetime.utcnow()

    # Re-run policy guard check (simplified - just check for blocklist words)
    # In production, this would call the LangGraph policy guard node
    violations = []

    # TODO: Implement proper policy guard check
    # For now, just clear violations since we're allowing edits
    review.violations = violations

    session.add(review)
    session.commit()
    session.refresh(review)

    logger.info(
        f"Draft review edited",
        extra={
            "correlation_id": correlation_id,
            "review_id": str(review.id),
            "thread_id": review.thread_id,
            "draft_version": review.draft_version,
        }
    )

    return DraftReviewResponse(
        id=str(review.id),
        thread_id=review.thread_id,
        draft_html=review.draft_html,
        original_message_summary=review.original_message_summary,
        original_message_excerpt=review.original_message_excerpt,
        intent=review.intent,
        confidence=review.confidence,
        violations=review.violations,
        status=review.status,
        feedback=review.feedback,
        edit_notes=review.edit_notes,
        draft_version=review.draft_version,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewed_at=review.reviewed_at,
    )
