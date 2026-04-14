"""LangGraph state machine for ChatFormula1 agent orchestration.

This module implements the main agent graph that orchestrates the RAG pipeline,
including query analysis, routing, retrieval, context ranking, and generation.
"""

from typing import Any, Literal, Optional

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.config.settings import Settings
from src.prompts.system_prompts import F1_EXPERT_SYSTEM_PROMPT
from src.search.tavily_client import TavilyClient
from src.vector_store.manager import VectorStoreManager

from .state import AgentState, QueryAnalysis, SearchDecision

logger = structlog.get_logger(__name__)


class F1AgentGraph:
    """LangGraph-based agent for ChatFormula1.

    This class implements a state machine that orchestrates the complete RAG pipeline:
    1. Query Analysis - Detect intent and extract entities
    2. Routing - Decide which retrieval methods to use
    3. Vector Search - Retrieve historical context from Pinecone
    4. Tavily Search - Get real-time F1 information
    5. Context Ranking - Score and rerank retrieved documents
    6. LLM Generation - Generate response with context
    7. Response Formatting - Format and validate output

    The graph uses checkpointing for conversation memory and supports streaming.
    """

    def __init__(
        self,
        config: Settings,
        vector_store: VectorStoreManager,
        tavily_client: TavilyClient,
    ) -> None:
        """Initialize F1 agent graph.

        Args:
            config: Application settings
            vector_store: Initialized vector store manager
            tavily_client: Initialized Tavily search client
        """
        self.config = config
        self.vector_store = vector_store
        self.tavily_client = tavily_client

        # Initialize LLM for generation with optimized parameters
        self.llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=config.openai_temperature,
            max_tokens=config.openai_max_tokens,
            streaming=config.openai_streaming,
            request_timeout=30,  # 30 second timeout
        )

        # Initialize LLM for structured output (query analysis)
        self.analysis_llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=0.0,  # Deterministic for analysis
        )

        # Initialize tools
        self._initialize_tools()

        # Build the graph
        self.graph = self._build_graph()
        self.compiled_graph = None

        logger.info(
            "f1_agent_graph_initialized",
            model=config.openai_model,
            temperature=config.openai_temperature,
        )

    def _initialize_tools(self) -> None:
        """Initialize F1 tools with dependencies."""
        from src.tools.f1_tools import initialize_tools

        # Initialize tools with vector store, settings, and tavily client
        initialize_tools(self.config, self.vector_store, self.tavily_client)

        logger.info("f1_tools_initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine with parallel retrieval optimization.

        Returns:
            Configured StateGraph
        """
        # Initialize graph with AgentState
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("analyze_query", self.analyze_query_node)
        graph.add_node("route", self.route_node)
        graph.add_node("vector_search", self.vector_search_node)
        graph.add_node("tavily_search", self.tavily_search_node)
        graph.add_node("parallel_retrieval", self.parallel_retrieval_node)
        graph.add_node("rank_context", self.rank_context_node)
        graph.add_node("generate", self.generate_node)
        graph.add_node("format_response", self.format_response_node)

        # Set entry point
        graph.set_entry_point("analyze_query")

        # Add edges
        graph.add_edge("analyze_query", "route")

        # Add conditional edges from route node
        graph.add_conditional_edges(
            "route",
            self.route_decision,
            {
                "vector_only": "vector_search",
                "search_only": "tavily_search",
                "both": "parallel_retrieval",  # Use parallel retrieval for both
                "direct": "generate",
            },
        )

        # Vector search flows to ranking
        graph.add_edge("vector_search", "rank_context")

        # Tavily search flows to ranking
        graph.add_edge("tavily_search", "rank_context")

        # Parallel retrieval flows directly to ranking
        graph.add_edge("parallel_retrieval", "rank_context")

        # Ranking flows to generation
        graph.add_edge("rank_context", "generate")

        # Generation flows to formatting
        graph.add_edge("generate", "format_response")

        # Formatting is the end
        graph.add_edge("format_response", END)

        logger.info("langgraph_state_machine_built", parallel_retrieval_enabled=True)

        return graph

    def compile(self, checkpointer: Optional[MemorySaver] = None) -> Any:
        """Compile the graph with optional checkpointing.

        Args:
            checkpointer: Optional MemorySaver for conversation persistence

        Returns:
            Compiled graph ready for execution
        """
        if checkpointer is None:
            checkpointer = MemorySaver()

        self.compiled_graph = self.graph.compile(checkpointer=checkpointer)

        logger.info(
            "langgraph_compiled",
            has_checkpointer=checkpointer is not None,
        )

        return self.compiled_graph

    async def analyze_query_node(self, state: AgentState) -> dict[str, Any]:
        """Analyze user query to detect intent and extract entities.

        Uses structured output with ChatOpenAI to ensure consistent analysis format.

        Args:
            state: Current agent state

        Returns:
            State updates with intent and entities
        """
        query = state.query

        logger.info("analyzing_query", query=query[:100])

        # Create analysis prompt
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
            # Use structured output
            structured_llm = self.analysis_llm.with_structured_output(QueryAnalysis)
            analysis: QueryAnalysis = await structured_llm.ainvoke(
                analysis_prompt.format_messages()
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
            # Fallback to safe defaults
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
        """Determine routing strategy based on query analysis.

        Args:
            state: Current agent state

        Returns:
            State updates with routing decision
        """
        intent = state.intent
        metadata = state.metadata

        requires_search = metadata.get("requires_search", False)
        requires_vector = metadata.get("requires_vector_search", False)

        logger.info(
            "routing_query",
            intent=intent,
            requires_search=requires_search,
            requires_vector=requires_vector,
        )

        # Store routing decision in metadata
        routing_decision = {
            "use_vector_search": requires_vector,
            "use_tavily_search": requires_search,
        }

        return {
            "metadata": {
                "routing_decision": routing_decision,
            },
        }

    def route_decision(
        self, state: AgentState
    ) -> Literal["vector_only", "search_only", "both", "direct"]:
        """Conditional edge function to determine next node after routing.

        Args:
            state: Current agent state

        Returns:
            Next node name
        """
        routing = state.metadata.get("routing_decision", {})
        use_vector = routing.get("use_vector_search", False)
        use_search = routing.get("use_tavily_search", False)

        # Check for off-topic queries
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

    def after_vector_search_decision(
        self, state: AgentState
    ) -> Literal["tavily", "rank"]:
        """Conditional edge after vector search.

        Args:
            state: Current agent state

        Returns:
            Next node name
        """
        routing = state.metadata.get("routing_decision", {})
        use_search = routing.get("use_tavily_search", False)

        if use_search:
            return "tavily"
        else:
            return "rank"

    async def vector_search_node(self, state: AgentState) -> dict[str, Any]:
        """Retrieve relevant documents from vector store with async optimization.

        Args:
            state: Current agent state

        Returns:
            State updates with retrieved documents
        """
        import time

        start_time = time.time()

        query = state.query
        entities = state.entities

        logger.info("performing_vector_search", query=query[:100])

        try:
            # Build metadata filters from entities
            filters = self._build_vector_filters(entities)

            # Perform similarity search (already async)
            docs = await self.vector_store.similarity_search(
                query=query,
                k=self.config.vector_search_top_k,
                filters=filters,
            )

            # Convert to dict format for state
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
                "metadata": {
                    "vector_search_error": str(e),
                },
            }

    async def tavily_search_node(self, state: AgentState) -> dict[str, Any]:
        """Retrieve real-time information from Tavily with async optimization.

        Args:
            state: Current agent state

        Returns:
            State updates with search results
        """
        import time

        start_time = time.time()

        query = state.query

        logger.info("performing_tavily_search", query=query[:100])

        try:
            # Use safe_search for graceful degradation (already async)
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

            # Convert to dict format for state
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
                "metadata": {
                    "tavily_search_error": str(e),
                },
            }

    async def parallel_retrieval_node(self, state: AgentState) -> dict[str, Any]:
        """Perform parallel retrieval from vector store and Tavily for maximum speed.

        This node executes both vector search and Tavily search concurrently,
        significantly reducing total retrieval time.

        Args:
            state: Current agent state

        Returns:
            State updates with both retrieved documents and search results
        """
        import time

        start_time = time.time()

        logger.info("performing_parallel_retrieval")

        # Execute both searches in parallel
        vector_task = asyncio.create_task(self.vector_search_node(state))
        tavily_task = asyncio.create_task(self.tavily_search_node(state))

        # Wait for both to complete
        vector_result, tavily_result = await asyncio.gather(
            vector_task,
            tavily_task,
            return_exceptions=True,
        )

        # Handle results
        retrieved_docs = []
        search_results = []
        metadata = {}

        if isinstance(vector_result, dict):
            retrieved_docs = vector_result.get("retrieved_docs", [])
            metadata.update(vector_result.get("metadata", {}))
        elif isinstance(vector_result, Exception):
            logger.error("parallel_vector_search_failed", error=str(vector_result))
            metadata["vector_search_error"] = str(vector_result)

        if isinstance(tavily_result, dict):
            search_results = tavily_result.get("search_results", [])
            metadata.update(tavily_result.get("metadata", {}))
        elif isinstance(tavily_result, Exception):
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
        """Rank and combine retrieved context from multiple sources.

        Args:
            state: Current agent state

        Returns:
            State updates with ranked context
        """
        retrieved_docs = state.retrieved_docs
        search_results = state.search_results

        logger.info(
            "ranking_context",
            vector_docs=len(retrieved_docs),
            search_results=len(search_results),
        )

        # Combine and rank all sources
        all_sources = []

        # Add vector store docs
        for doc in retrieved_docs:
            all_sources.append(
                {
                    "content": doc["content"],
                    "source": doc.get("metadata", {}).get("source", "vector_store"),
                    "score": 0.8,  # Default score for vector results
                    "type": "historical",
                }
            )

        # Add search results
        for result in search_results:
            all_sources.append(
                {
                    "content": result["content"],
                    "source": result.get("url", "search"),
                    "score": result.get("score", 0.7),
                    "type": "current",
                }
            )

        # Sort by score (descending)
        ranked_sources = sorted(all_sources, key=lambda x: x["score"], reverse=True)

        # Build context string
        context_parts = []

        if retrieved_docs:
            context_parts.append("=== Historical Context ===")
            for i, doc in enumerate(retrieved_docs[:3], 1):  # Top 3
                context_parts.append(f"\n[Source {i}] {doc['content'][:500]}...")

        if search_results:
            context_parts.append("\n\n=== Current Information ===")
            for i, result in enumerate(search_results[:3], 1):  # Top 3
                context_parts.append(
                    f"\n[Source {i}] {result['title']}\n{result['content'][:500]}..."
                )

        context = "\n".join(context_parts)

        logger.info(
            "context_ranked",
            total_sources=len(ranked_sources),
            context_length=len(context),
        )

        return {
            "context": context,
            "metadata": {
                "ranked_sources_count": len(ranked_sources),
                "context_length": len(context),
            },
        }

    async def generate_node(self, state: AgentState) -> dict[str, Any]:
        """Generate response using LLM with optimized caching and token usage.

        Args:
            state: Current agent state

        Returns:
            State updates with generated response
        """
        import time

        start_time = time.time()

        query = state.query
        context = state.context
        messages = state.messages

        logger.info("generating_response", query=query[:100])

        # Check cache first
        from src.utils.cache import get_cache_manager

        cache_manager = get_cache_manager()

        cache_key = cache_manager.get_llm_cache_key(
            query=query,
            context=context,
            model=self.config.openai_model,
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

        # Build optimized prompt with context
        prompt_messages = self._build_optimized_prompt(query, context, messages)

        try:
            # Generate response with token tracking
            response = await self.llm.ainvoke(prompt_messages)
            response_text = response.content

            # Track token usage if available
            token_usage = {}
            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("token_usage", {})
                token_usage = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

            # Cache the response
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
                "metadata": {
                    "generation_error": str(e),
                },
            }

    def _build_optimized_prompt(
        self,
        query: str,
        context: str,
        messages: list,
    ) -> list:
        """Build optimized prompt with token-efficient context.

        Args:
            query: User query
            context: Retrieved context
            messages: Conversation history

        Returns:
            List of prompt messages optimized for token usage
        """
        prompt_messages = [
            SystemMessage(content=F1_EXPERT_SYSTEM_PROMPT),
        ]

        # Add conversation history with sliding window (last 5 exchanges = 10 messages)
        # This prevents token overflow while maintaining context
        recent_messages = [m for m in messages if m.type != "system"][-10:]
        prompt_messages.extend(recent_messages)

        # Optimize context presentation to reduce tokens
        if context:
            # Truncate context if too long (keep most relevant parts)
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

    async def generate_streaming(self, state: AgentState):
        """Generate response with streaming for faster perceived performance.

        This method streams the LLM response token by token, providing
        immediate feedback to users.

        Args:
            state: Current agent state

        Yields:
            Response chunks as they are generated
        """
        query = state.query
        context = state.context
        messages = state.messages

        logger.info("generating_streaming_response", query=query[:100])

        # Build optimized prompt
        prompt_messages = self._build_optimized_prompt(query, context, messages)

        try:
            # Stream response
            full_response = ""
            async for chunk in self.llm.astream(prompt_messages):
                if hasattr(chunk, "content") and chunk.content:
                    full_response += chunk.content
                    yield chunk.content

            # Cache the complete response
            from src.utils.cache import get_cache_manager

            cache_manager = get_cache_manager()

            cache_key = cache_manager.get_llm_cache_key(
                query=query,
                context=context,
                model=self.config.openai_model,
                temperature=self.config.openai_temperature,
            )
            cache_manager.llm_cache.set(cache_key, full_response)

            logger.info(
                "streaming_response_complete",
                response_length=len(full_response),
            )

        except Exception as e:
            logger.error("streaming_generation_failed", error=str(e))
            yield "I apologize, but I encountered an error. Please try again."

    async def format_response_node(self, state: AgentState) -> dict[str, Any]:
        """Format and validate the final response.

        Args:
            state: Current agent state

        Returns:
            State updates with formatted response
        """
        response = state.response
        metadata = state.metadata

        logger.info("formatting_response")

        # Add fallback warnings if applicable
        warnings = []

        if metadata.get("tavily_fallback"):
            warnings.append(metadata.get("tavily_error", ""))

        if metadata.get("vector_search_error"):
            warnings.append(
                "⚠️ Historical context may be limited due to a temporary issue."
            )

        # Prepend warnings to response
        if warnings:
            formatted_response = "\n".join(warnings) + "\n\n" + response
        else:
            formatted_response = response

        logger.info(
            "response_formatted",
            has_warnings=len(warnings) > 0,
        )

        return {
            "response": formatted_response,
            "metadata": {
                "formatted": True,
                "warnings_count": len(warnings),
            },
        }

    def _build_vector_filters(
        self, entities: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Build Pinecone metadata filters from extracted entities.

        Args:
            entities: Extracted entities from query analysis

        Returns:
            Pinecone filter dictionary or None
        """
        filters = {}

        # Add year filter if present
        if "years" in entities and entities["years"]:
            years = entities["years"]
            if len(years) == 1:
                filters["year"] = int(years[0])
            elif len(years) > 1:
                # Use range filter
                filters["year"] = {
                    "$gte": int(min(years)),
                    "$lte": int(max(years)),
                }

        # Add driver filter if present
        if "drivers" in entities and entities["drivers"]:
            # Use first driver for simplicity
            filters["driver"] = entities["drivers"][0]

        # Add team filter if present
        if "teams" in entities and entities["teams"]:
            filters["team"] = entities["teams"][0]

        return filters if filters else None
