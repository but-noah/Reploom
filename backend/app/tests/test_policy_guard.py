"""
Unit tests for PolicyGuard blocklist validation.

Tests that PolicyGuard correctly blocks configured phrases from workspace settings.
"""
import pytest
from app.agents.reploom_crew import policy_guard_node, DraftCrewState


def test_policy_guard_blocks_configured_phrases():
    """Test that PolicyGuard detects and blocks configured phrases."""
    # Setup state with draft containing blocklisted phrase
    state: DraftCrewState = {
        "original_message_summary": "Test message",
        "workspace_id": "test-workspace",
        "thread_id": None,
        "intent": "support",
        "confidence": 0.9,
        "context_snippets": [],
        "draft_html": "<p>This is a free trial offer for you!</p>",
        "violations": [],
        "tone_level": 3,
        "style_json": {},
        "blocklist": ["free trial", "money back guarantee"],
    }

    # Run policy guard
    result = policy_guard_node(state)

    # Assert violation detected
    assert len(result["violations"]) == 1
    assert "free trial" in result["violations"][0].lower()


def test_policy_guard_case_insensitive():
    """Test that PolicyGuard is case-insensitive."""
    state: DraftCrewState = {
        "original_message_summary": "Test message",
        "workspace_id": "test-workspace",
        "thread_id": None,
        "intent": "support",
        "confidence": 0.9,
        "context_snippets": [],
        "draft_html": "<p>This is a FREE TRIAL offer!</p>",
        "violations": [],
        "tone_level": 3,
        "style_json": {},
        "blocklist": ["free trial"],
    }

    result = policy_guard_node(state)

    assert len(result["violations"]) == 1


def test_policy_guard_allows_clean_draft():
    """Test that PolicyGuard passes drafts without blocklisted phrases."""
    state: DraftCrewState = {
        "original_message_summary": "Test message",
        "workspace_id": "test-workspace",
        "thread_id": None,
        "intent": "support",
        "confidence": 0.9,
        "context_snippets": [],
        "draft_html": "<p>Thank you for your inquiry. We're happy to help!</p>",
        "violations": [],
        "tone_level": 3,
        "style_json": {},
        "blocklist": ["free trial", "money back guarantee"],
    }

    result = policy_guard_node(state)

    assert len(result["violations"]) == 0


def test_policy_guard_multiple_violations():
    """Test that PolicyGuard detects multiple blocklisted phrases."""
    state: DraftCrewState = {
        "original_message_summary": "Test message",
        "workspace_id": "test-workspace",
        "thread_id": None,
        "intent": "support",
        "confidence": 0.9,
        "context_snippets": [],
        "draft_html": "<p>Get our free trial with a money back guarantee!</p>",
        "violations": [],
        "tone_level": 3,
        "style_json": {},
        "blocklist": ["free trial", "money back guarantee", "limited time"],
    }

    result = policy_guard_node(state)

    assert len(result["violations"]) == 2
    assert any("free trial" in v.lower() for v in result["violations"])
    assert any("money back guarantee" in v.lower() for v in result["violations"])


def test_drafter_uses_tone_level():
    """Test that drafter node respects tone_level setting."""
    from app.agents.reploom_crew import drafter_node

    # Test with formal tone (level 1)
    state_formal: DraftCrewState = {
        "original_message_summary": "User needs help with account setup",
        "workspace_id": "test-workspace",
        "thread_id": None,
        "intent": "support",
        "confidence": 0.9,
        "context_snippets": ["Account setup guide available"],
        "draft_html": None,
        "violations": [],
        "tone_level": 1,  # Very formal
        "style_json": {},
        "blocklist": [],
    }

    result = drafter_node(state_formal)
    assert result["draft_html"] is not None
    assert len(result["draft_html"]) > 0

    # Test with casual tone (level 5)
    state_casual: DraftCrewState = {
        "original_message_summary": "User needs help with account setup",
        "workspace_id": "test-workspace",
        "thread_id": None,
        "intent": "support",
        "confidence": 0.9,
        "context_snippets": ["Account setup guide available"],
        "draft_html": None,
        "violations": [],
        "tone_level": 5,  # Very casual
        "style_json": {},
        "blocklist": [],
    }

    result = drafter_node(state_casual)
    assert result["draft_html"] is not None
    assert len(result["draft_html"]) > 0


def test_drafter_uses_brand_voice():
    """Test that drafter node respects brand voice guidelines."""
    from app.agents.reploom_crew import drafter_node

    state: DraftCrewState = {
        "original_message_summary": "User needs help",
        "workspace_id": "test-workspace",
        "thread_id": None,
        "intent": "support",
        "confidence": 0.9,
        "context_snippets": [],
        "draft_html": None,
        "violations": [],
        "tone_level": 3,
        "style_json": {"brand_voice": "professional yet approachable"},
        "blocklist": [],
    }

    result = drafter_node(state)
    assert result["draft_html"] is not None
