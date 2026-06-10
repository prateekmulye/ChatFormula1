"""Tests for Tavily search client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config.settings import Settings
from src.exceptions import RateLimitError, SearchAPIError
from src.search.tavily_client import TavilyClient


@pytest.fixture
def tavily_client(test_settings: Settings) -> TavilyClient:
    """Create a TavilyClient instance for testing."""
    return TavilyClient(test_settings)


@pytest.fixture
def mock_search_results() -> list[dict]:
    """Mock search results from Tavily API."""
    return [
        {
            "title": "Max Verstappen wins 2024 Championship",
            "url": "https://formula1.com/verstappen-champion",
            "content": "Max Verstappen secured his fourth consecutive championship...",
            "raw_content": "Max Verstappen secured his fourth consecutive championship with a dominant performance...",
            "score": 0.95,
            "published_date": "2024-11-24",
        },
        {
            "title": "F1 2024 Season Review",
            "url": "https://autosport.com/f1-2024-review",
            "content": "The 2024 Formula 1 season was marked by...",
            "raw_content": "The 2024 Formula 1 season was marked by intense competition...",
            "score": 0.88,
            "published_date": "2024-11-25",
        },
    ]


@pytest.mark.unit
def test_tavily_client_initialization(test_settings: Settings):
    """Test TavilyClient initialization."""
    client = TavilyClient(test_settings)

    assert client.settings == test_settings
    assert client.is_available is True
    assert client._consecutive_failures == 0
    assert client._fallback_mode is False


@pytest.mark.unit
def test_tavily_client_custom_rate_limits(test_settings: Settings):
    """Test TavilyClient with custom rate limits."""
    client = TavilyClient(
        test_settings,
        rate_limit_requests=30,
        rate_limit_window=120.0,
    )

    assert client._rate_limit_requests == 30
    assert client._rate_limit_window == 120.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_success(
    tavily_client: TavilyClient, mock_search_results: list[dict]
):
    """Test successful search operation."""
    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        return_value=mock_search_results,
    ):
        results = await tavily_client.search("Max Verstappen championship")

        assert len(results) == 2
        assert results[0]["title"] == "Max Verstappen wins 2024 Championship"
        assert tavily_client._consecutive_failures == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_overrides(
    tavily_client: TavilyClient, mock_search_results: list[dict]
):
    """Test search with parameter overrides."""
    with patch("src.search.tavily_client.TavilySearchResults") as mock_tool_class:
        mock_tool = MagicMock()
        mock_tool.ainvoke = AsyncMock(return_value=mock_search_results)
        mock_tool_class.return_value = mock_tool

        results = await tavily_client.search(
            "F1 news",
            max_results=10,
            include_answer=False,
            search_depth="basic",
        )

        assert len(results) == 2
        mock_tool_class.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_failure_records_failure(tavily_client: TavilyClient):
    """Test that search failures are recorded."""
    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        side_effect=Exception("API Error"),
    ):
        with pytest.raises(SearchAPIError):
            await tavily_client.search("test query")

        assert tavily_client._consecutive_failures == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_mode_after_consecutive_failures(tavily_client: TavilyClient):
    """Test that client enters fallback mode after consecutive failures."""
    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        side_effect=Exception("API Error"),
    ):
        # Trigger 3 consecutive failures
        for _ in range(3):
            with pytest.raises(SearchAPIError):
                await tavily_client.search("test query")

        assert tavily_client._fallback_mode is True
        assert tavily_client.is_available is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_safe_search_returns_empty_on_failure(tavily_client: TavilyClient):
    """Test that safe_search returns empty results on failure."""
    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        side_effect=Exception("API Error"),
    ):
        results, error = await tavily_client.safe_search("test query")

        assert results == []
        assert error is not None
        assert "unavailable" in error.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_safe_search_in_fallback_mode(tavily_client: TavilyClient):
    """Test safe_search behavior when in fallback mode."""
    tavily_client._fallback_mode = True

    results, error = await tavily_client.safe_search("test query")

    assert results == []
    assert error is not None
    assert "temporarily unavailable" in error.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_context(
    tavily_client: TavilyClient, mock_search_results: list[dict]
):
    """Test contextual search."""
    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        return_value=mock_search_results,
    ):
        result = await tavily_client.search_with_context(
            "championship",
            context="2024 season",
        )

        assert result["query"] == "championship"
        assert result["context"] == "2024 season"
        assert len(result["results"]) == 2


@pytest.mark.unit
def test_convert_to_documents(
    tavily_client: TavilyClient, mock_search_results: list[dict]
):
    """Test conversion of search results to documents."""
    documents = tavily_client.convert_to_documents(mock_search_results)

    assert len(documents) == 2
    assert documents[0].page_content == mock_search_results[0]["raw_content"]
    assert documents[0].metadata["source"] == mock_search_results[0]["url"]
    assert documents[0].metadata["title"] == mock_search_results[0]["title"]
    assert documents[0].metadata["score"] == mock_search_results[0]["score"]


@pytest.mark.unit
def test_convert_to_documents_with_deduplication(tavily_client: TavilyClient):
    """Test document conversion with deduplication."""
    duplicate_results = [
        {
            "title": "Test Article",
            "url": "https://example.com/article",
            "content": "Test content",
            "raw_content": "Test content",
            "score": 0.9,
        },
        {
            "title": "Test Article Duplicate",
            "url": "https://example.com/article",  # Same URL
            "content": "Test content",
            "raw_content": "Test content",
            "score": 0.85,
        },
    ]

    documents = tavily_client.convert_to_documents(duplicate_results, deduplicate=True)

    assert len(documents) == 1  # Duplicate removed


@pytest.mark.unit
def test_parse_and_normalize_result(tavily_client: TavilyClient):
    """Test result parsing and normalization."""
    result = {
        "title": "  Test Title  ",
        "url": "https://example.com",
        "content": "  Test content  ",
        "score": 0.95,
        "published_date": "2024-11-24",
    }

    normalized = tavily_client._parse_and_normalize_result(result)

    assert normalized is not None
    assert normalized["title"] == "Test Title"
    assert normalized["content"] == "Test content"
    assert normalized["score"] == 0.95


@pytest.mark.unit
def test_parse_result_with_invalid_score(tavily_client: TavilyClient):
    """Test that invalid scores are clamped to valid range."""
    result = {
        "title": "Test",
        "url": "https://example.com",
        "content": "Test content",
        "score": 1.5,  # Invalid score > 1.0
    }

    normalized = tavily_client._parse_and_normalize_result(result)

    assert normalized is not None
    assert 0.0 <= normalized["score"] <= 1.0


@pytest.mark.unit
def test_parse_result_missing_url(tavily_client: TavilyClient):
    """Test that results without URL are rejected."""
    result = {
        "title": "Test",
        "content": "Test content",
        # Missing URL
    }

    normalized = tavily_client._parse_and_normalize_result(result)

    assert normalized is None


@pytest.mark.unit
def test_parse_result_empty_content(tavily_client: TavilyClient):
    """Test that results with empty content are rejected."""
    result = {
        "title": "Test",
        "url": "https://example.com",
        "content": "   ",  # Empty after strip
    }

    normalized = tavily_client._parse_and_normalize_result(result)

    assert normalized is None


@pytest.mark.unit
def test_get_fallback_message(tavily_client: TavilyClient):
    """Test fallback message generation."""
    # Not in fallback mode
    assert tavily_client.get_fallback_message() == ""

    # Enter fallback mode
    tavily_client._fallback_mode = True
    tavily_client._last_failure_time = asyncio.get_event_loop().time()

    message = tavily_client.get_fallback_message()
    assert "temporarily unavailable" in message.lower()
    assert "historical knowledge" in message.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting(tavily_client: TavilyClient):
    """Test rate limiting functionality."""
    # Set very low rate limit for testing
    tavily_client._rate_limit_requests = 2
    tavily_client._rate_limit_window = 1.0

    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        return_value=[],
    ):
        # First two requests should succeed
        await tavily_client.search("query 1")
        await tavily_client.search("query 2")

        # Third request should hit rate limit
        with pytest.raises(RateLimitError) as exc_info:
            await tavily_client.search("query 3")

        assert exc_info.value.retry_after is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_latest_f1_news(
    tavily_client: TavilyClient, mock_search_results: list[dict]
):
    """Test getting latest F1 news."""
    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        return_value=mock_search_results,
    ):
        news = await tavily_client.get_latest_f1_news(
            "Monaco Grand Prix", max_results=3
        )

        assert len(news) == 2
        assert news[0]["title"] == "Max Verstappen wins 2024 Championship"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawl_f1_source(tavily_client: TavilyClient):
    """Test crawling an F1 source."""
    mock_result = [
        {
            "url": "https://formula1.com/article",
            "title": "Test Article",
            "content": "Short content",
            "raw_content": "Full article content with more details...",
            "score": 0.9,
        }
    ]

    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        documents = await tavily_client.crawl_f1_source("https://formula1.com/article")

        assert len(documents) == 1
        assert documents[0].page_content == "Full article content with more details..."
        assert documents[0].metadata["source"] == "https://formula1.com/article"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_map_f1_domain(
    tavily_client: TavilyClient, mock_search_results: list[dict]
):
    """Test mapping an F1 domain."""
    with patch.object(
        tavily_client.search_tool,
        "ainvoke",
        new_callable=AsyncMock,
        return_value=mock_search_results,
    ):
        pages = await tavily_client.map_f1_domain("autosport.com", "2024 season")

        assert len(pages) == 2
        assert pages[0]["title"] == "Max Verstappen wins 2024 Championship"
