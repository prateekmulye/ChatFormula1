"""Tests for the prompted-JSON analysis path (non-function-calling models).

When ``supports_function_calling`` is false (the default for Ollama), the
analyze step prompts for strict JSON, retries exactly once with the
validation error appended, and finally falls back to a safe route-to-both
analysis. The NDJSON stream must stay clean in this mode too.
"""

import json
from typing import Any
from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from chatf1_agent.caching import get_cache_manager
from chatf1_agent.graph import F1AgentGraph, _extract_json, safe_default_analysis
from chatf1_agent.server import ChatRequest, stream_chat_events
from chatf1_agent.settings import Settings
from chatf1_agent.state import AgentState

VALID_ANALYSIS_JSON = json.dumps(
    {
        "intent": "current_info",
        "confidence": 0.9,
        "requires_search": True,
        "requires_vector_search": False,
        "entities": {"drivers": ["Max Verstappen"]},
        "time_period": "2026 season",
        "reasoning": "asks about a live result",
    }
)


class FakeJSONLLM:
    """Plain-`ainvoke` fake returning scripted replies in order."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls: list[list[BaseMessage]] = []

    async def ainvoke(self, messages: list[BaseMessage]) -> AIMessage:
        self.calls.append(list(messages))
        return AIMessage(content=self.replies.pop(0))


@pytest.fixture(autouse=True)
def clear_caches():
    """Isolate the global TTL caches between tests."""
    get_cache_manager().clear_all()
    yield
    get_cache_manager().clear_all()


@pytest.fixture
def make_json_graph(
    mock_vector_store: Mock,
    mock_tavily_client: Mock,
    make_generation_llm: Any,
):
    """Factory for a graph running in JSON-analysis mode with fakes."""

    def _make(replies: list[str]) -> tuple[F1AgentGraph, FakeJSONLLM]:
        settings = Settings(_env_file=None, llm_provider="ollama")
        assert settings.supports_function_calling is False

        graph = F1AgentGraph(settings, mock_vector_store, mock_tavily_client)
        fake = FakeJSONLLM(replies)
        graph.analysis_llm = fake  # type: ignore[assignment]
        graph.llm = make_generation_llm()
        return graph, fake

    return _make


@pytest.mark.unit
class TestJsonAnalysisPath:
    """The happy path: the model emits valid JSON on the first try."""

    async def test_valid_json_is_parsed(self, make_json_graph: Any):
        """A valid JSON reply produces a normal analysis in one call."""
        graph, fake = make_json_graph([VALID_ANALYSIS_JSON])

        result = await graph.analyze_query_node(AgentState(query="Who leads?"))

        assert len(fake.calls) == 1
        assert result["intent"] == "current_info"
        assert result["entities"] == {"drivers": ["Max Verstappen"]}
        assert result["metadata"]["analysis_mode"] == "json"
        assert result["metadata"]["requires_search"] is True
        assert result["metadata"]["requires_vector_search"] is False
        assert "analysis_fallback" not in result["metadata"]

    async def test_markdown_fenced_json_is_tolerated(self, make_json_graph: Any):
        """A fenced ```json reply still parses."""
        graph, fake = make_json_graph(["```json\n" + VALID_ANALYSIS_JSON + "\n```"])

        result = await graph.analyze_query_node(AgentState(query="Who leads?"))

        assert len(fake.calls) == 1
        assert result["intent"] == "current_info"

    async def test_prompt_carries_schema_and_json_demand(self, make_json_graph: Any):
        """The system prompt embeds the schema and forbids prose."""
        graph, fake = make_json_graph([VALID_ANALYSIS_JSON])

        await graph.analyze_query_node(AgentState(query="Who leads?"))

        system_text = str(fake.calls[0][0].content)
        assert "JSON Schema" in system_text
        assert "requires_vector_search" in system_text  # schema made it in


@pytest.mark.unit
class TestJsonAnalysisRetry:
    """One repair retry with the validation error appended."""

    async def test_invalid_then_valid_json_retries_once(self, make_json_graph: Any):
        """An invalid first reply triggers exactly one corrective call."""
        graph, fake = make_json_graph(["{not json at all", VALID_ANALYSIS_JSON])

        result = await graph.analyze_query_node(AgentState(query="Who leads?"))

        assert len(fake.calls) == 2
        assert result["intent"] == "current_info"
        assert "analysis_fallback" not in result["metadata"]

        # The retry prompt contains the bad reply and the parse error.
        retry_messages = fake.calls[1]
        assert any("{not json at all" in str(m.content) for m in retry_messages)
        last = str(retry_messages[-1].content)
        assert "Validation error" in last
        assert "ONLY the corrected JSON object" in last

    async def test_garbage_twice_falls_back_to_both(self, make_json_graph: Any):
        """Two unusable replies yield the safe default: retrieve from both."""
        graph, fake = make_json_graph(["complete garbage", "still garbage"])

        result = await graph.analyze_query_node(AgentState(query="Who leads?"))

        assert len(fake.calls) == 2  # exactly ONE retry, then give up
        assert result["intent"] == "general"
        assert result["metadata"]["requires_search"] is True
        assert result["metadata"]["requires_vector_search"] is True
        assert result["metadata"]["analysis_fallback"] is True

    async def test_safe_default_routes_both(self):
        """The safe default analysis always routes to both sources."""
        analysis = safe_default_analysis("because tests")

        assert analysis.intent == "general"
        assert analysis.requires_search is True
        assert analysis.requires_vector_search is True
        assert analysis.confidence == 0.0


@pytest.mark.unit
class TestFunctionCallingPathUnchanged:
    """OpenAI-class providers keep the structured-output path."""

    async def test_default_settings_use_function_calling(
        self,
        test_settings: Settings,
        mock_vector_store: Mock,
        mock_tavily_client: Mock,
        make_analysis: Any,
    ):
        """With the OpenAI default, analysis runs via with_structured_output."""
        from .conftest import FakeAnalysisLLM

        graph = F1AgentGraph(test_settings, mock_vector_store, mock_tavily_client)
        graph.analysis_llm = FakeAnalysisLLM(make_analysis())  # type: ignore[assignment]

        result = await graph.analyze_query_node(AgentState(query="Who leads?"))

        assert result["metadata"]["analysis_mode"] == "function_calling"
        assert "analysis_fallback" not in result["metadata"]


@pytest.mark.unit
class TestExtractJson:
    """The lenient JSON extractor."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ('{"a": 1}', '{"a": 1}'),
            ('```json\n{"a": 1}\n```', '{"a": 1}'),
            ('Sure! Here you go: {"a": 1} hope that helps', '{"a": 1}'),
            ("no braces here", "no braces here"),
        ],
    )
    def test_extraction(self, text: str, expected: str):
        """Fences and prose are stripped; brace-less text passes through."""
        assert _extract_json(text) == expected


@pytest.mark.unit
class TestJsonModeStreamContract:
    """The NDJSON stream stays clean when analysis runs in JSON mode."""

    async def test_no_analysis_json_leaks_into_tokens(self, make_json_graph: Any):
        """Tokens carry only generation output; analysis JSON never leaks."""
        graph, _ = make_json_graph([VALID_ANALYSIS_JSON])
        request = ChatRequest(
            message="Who won the last race?", history=[], request_id="json-mode-1"
        )

        events = []
        async for line in stream_chat_events(graph, request):
            events.append(json.loads(line))

        tokens = [e["text"] for e in events if e["event"] == "token"]
        assert tokens, "generation must still stream tokens in JSON mode"
        assert "".join(tokens) == "Max won the race."
        for text in tokens:
            assert "requires_search" not in text
            assert "intent" not in text

        complete = events[-1]
        assert complete["event"] == "complete"
        assert complete["content"] == "Max won the race."
