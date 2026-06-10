"""LangGraph state models: AgentState and QueryAnalysis."""

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict, Field


def add_messages(
    left: Sequence[BaseMessage], right: Sequence[BaseMessage]
) -> list[BaseMessage]:
    """Append new messages to the existing conversation history."""
    return list(left) + list(right)


def replace_context(left: str, right: str) -> str:
    """Replace the context string with the latest value."""
    return right


def merge_metadata(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Merge metadata updates into the existing metadata dictionary."""
    merged = left.copy()
    merged.update(right)
    return merged


class AgentState(BaseModel):
    """State flowing through the agent graph.

    Attributes:
        messages: Conversation history (user and assistant messages)
        query: Current user query being processed
        intent: Detected intent (e.g. "current_info", "historical")
        entities: Extracted entities (drivers, teams, races, years, circuits)
        retrieved_docs: Documents retrieved from the vector store
        search_results: Results from Tavily search
        context: Combined context string for LLM generation
        response: Generated response from the LLM
        metadata: Additional metadata for tracking and debugging
        request_id: Correlation ID supplied by the gateway
        timestamp: Timestamp of the current state update
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(
        default_factory=list,
        description="Conversation history with user and assistant messages",
    )

    query: str = Field(
        default="",
        description="Current user query being processed",
    )

    intent: str | None = Field(
        default=None,
        description="Detected intent: current_info, historical, prediction, technical, general",
    )

    entities: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities: drivers, teams, races, years, circuits",
    )

    retrieved_docs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Documents retrieved from the vector store with metadata",
    )

    search_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Results from the Tavily search API",
    )

    context: Annotated[str, replace_context] = Field(
        default="",
        description="Combined context string for LLM generation",
    )

    response: str | None = Field(
        default=None,
        description="Generated response from the LLM",
    )

    metadata: Annotated[dict[str, Any], merge_metadata] = Field(
        default_factory=dict,
        description="Additional metadata for tracking and debugging",
    )

    request_id: str = Field(
        default="",
        description="Correlation ID supplied by the gateway",
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of the current state update",
    )


class QueryAnalysis(BaseModel):
    """Structured output schema for LLM query analysis."""

    intent: Literal[
        "current_info", "historical", "prediction", "technical", "general", "off_topic"
    ] = Field(description="Primary intent of the user query")

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for intent classification (0-1)",
    )

    requires_search: bool = Field(
        description="Whether the query requires real-time web search",
    )

    requires_vector_search: bool = Field(
        description="Whether the query requires historical knowledge from the vector store",
    )

    entities: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Extracted entities organized by type",
    )

    time_period: str | None = Field(
        default=None,
        description="Relevant time period (e.g. '2024 season', '2020-2023', 'all-time')",
    )

    reasoning: str = Field(
        description="Brief explanation of the analysis",
    )
