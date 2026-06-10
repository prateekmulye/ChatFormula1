"""Integration tests for LangGraph agent flow.

These tests require actual API credentials and test the complete agent workflow.
"""

import pytest
from langchain_core.messages import HumanMessage

from src.agent.graph import F1AgentGraph
from src.agent.state import AgentState
from src.config.settings import Settings


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentGraphIntegration:
    """Integration tests for F1AgentGraph."""

    @pytest.fixture
    async def agent_graph(self, test_settings: Settings):
        """Create agent graph for testing."""
        # Skip if no real API keys
        if (
            test_settings.openai_api_key.startswith("test-")
            or test_settings.pinecone_api_key.startswith("test-")
            or test_settings.tavily_api_key.startswith("test-")
        ):
            pytest.skip("Skipping integration test - no real API keys")

        graph = F1AgentGraph(test_settings)
        await graph.initialize()
        return graph

    async def test_agent_initialization(self, agent_graph: F1AgentGraph):
        """Test agent can be initialized."""
        assert agent_graph is not None
        assert agent_graph.graph is not None

    async def test_simple_query_flow(self, agent_graph: F1AgentGraph):
        """Test simple query through agent."""
        initial_state: AgentState = {
            "messages": [HumanMessage(content="Who won the 2021 F1 championship?")],
            "query": "Who won the 2021 F1 championship?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "test-session"},
        }

        # Run agent
        result = await agent_graph.run(initial_state)

        assert result is not None
        assert "response" in result
        assert result["response"] is not None

    async def test_query_analysis_node(self, agent_graph: F1AgentGraph):
        """Test query analysis node."""
        state: AgentState = {
            "messages": [HumanMessage(content="Tell me about Lewis Hamilton")],
            "query": "Tell me about Lewis Hamilton",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {},
        }

        # Run query analysis
        result = await agent_graph.analyze_query_node(state)

        assert "intent" in result or "entities" in result

    async def test_multi_turn_conversation(self, agent_graph: F1AgentGraph):
        """Test multi-turn conversation with context."""
        # First query
        state1: AgentState = {
            "messages": [HumanMessage(content="Who won the 2021 championship?")],
            "query": "Who won the 2021 championship?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "test-multi-turn"},
        }

        result1 = await agent_graph.run(state1)

        # Follow-up query
        state2: AgentState = {
            "messages": [
                HumanMessage(content="Who won the 2021 championship?"),
                result1.get("messages", [])[-1] if "messages" in result1 else None,
                HumanMessage(content="What about 2020?"),
            ],
            "query": "What about 2020?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "test-multi-turn"},
        }

        result2 = await agent_graph.run(state2)

        assert result2 is not None
        assert "response" in result2


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentTools:
    """Integration tests for agent tools."""

    async def test_search_current_f1_data_tool(self, test_settings: Settings):
        """Test search_current_f1_data tool."""
        if test_settings.tavily_api_key.startswith("test-"):
            pytest.skip("Skipping integration test - no real Tavily API key")

        from src.tools.f1_tools import search_current_f1_data

        result = await search_current_f1_data("latest F1 race results")

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_query_f1_history_tool(self, test_settings: Settings):
        """Test query_f1_history tool."""
        if test_settings.pinecone_api_key.startswith("test-"):
            pytest.skip("Skipping integration test - no real Pinecone API key")

        from src.tools.f1_tools import query_f1_history

        result = await query_f1_history("Lewis Hamilton championships")

        assert result is not None
        assert isinstance(result, str)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentErrorHandling:
    """Integration tests for agent error handling."""

    async def test_invalid_query_handling(self, test_settings: Settings):
        """Test handling of invalid queries."""
        if test_settings.openai_api_key.startswith("test-"):
            pytest.skip("Skipping integration test - no real OpenAI API key")

        graph = F1AgentGraph(test_settings)
        await graph.initialize()

        # Empty query
        state: AgentState = {
            "messages": [HumanMessage(content="")],
            "query": "",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {},
        }

        # Should handle gracefully
        try:
            result = await graph.run(state)
            assert result is not None
        except Exception as e:
            # Should raise appropriate error
            assert isinstance(e, (ValueError, TypeError))

    async def test_off_topic_query_handling(self, test_settings: Settings):
        """Test handling of off-topic queries."""
        if test_settings.openai_api_key.startswith("test-"):
            pytest.skip("Skipping integration test - no real OpenAI API key")

        graph = F1AgentGraph(test_settings)
        await graph.initialize()

        # Off-topic query
        state: AgentState = {
            "messages": [HumanMessage(content="What is the weather in Paris?")],
            "query": "What is the weather in Paris?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {},
        }

        result = await graph.run(state)

        # Should redirect to F1 topics
        assert result is not None
        response = result.get("response", "")
        assert "F1" in response or "Formula 1" in response


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentPerformance:
    """Integration tests for agent performance."""

    async def test_query_response_time(self, test_settings: Settings):
        """Test agent response time."""
        if test_settings.openai_api_key.startswith("test-"):
            pytest.skip("Skipping integration test - no real OpenAI API key")

        import time

        graph = F1AgentGraph(test_settings)
        await graph.initialize()

        state: AgentState = {
            "messages": [HumanMessage(content="Who is Lewis Hamilton?")],
            "query": "Who is Lewis Hamilton?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {},
        }

        start = time.time()
        result = await graph.run(state)
        elapsed = time.time() - start

        assert result is not None
        # Should respond within reasonable time (< 10 seconds)
        assert elapsed < 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
