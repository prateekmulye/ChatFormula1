from unittest.mock import MagicMock, patch
import pytest

# We use a context manager to temporarily mock modules just for the import
def import_f1_agent_graph():
    mock_structlog = MagicMock()
    mock_structlog.get_logger.return_value = MagicMock()

    mock_modules = {
        "structlog": mock_structlog,
        "structlog.types": MagicMock(),
        "pydantic": MagicMock(),
        "pydantic_settings": MagicMock(),
        "langchain": MagicMock(),
        "langchain_core": MagicMock(),
        "langchain_core.messages": MagicMock(),
        "langchain_core.prompts": MagicMock(),
        "langchain_openai": MagicMock(),
        "langgraph": MagicMock(),
        "langgraph.checkpoint": MagicMock(),
        "langgraph.checkpoint.memory": MagicMock(),
        "langgraph.graph": MagicMock(),
        "langchain_community": MagicMock(),
        "langchain_community.tools": MagicMock(),
        "langchain_community.tools.tavily_search": MagicMock(),
        "src.prompts.system_prompts": MagicMock(),
        "src.utils.cache": MagicMock(),
        "src.agent.state": MagicMock(),
        "src.config.settings": MagicMock(),
        "src.search.tavily_client": MagicMock(),
        "src.vector_store.manager": MagicMock(),
    }

    with patch.dict("sys.modules", mock_modules):
        from src.agent.graph import F1AgentGraph
        return F1AgentGraph

F1AgentGraph = import_f1_agent_graph()

class FakeAgentState:
    """A minimal fake AgentState for testing route_decision."""
    def __init__(self, intent=None, routing_decision=None):
        self.intent = intent
        self.metadata = {"routing_decision": routing_decision or {}}

class TestRouteDecision:
    @pytest.fixture
    def agent_graph(self):
        """Fixture to provide a partially mocked F1AgentGraph instance."""
        config = MagicMock()
        vector_store = MagicMock()
        tavily_client = MagicMock()

        with patch.object(F1AgentGraph, '_initialize_tools', return_value=None), \
             patch.object(F1AgentGraph, '_build_graph', return_value=MagicMock()):
            return F1AgentGraph(config, vector_store, tavily_client)

    def test_route_decision_off_topic(self, agent_graph):
        """Test that off-topic queries are routed directly to generation."""
        state = FakeAgentState(
            intent="off_topic",
            routing_decision={"use_vector_search": True, "use_tavily_search": True}
        )

        result = agent_graph.route_decision(state)
        assert result == "direct"

    def test_route_decision_both(self, agent_graph):
        """Test routing to both retrieval methods when requested."""
        state = FakeAgentState(
            intent="historical",
            routing_decision={"use_vector_search": True, "use_tavily_search": True}
        )

        result = agent_graph.route_decision(state)
        assert result == "both"

    def test_route_decision_vector_only(self, agent_graph):
        """Test routing to vector search only."""
        state = FakeAgentState(
            intent="historical",
            routing_decision={"use_vector_search": True, "use_tavily_search": False}
        )

        result = agent_graph.route_decision(state)
        assert result == "vector_only"

    def test_route_decision_search_only(self, agent_graph):
        """Test routing to search only."""
        state = FakeAgentState(
            intent="current_info",
            routing_decision={"use_vector_search": False, "use_tavily_search": True}
        )

        result = agent_graph.route_decision(state)
        assert result == "search_only"

    def test_route_decision_direct_none(self, agent_graph):
        """Test routing directly to generation when no search is needed."""
        state = FakeAgentState(
            intent="general",
            routing_decision={"use_vector_search": False, "use_tavily_search": False}
        )

        result = agent_graph.route_decision(state)
        assert result == "direct"

    def test_route_decision_missing_metadata(self, agent_graph):
        """Test graceful handling of missing routing decision in metadata."""
        state = FakeAgentState(intent="general")
        state.metadata = {}

        result = agent_graph.route_decision(state)
        assert result == "direct"
