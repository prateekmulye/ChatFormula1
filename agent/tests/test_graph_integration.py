"""Integration tests for the LangGraph pipeline.

The full graph runs against faked LLMs and retrieval backends, so these
tests exercise real LangGraph execution without any API keys.
"""

from datetime import datetime
from typing import Any
from unittest.mock import Mock

import pytest

from chatf1_agent.caching import get_cache_manager
from chatf1_agent.graph import F1AgentGraph, score_context_item
from chatf1_agent.settings import Settings
from chatf1_agent.state import AgentState

from .conftest import FakeAnalysisLLM


@pytest.fixture(autouse=True)
def clear_caches():
    """Isolate the global TTL caches between tests."""
    get_cache_manager().clear_all()
    yield
    get_cache_manager().clear_all()


@pytest.fixture
def graph(
    test_settings: Settings,
    mock_vector_store: Mock,
    mock_tavily_client: Mock,
    make_analysis: Any,
    make_generation_llm: Any,
) -> F1AgentGraph:
    """Graph wired to fakes: structured analysis, retrieval, generation."""
    agent = F1AgentGraph(test_settings, mock_vector_store, mock_tavily_client)
    agent.analysis_llm = FakeAnalysisLLM(make_analysis())
    agent.llm = make_generation_llm()
    return agent


@pytest.mark.unit
class TestGraphConstruction:
    """Tests for one-time graph compilation."""

    def test_graph_compiles_once_at_init(self, graph: F1AgentGraph):
        """The compiled graph is built in __init__ and reused."""
        assert graph.compiled_graph is not None
        first = graph.compiled_graph
        assert graph.compiled_graph is first

    def test_generation_llm_carries_generation_tag(
        self, test_settings: Settings, mock_vector_store: Mock, mock_tavily_client: Mock
    ):
        """The generation model is tagged for stream filtering."""
        agent = F1AgentGraph(test_settings, mock_vector_store, mock_tavily_client)

        assert agent.llm.tags == ["generation"]
        assert agent.llm.model_name == "gpt-4o-mini"
        assert agent.analysis_llm.model_name == "gpt-4o-mini"


@pytest.mark.unit
class TestRouting:
    """Tests for the route_decision conditional edge."""

    @pytest.mark.parametrize(
        ("use_vector", "use_search", "expected"),
        [
            (True, True, "both"),
            (True, False, "vector_only"),
            (False, True, "search_only"),
            (False, False, "direct"),
        ],
    )
    def test_route_decision_matrix(
        self, graph: F1AgentGraph, use_vector: bool, use_search: bool, expected: str
    ):
        """Routing follows the analysis flags."""
        state = AgentState(
            query="test",
            metadata={
                "routing_decision": {
                    "use_vector_search": use_vector,
                    "use_tavily_search": use_search,
                }
            },
        )

        assert graph.route_decision(state) == expected

    def test_off_topic_routes_direct(self, graph: F1AgentGraph):
        """Off-topic queries skip retrieval entirely."""
        state = AgentState(
            query="weather in Paris",
            intent="off_topic",
            metadata={
                "routing_decision": {
                    "use_vector_search": True,
                    "use_tavily_search": True,
                }
            },
        )

        assert graph.route_decision(state) == "direct"


@pytest.mark.unit
class TestContextRanking:
    """Tests for the salvaged ContextScore multi-factor ranking."""

    def test_search_results_score_high_recency(self):
        """Live search results get a 0.9 recency score."""
        score = score_context_item(
            {"content": "x" * 600, "source": "tavily_search", "score": 0.8}
        )

        assert score.recency == 0.9
        assert score.completeness == 1.0

    def test_vector_recency_uses_dynamic_year(self):
        """Recency decays from the *current* year, not a hardcoded season."""
        current_year = datetime.now().year
        fresh = score_context_item(
            {
                "content": "x" * 600,
                "source": "vector_store",
                "metadata": {"year": current_year},
            }
        )
        stale = score_context_item(
            {
                "content": "x" * 600,
                "source": "vector_store",
                "metadata": {"year": current_year - 5},
            }
        )

        assert fresh.recency == 1.0
        assert stale.recency == pytest.approx(0.5)
        assert fresh.total_score > stale.total_score

    def test_trusted_domains_get_authority_boost(self):
        """formula1.com outranks unknown domains on authority."""
        trusted = score_context_item(
            {
                "content": "x" * 300,
                "source": "tavily_search",
                "url": "https://formula1.com/article",
            }
        )
        unknown = score_context_item(
            {
                "content": "x" * 300,
                "source": "tavily_search",
                "url": "https://random-blog.example/article",
            }
        )

        assert trusted.authority == 0.9
        assert unknown.authority == 0.7

    def test_weighted_total_score(self):
        """Total score applies the 40/30/20/10 weighting."""
        score = score_context_item(
            {"content": "x" * 600, "source": "tavily_search", "score": 1.0}
        )

        expected = 1.0 * 0.4 + 0.9 * 0.3 + 0.7 * 0.2 + 1.0 * 0.1
        assert score.total_score == pytest.approx(expected)

    async def test_rank_context_emits_typed_sources(self, graph: F1AgentGraph):
        """rank_context publishes a typed sources list for the stream."""
        state = AgentState(
            query="who won?",
            retrieved_docs=[
                {
                    "content": "Verstappen won the 2024 title.",
                    "metadata": {"year": 2024, "title": "2024 season"},
                    "source": "vector_store",
                }
            ],
            search_results=[
                {
                    "content": "Latest race recap",
                    "url": "https://formula1.com/recap",
                    "title": "Race recap",
                    "score": 0.9,
                    "source": "tavily_search",
                }
            ],
        )

        result = await graph.rank_context_node(state)

        sources = result["metadata"]["sources"]
        kinds = {source["kind"] for source in sources}
        assert kinds == {"vector", "web"}
        assert all("score" in source for source in sources)
        assert "Historical Context" in result["context"]
        assert "Current Information" in result["context"]


@pytest.mark.unit
class TestGenerationCaching:
    """Tests for the LLM response cache inside generate_node."""

    async def test_cache_miss_then_hit(self, graph: F1AgentGraph):
        """The second identical generation is served from cache."""
        state = AgentState(query="Who won the last race?", context="")

        first = await graph.generate_node(state)
        assert first["metadata"]["from_cache"] is False

        second = await graph.generate_node(state)
        assert second["metadata"]["from_cache"] is True
        assert second["response"] == first["response"]


@pytest.mark.unit
class TestFullGraphRuns:
    """End-to-end graph execution with fakes."""

    async def test_full_run_produces_response(self, graph: F1AgentGraph):
        """A query flows through retrieval to a generated response."""
        state = AgentState(query="Who won the last race?")

        result = await graph.compiled_graph.ainvoke(state)

        assert result["response"] == "Max won the race."
        assert result["metadata"]["formatted"] is True
        assert result["metadata"]["sources"]

    async def test_degraded_search_prepends_warning(
        self,
        test_settings: Settings,
        mock_vector_store: Mock,
        make_analysis: Any,
        make_generation_llm: Any,
    ):
        """A Tavily outage surfaces as a warning, not a failure."""
        from unittest.mock import AsyncMock

        offline_tavily = Mock()
        offline_tavily.safe_search = AsyncMock(
            return_value=([], "Real-time search is temporarily unavailable.")
        )

        graph = F1AgentGraph(test_settings, mock_vector_store, offline_tavily)
        graph.analysis_llm = FakeAnalysisLLM(make_analysis())
        graph.llm = make_generation_llm()

        result = await graph.compiled_graph.ainvoke(
            AgentState(query="Who won the last race?")
        )

        assert result["response"].startswith(
            "Real-time search is temporarily unavailable."
        )
        assert result["metadata"]["warnings_count"] == 1

    async def test_off_topic_skips_retrieval(
        self,
        test_settings: Settings,
        mock_vector_store: Mock,
        mock_tavily_client: Mock,
        make_analysis: Any,
        make_generation_llm: Any,
    ):
        """Off-topic queries go straight to generation."""
        graph = F1AgentGraph(test_settings, mock_vector_store, mock_tavily_client)
        graph.analysis_llm = FakeAnalysisLLM(
            make_analysis(
                intent="off_topic",
                requires_search=False,
                requires_vector_search=False,
            )
        )
        graph.llm = make_generation_llm("I specialize in Formula 1 racing.")

        result = await graph.compiled_graph.ainvoke(
            AgentState(query="What is the weather in Paris?")
        )

        mock_vector_store.similarity_search.assert_not_awaited()
        mock_tavily_client.safe_search.assert_not_awaited()
        assert "Formula 1" in result["response"]
