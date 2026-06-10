"""Tests for the Tavily client built on langchain-tavily."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_tavily import TavilySearch

from chatf1_agent.exceptions import RateLimitError
from chatf1_agent.retrieval.tavily import TavilyClient
from chatf1_agent.settings import Settings


@pytest.fixture
def client(test_settings: Settings) -> TavilyClient:
    """Tavily client with caching disabled for deterministic tests."""
    return TavilyClient(test_settings, enable_cache=False)


def fake_search_tool(results: list[dict[str, Any]]) -> Mock:
    """Build a fake TavilySearch tool returning a canned response dict."""
    tool = Mock(spec=TavilySearch)
    tool.ainvoke = AsyncMock(
        return_value={
            "query": "test",
            "results": results,
            "response_time": 0.1,
        }
    )
    return tool


@pytest.mark.unit
class TestClientConstruction:
    """Tests for client and search-tool construction."""

    def test_requires_tavily_api_key(self, monkeypatch: pytest.MonkeyPatch):
        """Construction fails fast without a Tavily key."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        settings = Settings(_env_file=None)

        with pytest.raises(ValueError, match="tavily_api_key"):
            TavilyClient(settings)

    def test_search_tool_is_langchain_tavily(self, client: TavilyClient):
        """The lazily built default tool is a langchain-tavily TavilySearch."""
        tool = client.search_tool

        assert isinstance(tool, TavilySearch)
        assert tool.max_results == client.settings.tavily_max_results
        assert tool.search_depth == client.settings.tavily_search_depth

    def test_search_tool_is_cached(self, client: TavilyClient):
        """The default tool is created once and reused."""
        assert client.search_tool is client.search_tool


@pytest.mark.unit
class TestSearch:
    """Tests for the search call against a faked tool."""

    async def test_search_extracts_results_list(self, client: TavilyClient):
        """search() unwraps the langchain-tavily response envelope."""
        canned = [
            {
                "title": "Race recap",
                "url": "https://formula1.com/recap",
                "content": "Verstappen wins again",
                "score": 0.93,
            }
        ]
        client._search_tool = fake_search_tool(canned)

        results = await client.search("latest F1 race")

        assert results == canned

    async def test_search_handles_list_response(self, client: TavilyClient):
        """A bare list response (legacy shape) is passed through."""
        canned = [{"title": "t", "url": "https://x", "content": "c", "score": 0.5}]
        tool = Mock(spec=TavilySearch)
        tool.ainvoke = AsyncMock(return_value=canned)
        client._search_tool = tool

        results = await client.search("query")

        assert results == canned

    async def test_search_handles_empty_results(self, client: TavilyClient):
        """An empty results envelope yields an empty list."""
        client._search_tool = fake_search_tool([])

        results = await client.search("obscure query")

        assert results == []

    async def test_search_uses_cache(self, test_settings: Settings):
        """Identical queries hit the TTL cache instead of the API."""
        client = TavilyClient(test_settings, enable_cache=True)
        canned = [{"title": "t", "url": "https://x", "content": "c", "score": 0.5}]
        tool = fake_search_tool(canned)
        client._search_tool = tool

        first = await client.search("cached query")
        second = await client.search("cached query")

        assert first == second == canned
        assert tool.ainvoke.await_count == 1


@pytest.mark.unit
class TestRateLimiting:
    """Tests for the sliding-window rate limiter."""

    async def test_rate_limit_raises_when_window_full(self, test_settings: Settings):
        """Exceeding the window raises RateLimitError with retry_after."""
        client = TavilyClient(
            test_settings,
            rate_limit_requests=2,
            rate_limit_window=60.0,
            enable_cache=False,
        )

        await client._check_rate_limit()
        await client._check_rate_limit()

        with pytest.raises(RateLimitError) as exc_info:
            await client._check_rate_limit()

        assert exc_info.value.retry_after is not None
        assert exc_info.value.retry_after > 0

    async def test_requests_within_limit_pass(self, test_settings: Settings):
        """Requests inside the window are admitted."""
        client = TavilyClient(
            test_settings,
            rate_limit_requests=5,
            rate_limit_window=60.0,
            enable_cache=False,
        )

        for _ in range(5):
            await client._check_rate_limit()

        assert len(client._request_timestamps) == 5


@pytest.mark.unit
class TestResultNormalization:
    """Tests for result parsing and document conversion."""

    def test_normalize_valid_result(self, client: TavilyClient):
        """A complete result normalizes with all fields."""
        result = {
            "title": " Race recap ",
            "url": "https://formula1.com/recap",
            "content": " Verstappen wins ",
            "score": 0.9,
            "published_date": "2026-06-01",
        }

        normalized = client._parse_and_normalize_result(result)

        assert normalized is not None
        assert normalized["title"] == "Race recap"
        assert normalized["content"] == "Verstappen wins"
        assert normalized["score"] == 0.9

    def test_normalize_rejects_empty_content(self, client: TavilyClient):
        """Results without content are dropped."""
        assert (
            client._parse_and_normalize_result({"url": "https://x", "content": ""})
            is None
        )

    def test_normalize_rejects_missing_url(self, client: TavilyClient):
        """Results without a URL are dropped."""
        assert client._parse_and_normalize_result({"content": "text"}) is None

    def test_normalize_clamps_out_of_range_score(self, client: TavilyClient):
        """Scores outside [0, 1] are clamped."""
        normalized = client._parse_and_normalize_result(
            {"url": "https://x", "content": "text", "score": 7.5}
        )

        assert normalized is not None
        assert normalized["score"] == 1.0

    def test_convert_to_documents(
        self, client: TavilyClient, sample_search_results: list[dict[str, Any]]
    ):
        """Search results convert to LangChain documents with metadata."""
        documents = client.convert_to_documents(sample_search_results)

        assert len(documents) == 2
        assert documents[0].metadata["source_type"] == "tavily_search"
        assert documents[0].metadata["source"] == sample_search_results[0]["url"]
        assert documents[0].page_content == sample_search_results[0]["content"]

    def test_convert_deduplicates_by_url(self, client: TavilyClient):
        """Duplicate URLs collapse to a single document."""
        duplicate = {
            "title": "Same article",
            "url": "https://formula1.com/article",
            "content": "Body text of the article",
            "score": 0.8,
        }

        documents = client.convert_to_documents([duplicate, dict(duplicate)])

        assert len(documents) == 1

    def test_convert_deduplicates_by_content(self, client: TavilyClient):
        """Identical content under different URLs collapses to one document."""
        first = {
            "title": "A",
            "url": "https://a.example/article",
            "content": "Exactly the same body text",
            "score": 0.8,
        }
        second = {**first, "url": "https://b.example/article", "title": "B"}

        documents = client.convert_to_documents([first, second])

        assert len(documents) == 1
