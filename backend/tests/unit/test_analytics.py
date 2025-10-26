"""Unit tests for analytics metrics calculations."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.api.routes.analytics import calculate_metrics, parse_window
from app.models.draft_reviews import DraftReview


class TestParseWindow:
    """Test window parsing function."""

    def test_parse_window_7d(self):
        """Test parsing 7 day window."""
        result = parse_window("7d")
        assert result == timedelta(days=7)

    def test_parse_window_30d(self):
        """Test parsing 30 day window."""
        result = parse_window("30d")
        assert result == timedelta(days=30)

    def test_parse_window_invalid(self):
        """Test parsing invalid window raises ValueError."""
        with pytest.raises(ValueError, match="Invalid window"):
            parse_window("14d")


class TestCalculateMetrics:
    """Test metrics calculation logic."""

    def test_empty_reviews(self):
        """Test metrics calculation with empty review list."""
        result = calculate_metrics([])

        assert result["intents_count"] == {}
        assert result["review_rate"]["total"] == 0
        assert result["review_rate"]["approved"] == 0
        assert result["review_rate"]["approved_rate"] == 0
        assert result["frt"]["avg_seconds"] == 0
        assert result["frt"]["sla_met_count"] == 0
        assert result["frt"]["total_with_frt"] == 0

    def test_intents_count(self):
        """Test intent counting."""
        reviews = [
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread1",
                draft_id="draft1",
                intent="support",
                status="pending",
                draft_html="<p>Test</p>",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread2",
                draft_id="draft2",
                intent="support",
                status="pending",
                draft_html="<p>Test</p>",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread3",
                draft_id="draft3",
                intent="cs",
                status="pending",
                draft_html="<p>Test</p>",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread4",
                draft_id="draft4",
                intent="exec",
                status="pending",
                draft_html="<p>Test</p>",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        result = calculate_metrics(reviews)

        assert result["intents_count"] == {"support": 2, "cs": 1, "exec": 1}

    def test_intents_count_with_null(self):
        """Test intent counting with null values."""
        reviews = [
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread1",
                draft_id="draft1",
                intent=None,
                status="pending",
                draft_html="<p>Test</p>",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread2",
                draft_id="draft2",
                intent="support",
                status="pending",
                draft_html="<p>Test</p>",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        result = calculate_metrics(reviews)

        assert result["intents_count"] == {"unknown": 1, "support": 1}

    def test_review_rate_all_statuses(self):
        """Test review rate calculation with all statuses."""
        now = datetime.now(timezone.utc)
        reviews = [
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id=f"thread{i}",
                draft_id=f"draft{i}",
                intent="support",
                status=status,
                draft_html="<p>Test</p>",
                created_at=now,
                updated_at=now,
            )
            for i, status in enumerate(
                ["pending", "approved", "approved", "rejected", "editing"]
            )
        ]

        result = calculate_metrics(reviews)

        assert result["review_rate"]["total"] == 5
        assert result["review_rate"]["pending"] == 1
        assert result["review_rate"]["approved"] == 2
        assert result["review_rate"]["rejected"] == 1
        assert result["review_rate"]["editing"] == 1
        assert result["review_rate"]["pending_rate"] == 20.0
        assert result["review_rate"]["approved_rate"] == 40.0
        assert result["review_rate"]["rejected_rate"] == 20.0
        assert result["review_rate"]["editing_rate"] == 20.0

    def test_frt_calculation(self):
        """Test first response time calculation."""
        base_time = datetime.now(timezone.utc)

        reviews = [
            # FRT: 60 seconds (meets SLA)
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread1",
                draft_id="draft1",
                intent="support",
                status="approved",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=60),
                reviewed_at=base_time + timedelta(seconds=60),
            ),
            # FRT: 120 seconds (meets SLA)
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread2",
                draft_id="draft2",
                intent="support",
                status="rejected",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=120),
                reviewed_at=base_time + timedelta(seconds=120),
            ),
            # FRT: 600 seconds (misses SLA)
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread3",
                draft_id="draft3",
                intent="support",
                status="editing",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=600),
                reviewed_at=base_time + timedelta(seconds=600),
            ),
            # Pending - no FRT
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread4",
                draft_id="draft4",
                intent="support",
                status="pending",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time,
                reviewed_at=None,
            ),
        ]

        result = calculate_metrics(reviews, sla_threshold_seconds=300)

        assert result["frt"]["total_with_frt"] == 3
        assert result["frt"]["avg_seconds"] == pytest.approx(260.0, rel=1)
        assert result["frt"]["median_seconds"] == 120.0
        assert result["frt"]["min_seconds"] == 60.0
        assert result["frt"]["max_seconds"] == 600.0
        assert result["frt"]["sla_met_count"] == 2
        assert result["frt"]["sla_met_percentage"] == pytest.approx(66.67, rel=0.1)
        assert result["frt"]["sla_threshold_seconds"] == 300

    def test_frt_calculation_custom_sla(self):
        """Test FRT calculation with custom SLA threshold."""
        base_time = datetime.now(timezone.utc)

        reviews = [
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread1",
                draft_id="draft1",
                intent="support",
                status="approved",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=100),
                reviewed_at=base_time + timedelta(seconds=100),
            ),
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread2",
                draft_id="draft2",
                intent="support",
                status="approved",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=200),
                reviewed_at=base_time + timedelta(seconds=200),
            ),
        ]

        # With 150 second SLA, only first review meets it
        result = calculate_metrics(reviews, sla_threshold_seconds=150)

        assert result["frt"]["sla_met_count"] == 1
        assert result["frt"]["sla_met_percentage"] == 50.0
        assert result["frt"]["sla_threshold_seconds"] == 150

    def test_frt_uses_reviewed_at_when_available(self):
        """Test FRT uses reviewed_at timestamp when available."""
        base_time = datetime.now(timezone.utc)

        review = DraftReview(
            id=str(uuid4()),
            user_id="user1",
            user_email="test@example.com",
            thread_id="thread1",
            draft_id="draft1",
            intent="support",
            status="approved",
            draft_html="<p>Test</p>",
            created_at=base_time,
            updated_at=base_time + timedelta(seconds=200),  # Later update
            reviewed_at=base_time + timedelta(seconds=100),  # Actual review time
        )

        result = calculate_metrics([review])

        # Should use reviewed_at (100s) not updated_at (200s)
        assert result["frt"]["avg_seconds"] == 100.0

    def test_frt_handles_missing_reviewed_at(self):
        """Test FRT falls back to updated_at when reviewed_at is None."""
        base_time = datetime.now(timezone.utc)

        review = DraftReview(
            id=str(uuid4()),
            user_id="user1",
            user_email="test@example.com",
            thread_id="thread1",
            draft_id="draft1",
            intent="support",
            status="approved",
            draft_html="<p>Test</p>",
            created_at=base_time,
            updated_at=base_time + timedelta(seconds=150),
            reviewed_at=None,  # Missing reviewed_at
        )

        result = calculate_metrics([review])

        # Should fall back to updated_at
        assert result["frt"]["avg_seconds"] == 150.0

    def test_comprehensive_metrics(self):
        """Test comprehensive metrics calculation with realistic data."""
        base_time = datetime.now(timezone.utc)

        reviews = [
            # Support intent, approved, FRT 90s
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread1",
                draft_id="draft1",
                intent="support",
                status="approved",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=90),
                reviewed_at=base_time + timedelta(seconds=90),
            ),
            # CS intent, approved, FRT 180s
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread2",
                draft_id="draft2",
                intent="cs",
                status="approved",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=180),
                reviewed_at=base_time + timedelta(seconds=180),
            ),
            # Exec intent, rejected, FRT 400s
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread3",
                draft_id="draft3",
                intent="exec",
                status="rejected",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=400),
                reviewed_at=base_time + timedelta(seconds=400),
            ),
            # Support intent, pending (no FRT)
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread4",
                draft_id="draft4",
                intent="support",
                status="pending",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time,
                reviewed_at=None,
            ),
            # Other intent, editing, FRT 250s
            DraftReview(
                id=str(uuid4()),
                user_id="user1",
                user_email="test@example.com",
                thread_id="thread5",
                draft_id="draft5",
                intent="other",
                status="editing",
                draft_html="<p>Test</p>",
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=250),
                reviewed_at=base_time + timedelta(seconds=250),
            ),
        ]

        result = calculate_metrics(reviews, sla_threshold_seconds=300)

        # Check intents count
        assert result["intents_count"] == {"support": 2, "cs": 1, "exec": 1, "other": 1}

        # Check review rate
        assert result["review_rate"]["total"] == 5
        assert result["review_rate"]["approved"] == 2
        assert result["review_rate"]["rejected"] == 1
        assert result["review_rate"]["editing"] == 1
        assert result["review_rate"]["pending"] == 1
        assert result["review_rate"]["approved_rate"] == 40.0

        # Check FRT
        assert result["frt"]["total_with_frt"] == 4
        assert result["frt"]["sla_met_count"] == 3  # 90s, 180s, 250s meet SLA
        assert result["frt"]["sla_met_percentage"] == 75.0
        assert result["frt"]["min_seconds"] == 90.0
        assert result["frt"]["max_seconds"] == 400.0
