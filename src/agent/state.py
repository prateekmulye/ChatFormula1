"""Agent state and data models for LangGraph orchestration.

This module defines the state structure used by the LangGraph agent,
including message handling, context management, and metadata tracking.
"""

from datetime import datetime
from typing import Annotated, Any, Literal, Optional, Sequence

import structlog
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


def add_messages(
    left: Sequence[BaseMessage], right: Sequence[BaseMessage]
) -> list[BaseMessage]:
    """Reducer function to add messages to the state.

    This reducer appends new messages to the existing message list,
    which is the standard behavior for conversation history.

    Args:
        left: Existing messages in state
        right: New messages to add

    Returns:
        Combined list of messages
    """
    return list(left) + list(right)


def replace_context(left: str, right: str) -> str:
    """Reducer function to replace context in state.

    Args:
        left: Existing context (ignored)
        right: New context to set

    Returns:
        New context value
    """
    return right


def merge_metadata(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Reducer function to merge metadata dictionaries.

    Args:
        left: Existing metadata
        right: New metadata to merge

    Returns:
        Merged metadata dictionary
    """
    merged = left.copy()
    merged.update(right)
    return merged


class AgentState(BaseModel):
    """State model for LangGraph agent.

    This model defines all the state that flows through the agent graph,
    including conversation messages, retrieved context, search results,
    and metadata for tracking and debugging.

    Attributes:
        messages: Conversation history (user and assistant messages)
        query: Current user query being processed
        intent: Detected intent (e.g., "current_info", "historical", "prediction")
        entities: Extracted entities from query (drivers, teams, races, etc.)
        retrieved_docs: Documents retrieved from vector store
        search_results: Results from Tavily search
        context: Combined context string for LLM generation
        response: Generated response from LLM
        metadata: Additional metadata for tracking and debugging
        session_id: Unique identifier for conversation session
        timestamp: Timestamp of current state update
    """

    # Conversation messages with add_messages reducer
    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(
        default_factory=list,
        description="Conversation history with user and assistant messages",
    )

    # Current query being processed
    query: str = Field(
        default="",
        description="Current user query being processed",
    )

    # Query analysis results
    intent: Optional[str] = Field(
        default=None,
        description="Detected intent: current_info, historical, prediction, technical, general",
    )

    entities: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities: drivers, teams, races, years, circuits",
    )

    # Retrieved information
    retrieved_docs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Documents retrieved from vector store with metadata",
    )

    search_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Results from Tavily search API",
    )

    # Context for generation
    context: Annotated[str, replace_context] = Field(
        default="",
        description="Combined context string for LLM generation",
    )

    # Generated response
    response: Optional[str] = Field(
        default=None,
        description="Generated response from LLM",
    )

    # Metadata with merge_metadata reducer
    metadata: Annotated[dict[str, Any], merge_metadata] = Field(
        default_factory=dict,
        description="Additional metadata for tracking and debugging",
    )

    # Session tracking
    session_id: str = Field(
        default="",
        description="Unique identifier for conversation session",
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of current state update",
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class QueryAnalysis(BaseModel):
    """Structured output for query analysis.

    This model defines the expected structure when analyzing user queries
    to extract intent and entities.
    """

    intent: Literal[
        "current_info", "historical", "prediction", "technical", "general", "off_topic"
    ] = Field(description="Primary intent of the user query")

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for intent classification (0-1)",
    )

    requires_search: bool = Field(
        description="Whether query requires real-time search (current info)",
    )

    requires_vector_search: bool = Field(
        description="Whether query requires historical knowledge from vector store",
    )

    entities: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Extracted entities organized by type",
    )

    time_period: Optional[str] = Field(
        default=None,
        description="Relevant time period (e.g., '2024 season', '2020-2023', 'all-time')",
    )

    reasoning: str = Field(
        description="Brief explanation of the analysis",
    )


class SearchDecision(BaseModel):
    """Decision model for routing search strategy.

    Determines which retrieval methods to use based on query analysis.
    """

    use_vector_search: bool = Field(
        description="Whether to search vector store for historical context",
    )

    use_tavily_search: bool = Field(
        description="Whether to use Tavily for real-time information",
    )

    vector_search_filters: Optional[dict[str, Any]] = Field(
        default=None,
        description="Metadata filters for vector search (year, category, etc.)",
    )

    search_query: str = Field(
        description="Optimized query for search operations",
    )

    reasoning: str = Field(
        description="Explanation of routing decision",
    )


class PredictionOutput(BaseModel):
    """Structured output for race predictions.

    This model ensures predictions follow a consistent format with
    confidence levels and supporting reasoning.
    """

    prediction_type: Literal["race_winner", "podium", "qualifying", "championship"] = (
        Field(
            description="Type of prediction being made",
        )
    )

    predictions: list[dict[str, Any]] = Field(
        description="List of predictions with driver/team and confidence",
    )

    confidence_level: Literal["low", "medium", "high"] = Field(
        description="Overall confidence in predictions",
    )

    key_factors: list[str] = Field(
        description="Key factors influencing the prediction",
    )

    reasoning: str = Field(
        description="Detailed explanation of prediction reasoning",
    )

    data_sources: list[str] = Field(
        default_factory=list,
        description="Sources used for prediction (vector store, search, etc.)",
    )


class ConversationContext(BaseModel):
    """Model for managing conversation context.

    Tracks conversation history and provides methods for context management
    including sliding window and summarization.
    """

    session_id: str = Field(
        description="Unique session identifier",
    )

    messages: list[BaseMessage] = Field(
        default_factory=list,
        description="Full conversation history",
    )

    max_history: int = Field(
        default=10,
        description="Maximum number of message pairs to maintain",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Session creation timestamp",
    )

    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Session metadata (user preferences, etc.)",
    )

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to conversation history.

        Args:
            message: Message to add
        """
        self.messages.append(message)
        self.updated_at = datetime.now()

        # Implement sliding window if history exceeds max
        if len(self.messages) > self.max_history * 2:  # 2 messages per turn
            # Keep system message if present, then apply sliding window
            system_messages = [m for m in self.messages if m.type == "system"]
            other_messages = [m for m in self.messages if m.type != "system"]

            # Keep most recent messages
            recent_messages = other_messages[-(self.max_history * 2) :]
            self.messages = system_messages + recent_messages

            logger.info(
                "conversation_history_trimmed",
                session_id=self.session_id,
                total_messages=len(self.messages),
            )

    def get_recent_messages(self, count: int = 5) -> list[BaseMessage]:
        """Get the most recent messages.

        Args:
            count: Number of message pairs to retrieve

        Returns:
            List of recent messages
        """
        # Exclude system messages from count
        non_system = [m for m in self.messages if m.type != "system"]
        recent = non_system[-(count * 2) :]

        # Add back system message if present
        system_messages = [m for m in self.messages if m.type == "system"]
        return system_messages + recent

    def clear(self) -> None:
        """Clear conversation history while preserving session metadata."""
        # Keep system messages
        system_messages = [m for m in self.messages if m.type == "system"]
        self.messages = system_messages
        self.updated_at = datetime.now()

        logger.info(
            "conversation_cleared",
            session_id=self.session_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization.

        Returns:
            Dictionary representation of context
        """
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


def validate_state(state: AgentState) -> tuple[bool, Optional[str]]:
    """Validate agent state for consistency and completeness.

    Args:
        state: Agent state to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if not state.session_id:
        return False, "session_id is required"

    # Validate query if intent is set
    if state.intent and not state.query:
        return False, "query is required when intent is set"

    # Validate context if response is set
    if state.response and not state.context:
        logger.warning(
            "response_without_context",
            session_id=state.session_id,
        )

    # Validate message types
    for msg in state.messages:
        if not isinstance(msg, BaseMessage):
            return False, f"Invalid message type: {type(msg)}"

    return True, None


def create_initial_state(
    session_id: str,
    system_message: Optional[BaseMessage] = None,
) -> AgentState:
    """Create initial agent state for a new conversation.

    Args:
        session_id: Unique session identifier
        system_message: Optional system message to include

    Returns:
        Initialized AgentState
    """
    messages = [system_message] if system_message else []

    state = AgentState(
        messages=messages,
        session_id=session_id,
        timestamp=datetime.now(),
        metadata={
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        },
    )

    logger.info(
        "initial_state_created",
        session_id=session_id,
        has_system_message=system_message is not None,
    )

    return state
