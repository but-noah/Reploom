"""Analytics API routes for metrics and summary data."""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, and_, or_, case

from app.core.db import get_session
from app.models.draft_reviews import DraftReview

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Default SLA threshold in seconds (5 minutes)
DEFAULT_SLA_THRESHOLD_SECONDS = 300


def parse_window(window: str) -> timedelta:
    """Parse window parameter into timedelta."""
    if window == "7d":
        return timedelta(days=7)
    elif window == "30d":
        return timedelta(days=30)
    else:
        raise ValueError(f"Invalid window: {window}. Must be '7d' or '30d'")


def calculate_metrics(
    reviews: list[DraftReview],
    sla_threshold_seconds: int = DEFAULT_SLA_THRESHOLD_SECONDS,
) -> dict[str, Any]:
    """Calculate analytics metrics from review data.

    Args:
        reviews: List of DraftReview objects
        sla_threshold_seconds: SLA threshold in seconds (default: 300 = 5 minutes)

    Returns:
        Dictionary containing:
        - intents_count: {intent: count}
        - review_rate: {approved, rejected, editing, pending} counts and percentages
        - frt_seconds: {avg, median, min, max, sla_met_count, sla_met_percentage}
    """
    total_count = len(reviews)

    # 1. Intents count
    intents_count: dict[str, int] = {}
    for review in reviews:
        intent = review.intent or "unknown"
        intents_count[intent] = intents_count.get(intent, 0) + 1

    # 2. Review rate by status
    status_counts = {"approved": 0, "rejected": 0, "editing": 0, "pending": 0}
    for review in reviews:
        status = review.status
        if status in status_counts:
            status_counts[status] += 1

    review_rate = {
        "total": total_count,
        "approved": status_counts["approved"],
        "rejected": status_counts["rejected"],
        "editing": status_counts["editing"],
        "pending": status_counts["pending"],
        "approved_rate": (status_counts["approved"] / total_count * 100) if total_count > 0 else 0,
        "rejected_rate": (status_counts["rejected"] / total_count * 100) if total_count > 0 else 0,
        "editing_rate": (status_counts["editing"] / total_count * 100) if total_count > 0 else 0,
        "pending_rate": (status_counts["pending"] / total_count * 100) if total_count > 0 else 0,
    }

    # 3. First Response Time (FRT) - time from created_at to first review action
    frt_times: list[float] = []
    sla_met_count = 0

    for review in reviews:
        # FRT is the time from creation to first review action (reviewed_at or updated_at if status changed)
        if review.status != "pending":
            # Use reviewed_at if available, otherwise use updated_at
            response_time = review.reviewed_at or review.updated_at
            if response_time and review.created_at:
                frt = (response_time - review.created_at).total_seconds()
                if frt >= 0:  # Sanity check
                    frt_times.append(frt)
                    if frt <= sla_threshold_seconds:
                        sla_met_count += 1

    # Calculate FRT statistics
    frt_metrics = {
        "avg_seconds": sum(frt_times) / len(frt_times) if frt_times else 0,
        "median_seconds": sorted(frt_times)[len(frt_times) // 2] if frt_times else 0,
        "min_seconds": min(frt_times) if frt_times else 0,
        "max_seconds": max(frt_times) if frt_times else 0,
        "sla_threshold_seconds": sla_threshold_seconds,
        "sla_met_count": sla_met_count,
        "sla_met_percentage": (sla_met_count / len(frt_times) * 100) if frt_times else 0,
        "total_with_frt": len(frt_times),
    }

    return {
        "intents_count": intents_count,
        "review_rate": review_rate,
        "frt": frt_metrics,
    }


@router.get("/summary")
async def get_analytics_summary(
    window: Literal["7d", "30d"] = Query("7d", description="Time window for analytics"),
    workspace_id: str | None = Query(None, description="Filter by workspace ID"),
    sla_threshold_seconds: int = Query(
        DEFAULT_SLA_THRESHOLD_SECONDS,
        description="SLA threshold in seconds (default: 300 = 5 minutes)",
        ge=1,
    ),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get analytics summary for the specified time window.

    Returns metrics aggregated over the last 7 or 30 days:
    - intents_count: Distribution of entries by intent
    - review_rate: Breakdown of review statuses (approved/rejected/editing/pending)
    - frt: First response time statistics and SLA compliance

    Query Parameters:
    - window: '7d' or '30d' (default: 7d)
    - workspace_id: Optional workspace filter
    - sla_threshold_seconds: SLA threshold in seconds (default: 300)

    Example Response:
    {
      "window": "7d",
      "workspace_id": "ws-123",
      "period_start": "2025-10-19T00:00:00Z",
      "period_end": "2025-10-26T00:00:00Z",
      "metrics": {
        "intents_count": {"support": 45, "cs": 30, "exec": 15, "other": 10},
        "review_rate": {
          "total": 100,
          "approved": 60,
          "rejected": 20,
          "editing": 10,
          "pending": 10,
          "approved_rate": 60.0,
          "rejected_rate": 20.0,
          "editing_rate": 10.0,
          "pending_rate": 10.0
        },
        "frt": {
          "avg_seconds": 180.5,
          "median_seconds": 150.0,
          "min_seconds": 30.0,
          "max_seconds": 450.0,
          "sla_threshold_seconds": 300,
          "sla_met_count": 75,
          "sla_met_percentage": 83.33,
          "total_with_frt": 90
        }
      },
      "trend": {
        "intents_count_previous": {"support": 40, "cs": 25, "exec": 20, "other": 15},
        "review_rate_previous": {...},
        "frt_previous": {...}
      }
    }
    """
    try:
        # Parse window
        window_delta = parse_window(window)
        period_end = datetime.now(timezone.utc)
        period_start = period_end - window_delta

        # Build query for current period
        query = select(DraftReview).where(
            DraftReview.created_at >= period_start
        )

        if workspace_id:
            query = query.where(DraftReview.workspace_id == workspace_id)

        # Execute query
        reviews = session.exec(query).all()

        # Calculate current period metrics
        current_metrics = calculate_metrics(list(reviews), sla_threshold_seconds)

        # Calculate previous period metrics for trend comparison
        previous_period_end = period_start
        previous_period_start = previous_period_end - window_delta

        previous_query = select(DraftReview).where(
            and_(
                DraftReview.created_at >= previous_period_start,
                DraftReview.created_at < previous_period_end,
            )
        )

        if workspace_id:
            previous_query = previous_query.where(DraftReview.workspace_id == workspace_id)

        previous_reviews = session.exec(previous_query).all()
        previous_metrics = calculate_metrics(list(previous_reviews), sla_threshold_seconds)

        return {
            "window": window,
            "workspace_id": workspace_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "metrics": current_metrics,
            "trend": {
                "intents_count_previous": previous_metrics["intents_count"],
                "review_rate_previous": previous_metrics["review_rate"],
                "frt_previous": previous_metrics["frt"],
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating analytics: {str(e)}")
