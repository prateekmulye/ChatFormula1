"""Enhanced node functions with advanced logic for LangGraph agent.

This module provides additional node implementations with:
- Entity extraction using structured output
- Advanced routing logic with branching
- Error handling with fallbacks
- Result scoring and ranking
- Streaming support using astream_events
"""

from typing import Any, AsyncIterator, Optional

import structlog
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config.settings import Settings
from src.exceptions import SearchAPIError, VectorStoreError

from .state import AgentState

logger = structlog.get_logger(__name__)


class EntityExtraction(BaseModel):
    """Structured output for entity extraction."""

    drivers: list[str] = Field(
        default_factory=list,
        description="Driver names mentioned in query",
    )

    teams: list[str] = Field(
        default_factory=list,
        description="Team names mentioned in query",
    )

    races: list[str] = Field(
        default_factory=list,
        description="Race or Grand Prix names mentioned",
    )

    circuits: list[str] = Field(
        default_factory=list,
        description="Circuit names mentioned",
    )

    years: list[str] = Field(
        default_factory=list,
        description="Years or seasons mentioned",
    )

    technical_terms: list[str] = Field(
        default_factory=list,
        description="Technical F1 terms (DRS, ERS, tire compounds, etc.)",
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in entity extraction",
    )


class ContextScore(BaseModel):
    """Model for scoring retrieved context."""

    relevance: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance to query (0-1)",
    )

    recency: float = Field(
        ge=0.0,
        le=1.0,
        description="Recency score (0-1, higher for newer content)",
    )

    authority: float = Field(
        ge=0.0,
        le=1.0,
        description="Source authority score (0-1)",
    )

    completeness: float = Field(
        ge=0.0,
        le=1.0,
        description="Content completeness score (0-1)",
    )

    @property
    def total_score(self) -> float:
        """Calculate weighted total score."""
        return (
            self.relevance * 0.4
            + self.recency * 0.3
            + self.authority * 0.2
            + self.completeness * 0.1
        )


async def analyze_query_with_entities(
    query: str,
    llm: ChatOpenAI,
) -> tuple[str, dict[str, Any], EntityExtraction]:
    """Analyze query with detailed entity extraction using structured output.

    Args:
        query: User query to analyze
        llm: ChatOpenAI instance for analysis

    Returns:
        Tuple of (intent, metadata, entities)
    """
    logger.info("analyzing_query_with_entities", query=query[:100])

    # Entity extraction prompt
    entity_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an entity extractor for F1 queries. Extract all relevant entities:
- Driver names (e.g., "Lewis Hamilton", "Max Verstappen")
- Team names (e.g., "Mercedes", "Red Bull Racing")
- Race names (e.g., "Monaco Grand Prix", "British GP")
- Circuit names (e.g., "Silverstone", "Monza")
- Years/seasons (e.g., "2024", "2023 season")
- Technical terms (e.g., "DRS", "tire strategy", "undercut")

Be thorough and accurate. Extract full names when possible.""",
            ),
            ("human", "Extract entities from: {query}"),
        ]
    )

    try:
        # Use structured output for entity extraction
        structured_llm = llm.with_structured_output(EntityExtraction)
        entities: EntityExtraction = await structured_llm.ainvoke(
            entity_prompt.format_messages(query=query)
        )

        logger.info(
            "entities_extracted",
            drivers=len(entities.drivers),
            teams=len(entities.teams),
            races=len(entities.races),
            years=len(entities.years),
            confidence=entities.confidence,
        )

        # Determine intent based on entities and query content
        intent = _determine_intent_from_entities(query, entities)

        metadata = {
            "entity_confidence": entities.confidence,
            "entity_count": (
                len(entities.drivers)
                + len(entities.teams)
                + len(entities.races)
                + len(entities.circuits)
                + len(entities.years)
            ),
        }

        return intent, metadata, entities

    except Exception as e:
        logger.error("entity_extraction_failed", error=str(e))
        # Return empty entities on failure
        return (
            "general",
            {"entity_extraction_error": str(e)},
            EntityExtraction(confidence=0.0),
        )


def _determine_intent_from_entities(query: str, entities: EntityExtraction) -> str:
    """Determine query intent based on extracted entities and keywords.

    Args:
        query: User query
        entities: Extracted entities

    Returns:
        Intent string
    """
    query_lower = query.lower()

    # Check for prediction keywords
    prediction_keywords = [
        "predict",
        "prediction",
        "forecast",
        "will",
        "going to",
        "expect",
    ]
    if any(keyword in query_lower for keyword in prediction_keywords):
        return "prediction"

    # Check for current info keywords
    current_keywords = ["current", "latest", "now", "today", "this season", "2024"]
    if any(keyword in query_lower for keyword in current_keywords):
        return "current_info"

    # Check for historical keywords
    historical_keywords = ["history", "past", "previous", "all-time", "ever"]
    if any(keyword in query_lower for keyword in historical_keywords) or entities.years:
        return "historical"

    # Check for technical keywords
    technical_keywords = ["how does", "explain", "what is", "technical", "regulation"]
    if (
        any(keyword in query_lower for keyword in technical_keywords)
        or entities.technical_terms
    ):
        return "technical"

    # Check for off-topic
    f1_keywords = [
        "f1",
        "formula 1",
        "formula one",
        "grand prix",
        "gp",
        "driver",
        "team",
        "race",
        "circuit",
        "championship",
    ]
    has_f1_keyword = any(keyword in query_lower for keyword in f1_keywords)
    has_entities = (
        entities.drivers or entities.teams or entities.races or entities.circuits
    )

    if not has_f1_keyword and not has_entities and len(query.split()) > 5:
        return "off_topic"

    return "general"


async def route_with_branching(
    state: AgentState,
    config: Settings,
) -> dict[str, Any]:
    """Advanced routing logic with multiple branching paths.

    Implements sophisticated routing based on:
    - Query intent and confidence
    - Entity types and counts
    - Historical performance of retrieval methods
    - Fallback availability

    Args:
        state: Current agent state
        config: Application settings

    Returns:
        State updates with routing decision
    """
    intent = state.intent
    entities = state.entities
    metadata = state.metadata

    logger.info(
        "routing_with_branching",
        intent=intent,
        entity_count=metadata.get("entity_count", 0),
    )

    # Initialize routing decision
    routing = {
        "use_vector_search": False,
        "use_tavily_search": False,
        "search_priority": "balanced",  # balanced, vector_first, search_first
        "fallback_strategy": "graceful",  # graceful, strict, none
    }

    # Intent-based routing
    if intent == "current_info":
        routing["use_tavily_search"] = True
        routing["use_vector_search"] = True  # For context
        routing["search_priority"] = "search_first"

    elif intent == "historical":
        routing["use_vector_search"] = True
        routing["use_tavily_search"] = False
        routing["search_priority"] = "vector_first"

    elif intent == "prediction":
        routing["use_vector_search"] = True
        routing["use_tavily_search"] = True
        routing["search_priority"] = "balanced"

    elif intent == "technical":
        routing["use_vector_search"] = True
        routing["use_tavily_search"] = False
        routing["search_priority"] = "vector_first"

    elif intent == "off_topic":
        routing["use_vector_search"] = False
        routing["use_tavily_search"] = False
        routing["fallback_strategy"] = "strict"

    else:  # general
        routing["use_vector_search"] = True
        routing["use_tavily_search"] = True
        routing["search_priority"] = "balanced"

    # Adjust based on entity confidence
    entity_confidence = metadata.get("entity_confidence", 0.5)
    if entity_confidence < 0.3:
        # Low confidence - use both sources
        routing["use_vector_search"] = True
        routing["use_tavily_search"] = True

    logger.info(
        "routing_decision_made",
        vector=routing["use_vector_search"],
        tavily=routing["use_tavily_search"],
        priority=routing["search_priority"],
    )

    return {
        "metadata": {
            "routing_decision": routing,
        },
    }


async def vector_search_with_fallback(
    state: AgentState,
    vector_store: Any,
    config: Settings,
) -> dict[str, Any]:
    """Vector search with comprehensive error handling and fallback.

    Args:
        state: Current agent state
        vector_store: VectorStoreManager instance
        config: Application settings

    Returns:
        State updates with retrieved documents or fallback
    """
    query = state.query
    entities = state.entities

    logger.info("vector_search_with_fallback", query=query[:100])

    try:
        # Build filters from entities
        filters = _build_advanced_filters(entities)

        # Attempt primary search
        docs = await vector_store.similarity_search(
            query=query,
            k=config.vector_search_top_k,
            filters=filters,
        )

        if docs:
            retrieved_docs = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": "vector_store",
                    "score": 0.8,
                }
                for doc in docs
            ]

            logger.info("vector_search_successful", docs_count=len(retrieved_docs))

            return {
                "retrieved_docs": retrieved_docs,
                "metadata": {
                    "vector_search_status": "success",
                    "vector_search_count": len(retrieved_docs),
                },
            }
        else:
            # No results - try broader search without filters
            logger.warning("no_results_with_filters_retrying_without")

            docs = await vector_store.similarity_search(
                query=query,
                k=config.vector_search_top_k,
                filters=None,
            )

            retrieved_docs = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": "vector_store",
                    "score": 0.6,  # Lower score for unfiltered results
                }
                for doc in docs
            ]

            logger.info(
                "vector_search_fallback_successful", docs_count=len(retrieved_docs)
            )

            return {
                "retrieved_docs": retrieved_docs,
                "metadata": {
                    "vector_search_status": "fallback",
                    "vector_search_count": len(retrieved_docs),
                    "used_filters": False,
                },
            }

    except VectorStoreError as e:
        logger.error("vector_search_failed", error=str(e))
        return {
            "retrieved_docs": [],
            "metadata": {
                "vector_search_status": "failed",
                "vector_search_error": str(e),
            },
        }
    except Exception as e:
        logger.error("vector_search_unexpected_error", error=str(e))
        return {
            "retrieved_docs": [],
            "metadata": {
                "vector_search_status": "error",
                "vector_search_error": str(e),
            },
        }


async def tavily_search_with_fallback(
    state: AgentState,
    tavily_client: Any,
) -> dict[str, Any]:
    """Tavily search with graceful fallback handling.

    Args:
        state: Current agent state
        tavily_client: TavilyClient instance

    Returns:
        State updates with search results or fallback
    """
    query = state.query

    logger.info("tavily_search_with_fallback", query=query[:100])

    try:
        # Use safe_search which handles fallbacks internally
        results, error = await tavily_client.safe_search(query=query)

        if error:
            logger.warning("tavily_search_fallback_mode", error=error)
            return {
                "search_results": [],
                "metadata": {
                    "tavily_status": "fallback",
                    "tavily_error": error,
                    "tavily_fallback": True,
                },
            }

        if not results:
            logger.warning("tavily_search_no_results")
            return {
                "search_results": [],
                "metadata": {
                    "tavily_status": "no_results",
                },
            }

        # Convert results
        search_results = [
            {
                "content": result.get("content", ""),
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "score": result.get("score", 0.7),
                "source": "tavily_search",
            }
            for result in results
        ]

        logger.info("tavily_search_successful", results_count=len(search_results))

        return {
            "search_results": search_results,
            "metadata": {
                "tavily_status": "success",
                "tavily_search_count": len(search_results),
            },
        }

    except SearchAPIError as e:
        logger.error("tavily_search_api_error", error=str(e))
        return {
            "search_results": [],
            "metadata": {
                "tavily_status": "error",
                "tavily_error": str(e),
                "tavily_fallback": True,
            },
        }
    except Exception as e:
        logger.error("tavily_search_unexpected_error", error=str(e))
        return {
            "search_results": [],
            "metadata": {
                "tavily_status": "error",
                "tavily_error": str(e),
                "tavily_fallback": True,
            },
        }


def score_context_item(
    item: dict[str, Any],
    query: str,
) -> ContextScore:
    """Score a single context item for ranking.

    Args:
        item: Context item (document or search result)
        query: Original user query

    Returns:
        ContextScore with individual and total scores
    """
    # Relevance: based on provided score or default
    relevance = item.get("score", 0.5)

    # Recency: based on source type and metadata
    recency = 0.5  # Default
    if item.get("source") == "tavily_search":
        recency = 0.9  # Search results are current
    elif "metadata" in item:
        # Check for year in metadata
        year = item["metadata"].get("year")
        if year:
            current_year = 2024
            years_old = current_year - int(year)
            recency = max(0.1, 1.0 - (years_old * 0.1))

    # Authority: based on source type
    authority = 0.7  # Default
    if item.get("source") == "vector_store":
        authority = 0.8  # Curated knowledge base
    elif item.get("source") == "tavily_search":
        # Check URL for trusted domains
        url = item.get("url", "")
        trusted_domains = ["formula1.com", "fia.com", "autosport.com"]
        if any(domain in url for domain in trusted_domains):
            authority = 0.9
        else:
            authority = 0.7

    # Completeness: based on content length
    content = item.get("content", "")
    content_length = len(content)
    if content_length > 500:
        completeness = 1.0
    elif content_length > 200:
        completeness = 0.7
    elif content_length > 100:
        completeness = 0.5
    else:
        completeness = 0.3

    return ContextScore(
        relevance=relevance,
        recency=recency,
        authority=authority,
        completeness=completeness,
    )


async def rank_context_with_scoring(
    state: AgentState,
) -> dict[str, Any]:
    """Advanced context ranking with multi-factor scoring.

    Args:
        state: Current agent state

    Returns:
        State updates with ranked and scored context
    """
    retrieved_docs = state.retrieved_docs
    search_results = state.search_results
    query = state.query

    logger.info(
        "ranking_context_with_scoring",
        vector_docs=len(retrieved_docs),
        search_results=len(search_results),
    )

    # Score all items
    scored_items = []

    for doc in retrieved_docs:
        score = score_context_item(doc, query)
        scored_items.append(
            {
                "item": doc,
                "score": score.total_score,
                "score_breakdown": score.model_dump(),
            }
        )

    for result in search_results:
        score = score_context_item(result, query)
        scored_items.append(
            {
                "item": result,
                "score": score.total_score,
                "score_breakdown": score.model_dump(),
            }
        )

    # Sort by total score
    scored_items.sort(key=lambda x: x["score"], reverse=True)

    # Build context from top items
    context_parts = []

    # Separate by source type
    vector_items = [
        x for x in scored_items if x["item"].get("source") == "vector_store"
    ]
    search_items = [
        x for x in scored_items if x["item"].get("source") == "tavily_search"
    ]

    if vector_items:
        context_parts.append("=== Historical Context ===")
        for i, scored in enumerate(vector_items[:3], 1):
            item = scored["item"]
            context_parts.append(
                f"\n[Historical Source {i}] (Score: {scored['score']:.2f})\n"
                f"{item['content'][:600]}..."
            )

    if search_items:
        context_parts.append("\n\n=== Current Information ===")
        for i, scored in enumerate(search_items[:3], 1):
            item = scored["item"]
            context_parts.append(
                f"\n[Current Source {i}] {item.get('title', 'Untitled')} (Score: {scored['score']:.2f})\n"
                f"{item['content'][:600]}..."
            )

    context = "\n".join(context_parts)

    logger.info(
        "context_ranked_with_scores",
        total_items=len(scored_items),
        top_score=scored_items[0]["score"] if scored_items else 0,
        context_length=len(context),
    )

    return {
        "context": context,
        "metadata": {
            "scored_items_count": len(scored_items),
            "top_score": scored_items[0]["score"] if scored_items else 0,
            "context_length": len(context),
        },
    }


async def generate_with_streaming(
    state: AgentState,
    llm: ChatOpenAI,
) -> AsyncIterator[dict[str, Any]]:
    """Generate response with streaming support using astream_events.

    Args:
        state: Current agent state
        llm: ChatOpenAI instance

    Yields:
        State updates with streaming response chunks
    """
    query = state.query
    context = state.context
    messages = state.messages

    logger.info("generating_with_streaming", query=query[:100])

    # Build prompt
    from src.prompts.system_prompts import F1_EXPERT_SYSTEM_PROMPT

    prompt_messages = [
        {"role": "system", "content": F1_EXPERT_SYSTEM_PROMPT},
    ]

    # Add recent conversation history
    recent = [m for m in messages if m.type != "system"][-10:]
    for msg in recent:
        prompt_messages.append(
            {
                "role": "user" if msg.type == "human" else "assistant",
                "content": msg.content,
            }
        )

    # Add current query with context
    if context:
        user_content = f"""Context information:
{context}

User question: {query}

Please provide a comprehensive answer using the context above."""
    else:
        user_content = query

    prompt_messages.append({"role": "user", "content": user_content})

    # Stream response
    response_chunks = []

    try:
        async for event in llm.astream_events(prompt_messages, version="v1"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    response_chunks.append(chunk.content)

                    # Yield incremental update
                    yield {
                        "response": "".join(response_chunks),
                        "metadata": {
                            "streaming": True,
                            "chunk_count": len(response_chunks),
                        },
                    }

        # Final update
        full_response = "".join(response_chunks)

        logger.info(
            "streaming_generation_complete",
            response_length=len(full_response),
            chunks=len(response_chunks),
        )

        yield {
            "response": full_response,
            "messages": [
                HumanMessage(content=query),
                AIMessage(content=full_response),
            ],
            "metadata": {
                "streaming": False,
                "generation_complete": True,
                "response_length": len(full_response),
            },
        }

    except Exception as e:
        logger.error("streaming_generation_failed", error=str(e))
        error_response = (
            "I apologize, but I encountered an error generating a response. "
            "Please try rephrasing your question."
        )
        yield {
            "response": error_response,
            "messages": [
                HumanMessage(content=query),
                AIMessage(content=error_response),
            ],
            "metadata": {
                "generation_error": str(e),
            },
        }


def _build_advanced_filters(entities: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Build advanced Pinecone filters from entities.

    Args:
        entities: Extracted entities

    Returns:
        Pinecone filter dictionary or None
    """
    filters = {}

    # Year filters
    if "years" in entities and entities["years"]:
        years = [int(y) for y in entities["years"] if y.isdigit()]
        if years:
            if len(years) == 1:
                filters["year"] = years[0]
            else:
                filters["year"] = {
                    "$gte": min(years),
                    "$lte": max(years),
                }

    # Driver filter
    if "drivers" in entities and entities["drivers"]:
        # Use $in for multiple drivers
        if len(entities["drivers"]) == 1:
            filters["driver"] = entities["drivers"][0]
        else:
            filters["driver"] = {"$in": entities["drivers"]}

    # Team filter
    if "teams" in entities and entities["teams"]:
        if len(entities["teams"]) == 1:
            filters["team"] = entities["teams"][0]
        else:
            filters["team"] = {"$in": entities["teams"]}

    # Circuit filter
    if "circuits" in entities and entities["circuits"]:
        if len(entities["circuits"]) == 1:
            filters["circuit"] = entities["circuits"][0]

    return filters if filters else None
