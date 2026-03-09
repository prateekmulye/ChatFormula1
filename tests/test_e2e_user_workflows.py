"""End-to-end tests for complete user workflows.

These tests simulate real user interactions and test the entire system.
"""

import pytest
from langchain_core.messages import HumanMessage

from src.agent.graph import F1AgentGraph
from src.agent.state import AgentState
from src.config.settings import Settings


@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserConversationFlows:
    """End-to-end tests for user conversation flows."""

    @pytest.fixture
    async def agent(self, test_settings: Settings):
        """Create agent for E2E testing."""
        # Skip if no real API keys
        if (
            test_settings.openai_api_key.startswith("test-")
            or test_settings.pinecone_api_key.startswith("test-")
            or test_settings.tavily_api_key.startswith("test-")
        ):
            pytest.skip("Skipping E2E test - no real API keys")

        graph = F1AgentGraph(test_settings)
        await graph.initialize()
        return graph

    async def test_current_standings_query(self, agent: F1AgentGraph):
        """Test user asking about current standings."""
        # User asks about current standings
        state: AgentState = {
            "messages": [
                HumanMessage(content="What are the current F1 driver standings?")
            ],
            "query": "What are the current F1 driver standings?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-standings"},
        }

        result = await agent.run(state)

        # Should provide standings information
        assert result is not None
        assert "response" in result
        response = result["response"]

        # Response should mention drivers or standings
        assert any(
            keyword in response.lower()
            for keyword in ["driver", "standing", "points", "position"]
        )

    async def test_historical_query(self, agent: F1AgentGraph):
        """Test user asking about historical data."""
        state: AgentState = {
            "messages": [
                HumanMessage(content="Who won the 2020 F1 World Championship?")
            ],
            "query": "Who won the 2020 F1 World Championship?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-historical"},
        }

        result = await agent.run(state)

        # Should mention Lewis Hamilton (2020 champion)
        assert result is not None
        response = result["response"]
        assert "hamilton" in response.lower() or "2020" in response

    async def test_multi_turn_conversation_with_context(self, agent: F1AgentGraph):
        """Test multi-turn conversation maintaining context."""
        session_id = "e2e-multi-turn"

        # Turn 1: Ask about a driver
        state1: AgentState = {
            "messages": [HumanMessage(content="Tell me about Max Verstappen")],
            "query": "Tell me about Max Verstappen",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": session_id},
        }

        result1 = await agent.run(state1)
        assert result1 is not None

        # Turn 2: Follow-up question (using context)
        messages = [
            HumanMessage(content="Tell me about Max Verstappen"),
            result1.get("messages", [])[-1] if "messages" in result1 else None,
            HumanMessage(content="How many championships has he won?"),
        ]

        state2: AgentState = {
            "messages": [m for m in messages if m is not None],
            "query": "How many championships has he won?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": session_id},
        }

        result2 = await agent.run(state2)

        # Should understand "he" refers to Verstappen
        assert result2 is not None
        response2 = result2["response"]
        assert any(
            keyword in response2.lower()
            for keyword in ["championship", "title", "verstappen"]
        )

    async def test_prediction_request(self, agent: F1AgentGraph):
        """Test user requesting race prediction."""
        state: AgentState = {
            "messages": [
                HumanMessage(content="Predict the winner of the next Monaco Grand Prix")
            ],
            "query": "Predict the winner of the next Monaco Grand Prix",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-prediction"},
        }

        result = await agent.run(state)

        # Should provide prediction with reasoning
        assert result is not None
        response = result["response"]

        # Should mention Monaco or prediction-related terms
        assert any(
            keyword in response.lower()
            for keyword in ["monaco", "predict", "likely", "chance"]
        )

    async def test_technical_question(self, agent: F1AgentGraph):
        """Test user asking technical F1 question."""
        state: AgentState = {
            "messages": [HumanMessage(content="What is DRS in Formula 1?")],
            "query": "What is DRS in Formula 1?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-technical"},
        }

        result = await agent.run(state)

        # Should explain DRS
        assert result is not None
        response = result["response"]
        assert "drs" in response.lower() or "drag reduction" in response.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPredictionWorkflow:
    """End-to-end tests for prediction generation workflow."""

    @pytest.fixture
    async def agent(self, test_settings: Settings):
        """Create agent for E2E testing."""
        if (
            test_settings.openai_api_key.startswith("test-")
            or test_settings.pinecone_api_key.startswith("test-")
            or test_settings.tavily_api_key.startswith("test-")
        ):
            pytest.skip("Skipping E2E test - no real API keys")

        graph = F1AgentGraph(test_settings)
        await graph.initialize()
        return graph

    async def test_race_prediction_with_reasoning(self, agent: F1AgentGraph):
        """Test complete race prediction workflow."""
        state: AgentState = {
            "messages": [HumanMessage(content="Who will win the next race and why?")],
            "query": "Who will win the next race and why?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-race-prediction"},
        }

        result = await agent.run(state)

        assert result is not None
        response = result["response"]

        # Should provide prediction with reasoning
        assert len(response) > 100  # Should be detailed
        assert any(
            keyword in response.lower()
            for keyword in ["because", "due to", "based on", "considering"]
        )

    async def test_championship_scenario(self, agent: F1AgentGraph):
        """Test championship scenario prediction."""
        state: AgentState = {
            "messages": [
                HumanMessage(
                    content="What are the championship scenarios for the final race?"
                )
            ],
            "query": "What are the championship scenarios for the final race?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-championship"},
        }

        result = await agent.run(state)

        assert result is not None
        response = result["response"]

        # Should discuss championship scenarios
        assert any(
            keyword in response.lower()
            for keyword in ["championship", "scenario", "points", "position"]
        )


@pytest.mark.e2e
@pytest.mark.asyncio
class TestErrorScenarios:
    """End-to-end tests for error scenarios and recovery."""

    @pytest.fixture
    async def agent(self, test_settings: Settings):
        """Create agent for E2E testing."""
        if (
            test_settings.openai_api_key.startswith("test-")
            or test_settings.pinecone_api_key.startswith("test-")
            or test_settings.tavily_api_key.startswith("test-")
        ):
            pytest.skip("Skipping E2E test - no real API keys")

        graph = F1AgentGraph(test_settings)
        await graph.initialize()
        return graph

    async def test_off_topic_query_redirect(self, agent: F1AgentGraph):
        """Test handling of off-topic queries."""
        state: AgentState = {
            "messages": [HumanMessage(content="What is the capital of France?")],
            "query": "What is the capital of France?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-off-topic"},
        }

        result = await agent.run(state)

        # Should redirect to F1 topics
        assert result is not None
        response = result["response"]
        assert any(
            keyword in response.lower()
            for keyword in ["f1", "formula 1", "racing", "specialize"]
        )

    async def test_ambiguous_query_clarification(self, agent: F1AgentGraph):
        """Test handling of ambiguous queries."""
        state: AgentState = {
            "messages": [HumanMessage(content="Who won?")],
            "query": "Who won?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-ambiguous"},
        }

        result = await agent.run(state)

        # Should ask for clarification or provide recent winner
        assert result is not None
        response = result["response"]
        assert len(response) > 0

    async def test_recovery_after_error(self, agent: F1AgentGraph):
        """Test system recovery after error."""
        # First query that might cause issues
        state1: AgentState = {
            "messages": [HumanMessage(content="")],
            "query": "",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-recovery"},
        }

        try:
            await agent.run(state1)
        except Exception:  # noqa: S110
            pass  # Expected to fail

        # Follow-up query should work
        state2: AgentState = {
            "messages": [HumanMessage(content="Who is Lewis Hamilton?")],
            "query": "Who is Lewis Hamilton?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-recovery"},
        }

        result2 = await agent.run(state2)

        # Should recover and work normally
        assert result2 is not None
        assert "response" in result2


@pytest.mark.e2e
@pytest.mark.asyncio
class TestComplexConversations:
    """End-to-end tests for complex conversation scenarios."""

    @pytest.fixture
    async def agent(self, test_settings: Settings):
        """Create agent for E2E testing."""
        if (
            test_settings.openai_api_key.startswith("test-")
            or test_settings.pinecone_api_key.startswith("test-")
            or test_settings.tavily_api_key.startswith("test-")
        ):
            pytest.skip("Skipping E2E test - no real API keys")

        graph = F1AgentGraph(test_settings)
        await graph.initialize()
        return graph

    async def test_comparison_query(self, agent: F1AgentGraph):
        """Test comparing drivers or teams."""
        state: AgentState = {
            "messages": [
                HumanMessage(content="Compare Lewis Hamilton and Max Verstappen")
            ],
            "query": "Compare Lewis Hamilton and Max Verstappen",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-comparison"},
        }

        result = await agent.run(state)

        assert result is not None
        response = result["response"]

        # Should mention both drivers
        assert "hamilton" in response.lower()
        assert "verstappen" in response.lower()

    async def test_statistical_query(self, agent: F1AgentGraph):
        """Test query requiring statistical analysis."""
        state: AgentState = {
            "messages": [
                HumanMessage(
                    content="How many pole positions does Lewis Hamilton have?"
                )
            ],
            "query": "How many pole positions does Lewis Hamilton have?",
            "intent": None,
            "entities": None,
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {"session_id": "e2e-stats"},
        }

        result = await agent.run(state)

        assert result is not None
        response = result["response"]

        # Should provide numerical answer
        assert any(char.isdigit() for char in response)
        assert "pole" in response.lower() or "hamilton" in response.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
