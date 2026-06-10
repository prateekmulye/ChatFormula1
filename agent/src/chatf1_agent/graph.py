"""LangGraph pipeline: analyze → route → retrieve → rank → generate.

The graph is built and compiled exactly once at application startup (no
checkpointer — the agent is stateless; the gateway owns conversation
state). The generation LLM is tagged ``["generation"]`` so the streaming
server can forward only its tokens to clients.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Literal, cast

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from chatf1_agent.caching import get_cache_manager
from chatf1_agent.prompts import F1_EXPERT_SYSTEM_PROMPT
from chatf1_agent.providers import create_analysis_llm, create_generation_llm
from chatf1_agent.retrieval.tavily import TavilyClient
from chatf1_agent.retrieval.vector_store import VectorStoreManager
from chatf1_agent.settings import Settings
from chatf1_agent.state import AgentState, QueryAnalysis

logger = structlog.get_logger(__name__)

# Domains whose results get an authority boost during ranking.
TRUSTED_DOMAINS = ["formula1.com", "fia.com", "autosport.com"]


class ContextScore(BaseModel):
    """Multi-factor score for a retrieved context item."""

    relevance: float = Field(ge=0.0, le=1.0, description="Relevance to query (0-1)")
    recency: float = Field(
        ge=0.0, le=1.0, description="Recency score (higher for newer content)"
    )
    authority: float = Field(ge=0.0, le=1.0, description="Source authority score")
    completeness: float = Field(
        ge=0.0, le=1.0, description="Content completeness score"
    )

    @property
    def total_score(self) -> float:
        """Weighted total: relevance 40%, recency 30%, authority 20%, completeness 10%."""
        return (
            self.relevance * 0.4
            + self.recency * 0.3
            + self.authority * 0.2
            + self.completeness * 0.1
        )


def score_context_item(item: dict[str, Any]) -> ContextScore:
    """Score a single context item (vector document or search result).

    Args:
        item: Context item with content, source, and optional metadata.

    Returns:
        ContextScore with individual factor scores.
    """
    relevance = item.get("score", 0.5)

    # Recency: search results are current; vector docs decay by year.
    recency = 0.5
    if item.get("source") == "tavily_search":
        recency = 0.9
    elif "metadata" in item:
        year = item["metadata"].get("year")
        if year:
            current_year = datetime.now().year
            years_old = current_year - int(year)
            recency = max(0.1, 1.0 - (years_old * 0.1))

    # Authority: curated knowledge base or trusted F1 domains rank higher.
    authority = 0.7
    if item.get("source") == "vector_store":
        authority = 0.8
    elif item.get("source") == "tavily_search":
        url = item.get("url", "")
        authority = 0.9 if any(domain in url for domain in TRUSTED_DOMAINS) else 0.7

    # Completeness: longer content tends to be more complete.
    content_length = len(item.get("content", ""))
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


class F1AgentGraph:
    """LangGraph-based RAG pipeline for ChatFormula1.

    Orchestrates: query analysis → routing → (vector / web / parallel)
    retrieval → multi-factor context ranking → generation → formatting.
    The compiled graph is created once in ``__init__`` and reused for
    every request.
    """

    def __init__(
        self,
        config: Settings,
        vector_store: VectorStoreManager,
        tavily_client: TavilyClient,
    ) -> None:
        """Initialize the agent graph and compile it once.

        Args:
            config: Application settings
            vector_store: Initialized vector store manager
            tavily_client: Initialized Tavily search client
        """
        self.config = config
        self.vector_store = vector_store
        self.tavily_client = tavily_client

        self.llm = create_generation_llm(config)
        self.analysis_llm = create_analysis_llm(config)

        self.graph = self._build_graph()
        self.compiled_graph: Runnable = self.graph.compile()

        logger.info(
            "f1_agent_graph_initialized",
            generation_model=config.generation_model,
            analysis_model=config.analysis_model,
            temperature=config.openai_temperature,
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine with parallel retrieval.

        Returns:
            Configured StateGraph
        """
        graph = StateGraph(AgentState)

        graph.add_node("analyze_query", self.analyze_query_node)
        graph.add_node("route", self.route_node)
        graph.add_node("vector_search", self.vector_search_node)
        graph.add_node("tavily_search", self.tavily_search_node)
        graph.add_node("parallel_retrieval", self.parallel_retrieval_node)
        graph.add_node("rank_context", self.rank_context_node)
        graph.add_node("generate", self.generate_node)
        graph.add_node("format_response", self.format_response_node)

        graph.set_entry_point("analyze_query")
        graph.add_edge("analyze_query", "route")

        graph.add_conditional_edges(
            "route",
            self.route_decision,
            {
                "vector_only": "vector_search",
                "search_only": "tavily_search",
                "both": "parallel_retrieval",
                "direct": "generate",
            },
        )

        graph.add_edge("vector_search", "rank_context")
        graph.add_edge("tavily_search", "rank_context")
        graph.add_edge("parallel_retrieval", "rank_context")
        graph.add_edge("rank_context", "generate")
        graph.add_edge("generate", "format_response")
        graph.add_edge("format_response", END)

        logger.info("langgraph_state_machine_built", parallel_retrieval_enabled=True)

        return graph

    async def analyze_query_node(self, state: AgentState) -> dict[str, Any]:
        """Analyze the user query to detect intent and extract entities.

        Uses structured output to ensure a consistent analysis format.

        Args:
            state: Current agent state

        Returns:
            State updates with intent and entities
        """
        query = state.query

        logger.info("analyzing_query", query=query[:100])

        analysis_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="""You are a query analyzer for an F1 chatbot. Analyze the user's query and extract:
1. Intent: current_info, historical, prediction, technical, general, or off_topic
2. Confidence: 0.0 to 1.0
3. Whether real-time search is needed
4. Whether vector store search is needed
5. Entities: drivers, teams, races, years, circuits
6. Time period if relevant
7. Brief reasoning

Be accurate and concise."""
                ),
                HumanMessage(content=f"Analyze this F1 query: {query}"),
            ]
        )

        try:
            structured_llm = self.analysis_llm.with_structured_output(QueryAnalysis)
            analysis = cast(
                QueryAnalysis,
                await structured_llm.ainvoke(analysis_prompt.format_messages()),
            )

            logger.info(
                "query_analyzed",
                intent=analysis.intent,
                confidence=analysis.confidence,
                requires_search=analysis.requires_search,
                requires_vector=analysis.requires_vector_search,
            )

            return {
                "intent": analysis.intent,
                "entities": analysis.entities,
                "metadata": {
                    "analysis": analysis.model_dump(),
                    "requires_search": analysis.requires_search,
                    "requires_vector_search": analysis.requires_vector_search,
                },
            }

        except Exception as e:
            logger.error("query_analysis_failed", error=str(e))
            # Fall back to retrieving from both sources.
            return {
                "intent": "general",
                "entities": {},
                "metadata": {
                    "analysis_error": str(e),
                    "requires_search": True,
                    "requires_vector_search": True,
                },
            }

    async def route_node(self, state: AgentState) -> dict[str, Any]:
        """Record the routing decision based on query analysis.

        Args:
            state: Current agent state

        Returns:
            State updates with the routing decision
        """
        metadata = state.metadata
        requires_search = metadata.get("requires_search", False)
        requires_vector = metadata.get("requires_vector_search", False)

        logger.info(
            "routing_query",
            intent=state.intent,
            requires_search=requires_search,
            requires_vector=requires_vector,
        )

        return {
            "metadata": {
                "routing_decision": {
                    "use_vector_search": requires_vector,
                    "use_tavily_search": requires_search,
                },
            },
        }

    def route_decision(
        self, state: AgentState
    ) -> Literal["vector_only", "search_only", "both", "direct"]:
        """Conditional edge: pick the retrieval strategy after routing.

        Args:
            state: Current agent state

        Returns:
            Next node name
        """
        routing = state.metadata.get("routing_decision", {})
        use_vector = routing.get("use_vector_search", False)
        use_search = routing.get("use_tavily_search", False)

        if state.intent == "off_topic":
            logger.info("routing_to_direct_generation_off_topic")
            return "direct"

        if use_vector and use_search:
            logger.info("routing_to_both_retrieval_methods")
            return "both"
        elif use_vector:
            logger.info("routing_to_vector_only")
            return "vector_only"
        elif use_search:
            logger.info("routing_to_search_only")
            return "search_only"
        else:
            logger.info("routing_to_direct_generation")
            return "direct"

    async def vector_search_node(self, state: AgentState) -> dict[str, Any]:
        """Retrieve relevant documents from the vector store.

        Args:
            state: Current agent state

        Returns:
            State updates with retrieved documents
        """
        start_time = time.time()
        query = state.query

        logger.info("performing_vector_search", query=query[:100])

        try:
            filters = self._build_vector_filters(state.entities)

            docs = await self.vector_store.similarity_search(
                query=query,
                k=self.config.vector_search_top_k,
                filters=filters,
            )

            retrieved_docs = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": "vector_store",
                }
                for doc in docs
            ]

            elapsed = time.time() - start_time

            logger.info(
                "vector_search_completed",
                docs_retrieved=len(retrieved_docs),
                elapsed_ms=elapsed * 1000,
            )

            return {
                "retrieved_docs": retrieved_docs,
                "metadata": {
                    "vector_search_count": len(retrieved_docs),
                    "vector_search_time_ms": elapsed * 1000,
                },
            }

        except Exception as e:
            logger.error("vector_search_failed", error=str(e))
            return {
                "retrieved_docs": [],
                "metadata": {"vector_search_error": str(e)},
            }

    async def tavily_search_node(self, state: AgentState) -> dict[str, Any]:
        """Retrieve real-time information from Tavily.

        Args:
            state: Current agent state

        Returns:
            State updates with search results
        """
        start_time = time.time()
        query = state.query

        logger.info("performing_tavily_search", query=query[:100])

        try:
            results, error = await self.tavily_client.safe_search(query=query)

            if error:
                logger.warning("tavily_search_unavailable", error=error)
                return {
                    "search_results": [],
                    "metadata": {
                        "tavily_error": error,
                        "tavily_fallback": True,
                    },
                }

            search_results = [
                {
                    "content": result.get("content", ""),
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "score": result.get("score", 0.0),
                    "source": "tavily_search",
                }
                for result in results
            ]

            elapsed = time.time() - start_time

            logger.info(
                "tavily_search_completed",
                results_count=len(search_results),
                elapsed_ms=elapsed * 1000,
            )

            return {
                "search_results": search_results,
                "metadata": {
                    "tavily_search_count": len(search_results),
                    "tavily_search_time_ms": elapsed * 1000,
                },
            }

        except Exception as e:
            logger.error("tavily_search_failed", error=str(e))
            return {
                "search_results": [],
                "metadata": {"tavily_search_error": str(e)},
            }

    async def parallel_retrieval_node(self, state: AgentState) -> dict[str, Any]:
        """Run vector search and Tavily search concurrently.

        Args:
            state: Current agent state

        Returns:
            State updates with both retrieved documents and search results
        """
        start_time = time.time()

        logger.info("performing_parallel_retrieval")

        vector_task = asyncio.create_task(self.vector_search_node(state))
        tavily_task = asyncio.create_task(self.tavily_search_node(state))

        vector_result: dict[str, Any] | BaseException
        tavily_result: dict[str, Any] | BaseException
        vector_result, tavily_result = await asyncio.gather(
            vector_task,
            tavily_task,
            return_exceptions=True,
        )

        retrieved_docs: list[dict[str, Any]] = []
        search_results: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {}

        if isinstance(vector_result, dict):
            retrieved_docs = vector_result.get("retrieved_docs", [])
            metadata.update(vector_result.get("metadata", {}))
        elif isinstance(vector_result, BaseException):
            logger.error("parallel_vector_search_failed", error=str(vector_result))
            metadata["vector_search_error"] = str(vector_result)

        if isinstance(tavily_result, dict):
            search_results = tavily_result.get("search_results", [])
            metadata.update(tavily_result.get("metadata", {}))
        elif isinstance(tavily_result, BaseException):
            logger.error("parallel_tavily_search_failed", error=str(tavily_result))
            metadata["tavily_search_error"] = str(tavily_result)

        elapsed = time.time() - start_time

        logger.info(
            "parallel_retrieval_completed",
            vector_docs=len(retrieved_docs),
            tavily_results=len(search_results),
            elapsed_ms=elapsed * 1000,
        )

        return {
            "retrieved_docs": retrieved_docs,
            "search_results": search_results,
            "metadata": {
                **metadata,
                "parallel_retrieval_time_ms": elapsed * 1000,
            },
        }

    async def rank_context_node(self, state: AgentState) -> dict[str, Any]:
        """Rank retrieved context with multi-factor scoring.

        Each item is scored on relevance, recency, authority, and
        completeness; the top items from each source feed the generation
        context. A typed ``sources`` list is placed in metadata for the
        streaming server to forward to clients.

        Args:
            state: Current agent state

        Returns:
            State updates with ranked context and sources
        """
        retrieved_docs = state.retrieved_docs
        search_results = state.search_results

        logger.info(
            "ranking_context",
            vector_docs=len(retrieved_docs),
            search_results=len(search_results),
        )

        scored_vector: list[tuple[float, dict[str, Any]]] = sorted(
            ((score_context_item(doc).total_score, doc) for doc in retrieved_docs),
            key=lambda pair: pair[0],
            reverse=True,
        )
        scored_search: list[tuple[float, dict[str, Any]]] = sorted(
            (
                (score_context_item(result).total_score, result)
                for result in search_results
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )

        context_parts = []
        sources: list[dict[str, Any]] = []

        if scored_vector:
            context_parts.append("=== Historical Context ===")
            for i, (score, item) in enumerate(scored_vector[:3], 1):
                context_parts.append(
                    f"\n[Historical Source {i}] (Score: {score:.2f})\n"
                    f"{item['content'][:600]}..."
                )
                sources.append(
                    {
                        "kind": "vector",
                        "title": item.get("metadata", {}).get("title")
                        or item.get("metadata", {}).get("source", "knowledge base"),
                        "url": None,
                        "snippet": item["content"][:200],
                        "score": round(score, 4),
                    }
                )

        if scored_search:
            context_parts.append("\n\n=== Current Information ===")
            for i, (score, item) in enumerate(scored_search[:3], 1):
                context_parts.append(
                    f"\n[Current Source {i}] {item.get('title', 'Untitled')} "
                    f"(Score: {score:.2f})\n{item['content'][:600]}..."
                )
                sources.append(
                    {
                        "kind": "web",
                        "title": item.get("title", "Untitled"),
                        "url": item.get("url") or None,
                        "snippet": item["content"][:200],
                        "score": round(score, 4),
                    }
                )

        context = "\n".join(context_parts)
        top_score = max(
            (score for score, _ in scored_vector + scored_search), default=0.0
        )

        logger.info(
            "context_ranked",
            total_items=len(scored_vector) + len(scored_search),
            top_score=top_score,
            context_length=len(context),
        )

        return {
            "context": context,
            "metadata": {
                "sources": sources,
                "scored_items_count": len(scored_vector) + len(scored_search),
                "top_score": top_score,
                "context_length": len(context),
            },
        }

    async def generate_node(self, state: AgentState) -> dict[str, Any]:
        """Generate the response, serving from the LLM cache when possible.

        Cache hits return without invoking the LLM, so a cached request
        emits zero token events on the stream — the NDJSON contract's
        cache-hit semantics fall out of this for free.

        Args:
            state: Current agent state

        Returns:
            State updates with the generated response
        """
        start_time = time.time()
        query = state.query
        context = state.context

        logger.info("generating_response", query=query[:100])

        cache_manager = get_cache_manager()
        cache_key = cache_manager.get_llm_cache_key(
            query=query,
            context=context,
            model=self.config.generation_model,
            temperature=self.config.openai_temperature,
        )

        cached_response = cache_manager.llm_cache.get(cache_key)
        if cached_response is not None:
            elapsed = time.time() - start_time
            logger.info(
                "llm_response_cache_hit",
                query=query[:100],
                elapsed_ms=elapsed * 1000,
            )
            return {
                "response": cached_response,
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=cached_response),
                ],
                "metadata": {
                    "generation_successful": True,
                    "response_length": len(cached_response),
                    "from_cache": True,
                    "generation_time_ms": elapsed * 1000,
                },
            }

        prompt_messages = self._build_prompt(query, context, list(state.messages))

        try:
            # Stream-accumulate so token chunks flow through astream_events
            # (the server forwards them as NDJSON `token` events).
            response_text = ""
            token_usage: dict[str, int] = {}
            async for chunk in self.llm.astream(prompt_messages):
                if chunk.content:
                    response_text += str(chunk.content)
                usage_metadata = getattr(chunk, "usage_metadata", None)
                if usage_metadata:
                    token_usage = {
                        "prompt_tokens": usage_metadata.get("input_tokens", 0),
                        "completion_tokens": usage_metadata.get("output_tokens", 0),
                        "total_tokens": usage_metadata.get("total_tokens", 0),
                    }

            cache_manager.llm_cache.set(cache_key, response_text)

            elapsed = time.time() - start_time

            logger.info(
                "response_generated",
                response_length=len(response_text),
                elapsed_ms=elapsed * 1000,
                **token_usage,
            )

            return {
                "response": response_text,
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=response_text),
                ],
                "metadata": {
                    "generation_successful": True,
                    "response_length": len(response_text),
                    "from_cache": False,
                    "generation_time_ms": elapsed * 1000,
                    "token_usage": token_usage,
                },
            }

        except Exception as e:
            logger.error("generation_failed", error=str(e))
            error_response = (
                "I apologize, but I encountered an error generating a response. "
                "Please try rephrasing your question."
            )
            return {
                "response": error_response,
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=error_response),
                ],
                "metadata": {"generation_error": str(e)},
            }

    def _build_prompt(
        self,
        query: str,
        context: str,
        messages: list[BaseMessage],
    ) -> list[BaseMessage]:
        """Build the generation prompt with a sliding history window.

        Args:
            query: User query
            context: Retrieved context
            messages: Conversation history

        Returns:
            List of prompt messages bounded for token usage
        """
        prompt_messages: list[BaseMessage] = [
            SystemMessage(content=F1_EXPERT_SYSTEM_PROMPT),
        ]

        # Sliding window: last 10 non-system messages (5 exchanges).
        recent_messages = [m for m in messages if m.type != "system"][-10:]
        prompt_messages.extend(recent_messages)

        if context:
            max_context_length = 3000  # ~750 tokens
            if len(context) > max_context_length:
                context = context[:max_context_length] + "\n...[context truncated]"

            user_message = f"""Context:
{context}

Question: {query}

Provide a concise, accurate answer using the context. Cite sources."""
        else:
            user_message = query

        prompt_messages.append(HumanMessage(content=user_message))

        return prompt_messages

    async def format_response_node(self, state: AgentState) -> dict[str, Any]:
        """Format the final response, prepending degradation warnings.

        Args:
            state: Current agent state

        Returns:
            State updates with the formatted response
        """
        response = state.response or ""
        metadata = state.metadata

        logger.info("formatting_response")

        warnings = []

        if metadata.get("tavily_fallback"):
            warnings.append(metadata.get("tavily_error", ""))

        if metadata.get("vector_search_error"):
            warnings.append(
                "Historical context may be limited due to a temporary issue."
            )

        if warnings:
            formatted_response = "\n".join(warnings) + "\n\n" + response
        else:
            formatted_response = response

        logger.info("response_formatted", has_warnings=len(warnings) > 0)

        return {
            "response": formatted_response,
            "metadata": {
                "formatted": True,
                "warnings_count": len(warnings),
            },
        }

    def _build_vector_filters(self, entities: dict[str, Any]) -> dict[str, Any] | None:
        """Build Pinecone metadata filters from extracted entities.

        Args:
            entities: Extracted entities from query analysis

        Returns:
            Pinecone filter dictionary or None
        """
        filters: dict[str, Any] = {}

        if entities.get("years"):
            years = entities["years"]
            if len(years) == 1:
                filters["year"] = int(years[0])
            elif len(years) > 1:
                filters["year"] = {
                    "$gte": int(min(years)),
                    "$lte": int(max(years)),
                }

        if entities.get("drivers"):
            filters["driver"] = entities["drivers"][0]

        if entities.get("teams"):
            filters["team"] = entities["teams"][0]

        return filters if filters else None
