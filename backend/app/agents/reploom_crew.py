"""
Reploom Draft Generation Crew

A multi-agent LangGraph workflow for generating email drafts with:
- Intent classification
- Context building (stub)
- Draft generation with tone control
- Policy enforcement (blocklist, tone compliance)

Flow: classifier -> contextBuilder -> drafter -> policyGuard
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os

# TODO: Replace MemorySaver with PostgresCheckpointer once available
# See: https://github.com/but-noah/Reploom/issues/XXX
# from langgraph.checkpoint.postgres import PostgresCheckpointer
# checkpointer = PostgresCheckpointer.from_conn_string(settings.DATABASE_URL)

# State Schema
class DraftCrewState(TypedDict):
    """State for the draft generation crew workflow."""
    # Input
    original_message_summary: str
    workspace_id: str | None

    # Intermediate
    intent: Literal["support", "cs", "exec", "other"] | None
    confidence: float | None
    context_snippets: list[str]

    # Output
    draft_html: str | None
    violations: list[str]

    # Config
    tone_level: Literal["formal", "friendly", "casual"] | None
    blocklist: list[str]


# Configuration
BLOCKLIST_PHRASES = os.getenv("REPLOOM_BLOCKLIST", "free trial,money back guarantee,limited time offer").split(",")
DEFAULT_TONE = os.getenv("REPLOOM_DEFAULT_TONE", "friendly")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


# Node: Classifier
def classifier_node(state: DraftCrewState) -> DraftCrewState:
    """
    Classify the intent of the incoming message.

    Returns:
        - intent: support | cs | exec | other
        - confidence: 0.0 - 1.0
    """
    message_summary = state["original_message_summary"]

    prompt = f"""Classify the intent of this email summary into one of these categories:
- support: Technical support or troubleshooting
- cs: Customer service, billing, or account questions
- exec: Executive/partnership/press inquiry
- other: General inquiries or uncategorized

Email summary: {message_summary}

Respond with JSON only:
{{"intent": "<category>", "confidence": <0.0-1.0>}}
"""

    response = llm.invoke([HumanMessage(content=prompt)])

    # Parse response (simplified - in production use structured output)
    import json
    try:
        result = json.loads(response.content)
        intent = result.get("intent", "other")
        confidence = result.get("confidence", 0.5)
    except:
        intent = "other"
        confidence = 0.5

    return {
        **state,
        "intent": intent,
        "confidence": confidence,
    }


# Node: Context Builder (Stub)
def context_builder_node(state: DraftCrewState) -> DraftCrewState:
    """
    Build context for draft generation.

    TODO: Implement RAG retrieval from Qdrant
    TODO: Fetch workspace-specific context (past emails, KB articles, etc.)

    For now, returns empty context_snippets.
    """
    # Placeholder implementation
    context_snippets = []

    # Future implementation would:
    # 1. Query Qdrant with message_summary as embedding
    # 2. Fetch workspace-specific documents
    # 3. Retrieve similar past conversations
    # 4. Pull relevant KB articles based on intent

    return {
        **state,
        "context_snippets": context_snippets,
    }


# Node: Drafter
def drafter_node(state: DraftCrewState) -> DraftCrewState:
    """
    Generate HTML draft response respecting tone_level.
    """
    message_summary = state["original_message_summary"]
    intent = state["intent"]
    tone = state.get("tone_level") or DEFAULT_TONE
    context = state.get("context_snippets", [])

    # Build context string
    context_str = ""
    if context:
        context_str = "\n\nRelevant context:\n" + "\n".join(f"- {snippet}" for snippet in context)

    # Tone instructions
    tone_instructions = {
        "formal": "Use professional, formal language. Avoid contractions. Be respectful and precise.",
        "friendly": "Use warm, professional language. Contractions are fine. Be helpful and approachable.",
        "casual": "Use conversational, relaxed language. Be personable and authentic.",
    }

    prompt = f"""Generate an HTML email response for this customer inquiry.

Intent: {intent}
Tone: {tone} - {tone_instructions.get(tone, tone_instructions["friendly"])}
Message summary: {message_summary}
{context_str}

Requirements:
- Return valid HTML (use <p>, <br>, <strong>, <em>, etc.)
- Be concise but complete
- Match the requested tone
- Address the customer's needs based on the intent
- Do NOT include any code blocks or markdown - just raw HTML

Generate the HTML email body:
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    draft_html = response.content.strip()

    # Clean up any markdown code blocks if LLM included them
    if draft_html.startswith("```html"):
        draft_html = draft_html.replace("```html", "").replace("```", "").strip()

    return {
        **state,
        "draft_html": draft_html,
    }


# Node: Policy Guard
def policy_guard_node(state: DraftCrewState) -> DraftCrewState:
    """
    Check draft against workspace policy:
    - Blocklist phrases
    - Tone compliance (future: use LLM to verify tone)

    If violations found, halt the workflow.
    """
    draft = state.get("draft_html", "")
    blocklist = state.get("blocklist") or BLOCKLIST_PHRASES
    violations = []

    # Check blocklist
    draft_lower = draft.lower()
    for phrase in blocklist:
        if phrase.strip().lower() in draft_lower:
            violations.append(f"Blocklisted phrase detected: '{phrase.strip()}'")

    # Future: LLM-based tone verification
    # if state.get("tone_level"):
    #     tone_check = verify_tone_compliance(draft, state["tone_level"])
    #     if not tone_check["compliant"]:
    #         violations.append(f"Tone mismatch: {tone_check['reason']}")

    return {
        **state,
        "violations": violations,
    }


# Routing logic
def should_halt(state: DraftCrewState) -> str:
    """Route to END if violations detected, else continue."""
    if state.get("violations"):
        return "halt"
    return "continue"


# Build the graph
def create_reploom_crew() -> StateGraph:
    """
    Create the LangGraph workflow for draft generation.

    Flow:
        classifier -> contextBuilder -> drafter -> policyGuard
                                                        |
                                                   (violations?) -> halt/continue
    """
    workflow = StateGraph(DraftCrewState)

    # Add nodes
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("contextBuilder", context_builder_node)
    workflow.add_node("drafter", drafter_node)
    workflow.add_node("policyGuard", policy_guard_node)

    # Define edges
    workflow.set_entry_point("classifier")
    workflow.add_edge("classifier", "contextBuilder")
    workflow.add_edge("contextBuilder", "drafter")
    workflow.add_edge("drafter", "policyGuard")

    # Conditional routing from policyGuard
    workflow.add_conditional_edges(
        "policyGuard",
        should_halt,
        {
            "halt": END,
            "continue": END,
        }
    )

    return workflow


# Compile the graph with checkpointer
checkpointer = MemorySaver()
graph = create_reploom_crew().compile(checkpointer=checkpointer)


# Export for LangGraph server
reploom_crew = graph


# Helper function for backend wrapper
def run_draft_flow(
    message_summary: str,
    workspace_id: str | None = None,
    thread_id: str | None = None,
    tone_level: str = "friendly",
    blocklist: list[str] | None = None,
) -> dict:
    """
    Run the draft generation flow.

    Args:
        message_summary: Summary of the incoming message
        workspace_id: Workspace identifier
        thread_id: Thread ID for resumable execution (checkpointer)
        tone_level: Tone of the response (formal, friendly, casual)
        blocklist: List of disallowed phrases

    Returns:
        dict with keys: draft_html, confidence, intent, violations
    """
    config = {"configurable": {"thread_id": thread_id or "default"}}

    initial_state = {
        "original_message_summary": message_summary,
        "workspace_id": workspace_id,
        "tone_level": tone_level,
        "blocklist": blocklist or BLOCKLIST_PHRASES,
        "intent": None,
        "confidence": None,
        "context_snippets": [],
        "draft_html": None,
        "violations": [],
    }

    # Run the workflow
    result = graph.invoke(initial_state, config=config)

    return {
        "draft_html": result.get("draft_html"),
        "confidence": result.get("confidence"),
        "intent": result.get("intent"),
        "violations": result.get("violations", []),
    }
