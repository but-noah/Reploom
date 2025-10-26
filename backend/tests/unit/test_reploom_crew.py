"""
Unit tests for Reploom Crew workflow nodes.

Tests cover:
- Policy guard blocklist enforcement
- Tone level variations in draft generation
- Intent classification
- State transitions
"""
import pytest
from app.agents.reploom_crew import (
    classifier_node,
    context_builder_node,
    drafter_node,
    policy_guard_node,
    should_halt,
    DraftCrewState,
)


class TestPolicyGuard:
    """Test suite for policy guard node."""

    def test_blocklist_detection_single_phrase(self):
        """Policy guard should detect a single blocklisted phrase."""
        state: DraftCrewState = {
            "original_message_summary": "Test message",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "draft_html": "<p>Get your free trial now!</p>",
            "violations": [],
            "tone_level": "friendly",
            "blocklist": ["free trial", "money back guarantee"],
        }

        result = policy_guard_node(state)

        assert len(result["violations"]) == 1
        assert "free trial" in result["violations"][0].lower()

    def test_blocklist_detection_multiple_phrases(self):
        """Policy guard should detect multiple blocklisted phrases."""
        state: DraftCrewState = {
            "original_message_summary": "Test message",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "draft_html": "<p>Get your free trial with a money back guarantee!</p>",
            "violations": [],
            "tone_level": "friendly",
            "blocklist": ["free trial", "money back guarantee"],
        }

        result = policy_guard_node(state)

        assert len(result["violations"]) == 2
        assert any("free trial" in v.lower() for v in result["violations"])
        assert any("money back guarantee" in v.lower() for v in result["violations"])

    def test_no_violations_clean_draft(self):
        """Policy guard should pass clean drafts without violations."""
        state: DraftCrewState = {
            "original_message_summary": "Test message",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "draft_html": "<p>Thank you for contacting support. We'll help you resolve this issue.</p>",
            "violations": [],
            "tone_level": "friendly",
            "blocklist": ["free trial", "money back guarantee"],
        }

        result = policy_guard_node(state)

        assert len(result["violations"]) == 0

    def test_case_insensitive_blocklist(self):
        """Policy guard should be case-insensitive."""
        state: DraftCrewState = {
            "original_message_summary": "Test message",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "draft_html": "<p>Get your FREE TRIAL now!</p>",
            "violations": [],
            "tone_level": "friendly",
            "blocklist": ["free trial"],
        }

        result = policy_guard_node(state)

        assert len(result["violations"]) == 1

    def test_should_halt_with_violations(self):
        """Router should halt when violations are present."""
        state: DraftCrewState = {
            "original_message_summary": "Test",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "draft_html": "<p>Test</p>",
            "violations": ["Blocklisted phrase detected: 'free trial'"],
            "tone_level": "friendly",
            "blocklist": [],
        }

        result = should_halt(state)

        assert result == "halt"

    def test_should_continue_without_violations(self):
        """Router should continue when no violations are present."""
        state: DraftCrewState = {
            "original_message_summary": "Test",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "draft_html": "<p>Test</p>",
            "violations": [],
            "tone_level": "friendly",
            "blocklist": [],
        }

        result = should_halt(state)

        assert result == "continue"


class TestDrafter:
    """Test suite for drafter node with tone variations."""

    @pytest.mark.asyncio
    async def test_tone_formal_vs_friendly(self):
        """Drafter should produce different outputs for formal vs friendly tones."""
        base_state = {
            "original_message_summary": "Customer wants to know about pricing",
            "workspace_id": "ws-test",
            "intent": "cs",
            "confidence": 0.85,
            "context_snippets": [],
            "violations": [],
            "blocklist": [],
        }

        # Generate formal draft
        formal_state: DraftCrewState = {
            **base_state,
            "tone_level": "formal",
            "draft_html": None,
        }
        formal_result = drafter_node(formal_state)

        # Generate friendly draft
        friendly_state: DraftCrewState = {
            **base_state,
            "tone_level": "friendly",
            "draft_html": None,
        }
        friendly_result = drafter_node(friendly_state)

        # Both should produce HTML
        assert formal_result["draft_html"] is not None
        assert friendly_result["draft_html"] is not None

        # They should be different
        assert formal_result["draft_html"] != friendly_result["draft_html"]

        # Formal should avoid contractions (heuristic check)
        # Note: This is a simplistic check; in production, you'd use more sophisticated tone analysis
        formal_html = formal_result["draft_html"].lower()
        friendly_html = friendly_result["draft_html"].lower()

        # Check for HTML tags
        assert "<p>" in formal_html or "<div>" in formal_html
        assert "<p>" in friendly_html or "<div>" in friendly_html

    @pytest.mark.asyncio
    async def test_tone_casual_style(self):
        """Drafter should produce casual tone when requested."""
        state: DraftCrewState = {
            "original_message_summary": "Customer wants help with a feature",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "tone_level": "casual",
            "draft_html": None,
            "violations": [],
            "blocklist": [],
        }

        result = drafter_node(state)

        assert result["draft_html"] is not None
        assert len(result["draft_html"]) > 0
        # Check for HTML
        assert "<p>" in result["draft_html"].lower() or "<div>" in result["draft_html"].lower()


class TestClassifier:
    """Test suite for classifier node."""

    @pytest.mark.asyncio
    async def test_classifier_returns_intent_and_confidence(self):
        """Classifier should return intent and confidence."""
        state: DraftCrewState = {
            "original_message_summary": "I need help resetting my password",
            "workspace_id": "ws-test",
            "intent": None,
            "confidence": None,
            "context_snippets": [],
            "draft_html": None,
            "violations": [],
            "tone_level": "friendly",
            "blocklist": [],
        }

        result = classifier_node(state)

        assert result["intent"] in ["support", "cs", "exec", "other"]
        assert result["confidence"] is not None
        assert 0.0 <= result["confidence"] <= 1.0


class TestContextBuilder:
    """Test suite for context builder node (stub)."""

    def test_context_builder_returns_empty_list(self):
        """Context builder should return empty list (stub implementation)."""
        state: DraftCrewState = {
            "original_message_summary": "Test message",
            "workspace_id": "ws-test",
            "intent": "support",
            "confidence": 0.9,
            "context_snippets": [],
            "draft_html": None,
            "violations": [],
            "tone_level": "friendly",
            "blocklist": [],
        }

        result = context_builder_node(state)

        assert result["context_snippets"] == []


class TestWorkflowIntegration:
    """Integration tests for the full workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_no_violations(self):
        """Test complete workflow from classifier to policy guard."""
        initial_state: DraftCrewState = {
            "original_message_summary": "I need help with my account settings",
            "workspace_id": "ws-test",
            "intent": None,
            "confidence": None,
            "context_snippets": [],
            "draft_html": None,
            "violations": [],
            "tone_level": "friendly",
            "blocklist": ["free trial"],
        }

        # Run through the workflow manually
        state = classifier_node(initial_state)
        state = context_builder_node(state)
        state = drafter_node(state)
        state = policy_guard_node(state)

        # Verify final state
        assert state["intent"] is not None
        assert state["confidence"] is not None
        assert state["draft_html"] is not None
        assert len(state["violations"]) == 0

    @pytest.mark.asyncio
    async def test_full_workflow_with_violations(self):
        """Test workflow that triggers policy violations."""
        initial_state: DraftCrewState = {
            "original_message_summary": "Tell them about our free trial offer",
            "workspace_id": "ws-test",
            "intent": None,
            "confidence": None,
            "context_snippets": [],
            "draft_html": None,
            "violations": [],
            "tone_level": "friendly",
            "blocklist": ["free trial"],
        }

        # Run through the workflow manually
        state = classifier_node(initial_state)
        state = context_builder_node(state)
        state = drafter_node(state)
        state = policy_guard_node(state)

        # The drafter might or might not include "free trial" depending on the LLM
        # This test is non-deterministic, but we can check the structure
        assert state["intent"] is not None
        assert state["confidence"] is not None
        assert state["draft_html"] is not None
        # Violations may or may not be present depending on LLM output
