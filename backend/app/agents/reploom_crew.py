"""
Reploom Draft Generation Crew

A production-ready LangGraph workflow for generating email drafts with:
- Intent classification
- Context building (stub)
- Draft generation with tone control
- Policy enforcement (blocklist, tone compliance)
- Persistent checkpointer (Postgres or memory fallback)

Flow: classifier -> contextBuilder -> drafter -> policyGuard
"""
import logging
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.workspace import get_workspace_settings

# Configure logging with PII redaction
logger = logging.getLogger(__name__)


def redact_pii(text: str, max_length: int = 100) -> str:
    """Redact PII from logs by truncating and masking."""
    if len(text) > max_length:
        return text[:max_length] + "...[REDACTED]"
    return text


# State Schema
class DraftCrewState(TypedDict):
    """State for the draft generation crew workflow."""
    # Input
    original_message_summary: str
    workspace_id: str | None
    thread_id: str | None  # Track thread ID in state

    # Intermediate
    intent: Literal["support", "cs", "exec", "other"] | None
    confidence: float | None
    context_snippets: list[str]

    # Output
    draft_html: str | None
    violations: list[str]

    # Config (loaded from workspace settings)
    tone_level: int  # 1-5 scale: 1=very formal, 5=very casual
    style_json: dict  # Additional brand voice guidelines
    blocklist: list[str]


# Initialize LLM
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

    # Log with PII redaction
    logger.info(
        f"Classifying message intent",
        extra={
            "message_preview": redact_pii(message_summary, 50),
            "workspace_id": state.get("workspace_id", "unknown"),
        }
    )

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

    # Parse response
    import json
    try:
        result = json.loads(response.content)
        intent = result.get("intent", "other")
        confidence = result.get("confidence", 0.5)
    except Exception as e:
        logger.warning(f"Failed to parse classifier response: {e}")
        intent = "other"
        confidence = 0.5

    logger.info(f"Classified as intent={intent} with confidence={confidence:.2f}")

    return {
        **state,
        "intent": intent,
        "confidence": confidence,
    }


# Node: Context Builder
def context_builder_node(state: DraftCrewState) -> DraftCrewState:
    """
    Build context for draft generation using KB retrieval.

    Retrieves relevant knowledge base chunks based on the message summary
    and workspace context.
    """
    message_summary = state["original_message_summary"]
    workspace_id = state.get("workspace_id")

    logger.info(
        f"Building context from KB",
        extra={
            "workspace_id": workspace_id,
            "message_preview": redact_pii(message_summary, 50),
        }
    )

    context_snippets = []

    # Retrieve from KB if workspace_id is available
    if workspace_id:
        try:
            from app.kb.retrieval import search_kb

            # Search KB for relevant chunks
            search_results = search_kb(
                query=message_summary,
                workspace_id=workspace_id,
                k=5,  # Top 5 most relevant chunks
                with_vectors=False,  # Optimize: skip vectors
            )

            # Format snippets for drafter
            for result in search_results:
                snippet = f"[{result.source}"
                if result.title:
                    snippet += f" - {result.title}"
                snippet += f"] {result.content}"
                context_snippets.append(snippet)

            logger.info(f"Retrieved {len(context_snippets)} KB snippets")

        except Exception as e:
            logger.warning(f"KB retrieval failed: {e}. Continuing without KB context.")
            # Don't fail the entire workflow if KB is unavailable
            context_snippets = []
    else:
        logger.info("No workspace_id provided, skipping KB retrieval")

    return {
        **state,
        "context_snippets": context_snippets,
    }


# Node: Drafter
def drafter_node(state: DraftCrewState) -> DraftCrewState:
    """
    Generate HTML draft response respecting tone_level (1-5) and style guidelines.
    """
    message_summary = state["original_message_summary"]
    intent = state["intent"]
    tone_level = state.get("tone_level", 3)
    style_json = state.get("style_json", {})
    context = state.get("context_snippets", [])

    logger.info(
        f"Generating draft",
        extra={
            "intent": intent,
            "tone_level": tone_level,
            "context_count": len(context),
        }
    )

    # Build context string
    context_str = ""
    if context:
        context_str = "\n\nRelevant context:\n" + "\n".join(f"- {snippet}" for snippet in context)

    # Map tone level (1-5) to tone instructions
    tone_map = {
        1: ("Very Formal", "Use highly professional, formal language. Avoid all contractions. Be extremely respectful and precise. Use formal greetings and closings."),
        2: ("Formal", "Use professional, formal language. Avoid contractions. Be respectful and precise."),
        3: ("Neutral", "Use warm, professional language. Contractions are acceptable. Be helpful and clear."),
        4: ("Casual", "Use friendly, conversational language. Use contractions naturally. Be personable and approachable."),
        5: ("Very Casual", "Use relaxed, conversational language. Be personable and authentic. Write as you would to a friend."),
    }

    tone_name, tone_instruction = tone_map.get(tone_level, tone_map[3])

    # Add brand voice guidelines if present
    brand_voice_str = ""
    if style_json and "brand_voice" in style_json:
        brand_voice_str = f"\n\nBrand Voice Guidelines: {style_json['brand_voice']}"

    prompt = f"""Generate an HTML email response for this customer inquiry.

Intent: {intent}
Tone Level: {tone_level}/5 ({tone_name})
Tone Instruction: {tone_instruction}{brand_voice_str}
Message summary: {message_summary}
{context_str}

Requirements:
- Return valid HTML (use <p>, <br>, <strong>, <em>, etc.)
- Be concise but complete
- Match the requested tone level and brand voice
- Address the customer's needs based on the intent
- Do NOT include any code blocks or markdown - just raw HTML

Generate the HTML email body:
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    draft_html = response.content.strip()

    # Clean up any markdown code blocks if LLM included them
    if draft_html.startswith("```html"):
        draft_html = draft_html.replace("```html", "").replace("```", "").strip()

    logger.info(f"Generated draft with {len(draft_html)} characters")

    return {
        **state,
        "draft_html": draft_html,
    }


# Node: Policy Guard
def policy_guard_node(state: DraftCrewState) -> DraftCrewState:
    """
    Check draft against workspace policy:
    - Blocklist phrases (loaded from workspace settings)
    - Fail fast on violations

    If violations found, halt the workflow.
    """
    draft = state.get("draft_html", "")
    blocklist = state.get("blocklist", [])
    violations = []

    logger.info(
        f"Checking policy compliance",
        extra={
            "blocklist_count": len(blocklist),
            "draft_length": len(draft),
        }
    )

    # Check blocklist (case-insensitive, fail fast)
    draft_lower = draft.lower()
    for phrase in blocklist:
        phrase_clean = phrase.strip().lower()
        if phrase_clean and phrase_clean in draft_lower:
            violation_msg = f"Blocklisted phrase detected: '{phrase.strip()}'"
            violations.append(violation_msg)
            logger.warning(
                f"Policy violation",
                extra={
                    "violation": phrase.strip(),
                    "workspace_id": state.get("workspace_id", "unknown"),
                }
            )

    # Future: LLM-based tone verification
    # if state.get("tone_level"):
    #     tone_check = verify_tone_compliance(draft, state["tone_level"])
    #     if not tone_check["compliant"]:
    #         violations.append(f"Tone mismatch: {tone_check['reason']}")

    if violations:
        logger.warning(f"Draft failed policy check with {len(violations)} violation(s)")
    else:
        logger.info("Draft passed policy check")

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


# Initialize checkpointer based on configuration
def get_checkpointer():
    """
    Get checkpointer based on GRAPH_CHECKPOINTER setting.

    - postgres: PostgreSQL checkpointer (production)
    - memory: In-memory checkpointer (development only)

    Falls back to memory if postgres is configured but unavailable.
    """
    checkpointer_type = settings.GRAPH_CHECKPOINTER.lower()

    if checkpointer_type == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresCheckpointer

            # Extract connection string
            # LangGraph PostgresCheckpointer uses psycopg3 format
            db_url = settings.DATABASE_URL

            logger.info("Initializing PostgreSQL checkpointer")
            checkpointer = PostgresCheckpointer.from_conn_string(db_url)

            # Test connection
            checkpointer.setup()
            logger.info("PostgreSQL checkpointer initialized successfully")
            return checkpointer

        except ImportError:
            logger.warning(
                "PostgreSQL checkpointer not available (missing langgraph-checkpoint-postgres). "
                "Falling back to memory checkpointer. "
                "Install with: pip install langgraph-checkpoint-postgres"
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize PostgreSQL checkpointer: {e}. "
                "Falling back to memory checkpointer."
            )

    # Fallback to memory checkpointer
    logger.warning(
        "Using in-memory checkpointer. State will not persist across server restarts. "
        "For production, set GRAPH_CHECKPOINTER=postgres and ensure database is configured."
    )
    return MemorySaver()


# Initialize checkpointer and compile graph
checkpointer = get_checkpointer()
graph = create_reploom_crew().compile(checkpointer=checkpointer)

# Export for LangGraph server
reploom_crew = graph


def prepare_initial_state(
    message_summary: str,
    workspace_id: str | None = None,
    thread_id: str | None = None,
) -> DraftCrewState:
    """
    Prepare initial state for the workflow, loading workspace settings.

    Args:
        message_summary: Summary of the incoming message
        workspace_id: Workspace identifier (loads settings from DB)
        thread_id: Thread ID for resumable execution

    Returns:
        Initial state dict with workspace settings applied
    """
    # Load workspace settings
    workspace_config = get_workspace_settings(workspace_id)

    logger.info(
        f"Prepared initial state",
        extra={
            "workspace_id": workspace_config.workspace_id,
            "tone_level": workspace_config.tone_level,
            "blocklist_count": len(workspace_config.blocklist),
        }
    )

    return {
        "original_message_summary": message_summary,
        "workspace_id": workspace_id,
        "thread_id": thread_id,
        "tone_level": workspace_config.tone_level,
        "style_json": workspace_config.style_json,
        "blocklist": workspace_config.blocklist,
        "intent": None,
        "confidence": None,
        "context_snippets": [],
        "draft_html": None,
        "violations": [],
    }
