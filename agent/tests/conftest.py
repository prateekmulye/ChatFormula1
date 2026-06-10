"""Pytest configuration and fixtures for the agent service.

Every test runs with dummy credentials injected by the autouse
``dummy_environment`` fixture — the suite never needs real API keys.
Integration tests that require live services detect the ``test-`` prefix
and skip themselves.
"""

import os
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from chatf1_agent.settings import Settings, get_settings
from chatf1_agent.state import QueryAnalysis

DUMMY_ENV = {
    "OPENAI_API_KEY": "test-openai-key",
    "PINECONE_API_KEY": "test-pinecone-key",
    "TAVILY_API_KEY": "test-tavily-key",
    "INTERNAL_API_TOKEN": "test-internal-token",
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "DEBUG",
}


@pytest.fixture(autouse=True)
def dummy_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Inject dummy credentials and reset the settings cache around each test."""
    for key, value in DUMMY_ENV.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings() -> Settings:
    """Settings built from the dummy environment."""
    return Settings()


# ============================================================================
# Mock factories for external services
# ============================================================================


@pytest.fixture
def mock_vector_store() -> Mock:
    """Vector store mock returning two F1 championship documents."""
    mock = Mock()
    mock.similarity_search = AsyncMock(
        return_value=[
            Document(
                page_content="Lewis Hamilton won the 2020 championship",
                metadata={"year": 2020, "category": "championship", "source": "test"},
            ),
            Document(
                page_content="Max Verstappen won the 2021 championship",
                metadata={"year": 2021, "category": "championship", "source": "test"},
            ),
        ]
    )
    mock.add_documents = AsyncMock(return_value=["doc1", "doc2", "doc3"])
    mock.similarity_search_with_score = AsyncMock(
        return_value=[(Document(page_content="Test doc", metadata={}), 0.95)]
    )
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_tavily_client() -> Mock:
    """Tavily client mock whose safe_search returns one healthy result."""
    mock = Mock()
    mock.safe_search = AsyncMock(
        return_value=(
            [
                {
                    "title": "F1 Race Results",
                    "url": "https://formula1.com/results",
                    "content": "Max Verstappen won the latest race",
                    "score": 0.95,
                }
            ],
            None,
        )
    )
    return mock


class FakeStructuredOutput:
    """Stand-in for an LLM bound to structured output."""

    def __init__(self, analysis: QueryAnalysis) -> None:
        self.analysis = analysis

    async def ainvoke(self, messages: Any) -> QueryAnalysis:
        return self.analysis


class FakeAnalysisLLM:
    """Stand-in for the analysis LLM returning a fixed QueryAnalysis."""

    def __init__(self, analysis: QueryAnalysis) -> None:
        self.analysis = analysis

    def with_structured_output(self, schema: Any) -> FakeStructuredOutput:
        return FakeStructuredOutput(self.analysis)


@pytest.fixture
def make_analysis() -> Any:
    """Factory for QueryAnalysis objects with sane defaults."""

    def _make(**overrides: Any) -> QueryAnalysis:
        defaults: dict[str, Any] = {
            "intent": "current_info",
            "confidence": 0.9,
            "requires_search": True,
            "requires_vector_search": True,
            "entities": {},
            "reasoning": "test analysis",
        }
        defaults.update(overrides)
        return QueryAnalysis(**defaults)

    return _make


@pytest.fixture
def make_generation_llm() -> Any:
    """Factory for a streaming fake generation LLM tagged ``generation``."""

    def _make(text: str = "Max won the race.") -> GenericFakeChatModel:
        return GenericFakeChatModel(
            messages=iter([AIMessage(content=text)]),
            tags=["generation"],
        )

    return _make


# ============================================================================
# Sample data fixtures
# ============================================================================


@pytest.fixture
def sample_documents() -> list[Document]:
    """Three sample F1 documents with metadata."""
    return [
        Document(
            page_content="Lewis Hamilton is a seven-time Formula 1 World Champion.",
            metadata={
                "source": "test",
                "category": "driver_stats",
                "year": 2020,
                "driver": "Lewis Hamilton",
            },
        ),
        Document(
            page_content="Max Verstappen won the 2021 and 2022 championships.",
            metadata={
                "source": "test",
                "category": "championship",
                "year": 2022,
                "driver": "Max Verstappen",
            },
        ),
        Document(
            page_content="Monaco Grand Prix is held on the streets of Monte Carlo.",
            metadata={
                "source": "test",
                "category": "circuit",
                "race": "Monaco Grand Prix",
            },
        ),
    ]


@pytest.fixture
def sample_messages() -> list[Any]:
    """A realistic two-exchange conversation."""
    return [
        HumanMessage(content="Who won the 2021 championship?"),
        AIMessage(content="Max Verstappen won the 2021 Formula 1 World Championship."),
        HumanMessage(content="What about 2020?"),
        AIMessage(content="Lewis Hamilton won the 2020 championship."),
    ]


@pytest.fixture
def sample_search_results() -> list[dict[str, Any]]:
    """Two sample Tavily search results."""
    return [
        {
            "title": "F1 2024 Season Preview",
            "url": "https://formula1.com/2024-preview",
            "content": "The 2024 season promises exciting battles between top teams.",
            "score": 0.92,
            "published_date": "2024-01-15",
        },
        {
            "title": "Latest F1 News",
            "url": "https://formula1.com/news",
            "content": "Breaking news from the world of Formula 1.",
            "score": 0.85,
            "published_date": "2024-03-10",
        },
    ]


def has_real_api_keys() -> bool:
    """True when the environment carries non-dummy API keys."""
    return not any(
        os.environ.get(key, "").startswith("test-")
        for key in ("OPENAI_API_KEY", "PINECONE_API_KEY", "TAVILY_API_KEY")
    )
