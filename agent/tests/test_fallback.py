"""Tests for graceful degradation when external services fail."""

import time
from unittest.mock import AsyncMock

import pytest

from chatf1_agent.exceptions import RateLimitError, SearchAPIError
from chatf1_agent.retrieval.tavily import TavilyClient
from chatf1_agent.settings import Settings


@pytest.fixture
def client(test_settings: Settings) -> TavilyClient:
    """Tavily client with caching disabled for deterministic tests."""
    return TavilyClient(test_settings, enable_cache=False)


@pytest.mark.unit
class TestFallbackMode:
    """Tests for the Tavily fallback-mode state machine."""

    def test_available_initially(self, client: TavilyClient):
        """A fresh client is available and has no fallback message."""
        assert client.is_available is True
        assert client.get_fallback_message() == ""

    def test_enters_fallback_after_consecutive_failures(self, client: TavilyClient):
        """Three consecutive failures flip the client into fallback mode."""
        for _ in range(3):
            client._record_failure()

        assert client.is_available is False
        message = client.get_fallback_message()
        assert "temporarily unavailable" in message
        assert "historical knowledge" in message

    def test_success_resets_failure_count(self, client: TavilyClient):
        """A success between failures prevents fallback mode."""
        client._record_failure()
        client._record_failure()
        client._record_success()
        client._record_failure()

        assert client.is_available is True

    def test_success_exits_fallback_mode(self, client: TavilyClient):
        """A successful search exits fallback mode immediately."""
        for _ in range(3):
            client._record_failure()
        assert client.is_available is False

        client._record_success()
        assert client.is_available is True

    def test_cooldown_expiry_exits_fallback(self, client: TavilyClient):
        """Fallback mode lifts automatically after the cooldown elapses."""
        for _ in range(3):
            client._record_failure()
        assert client.is_available is False

        client._last_failure_time = time.time() - (client._fallback_cooldown + 1)
        assert client.is_available is True


@pytest.mark.unit
class TestSafeSearch:
    """Tests for safe_search never raising."""

    async def test_skips_search_in_fallback_mode(self, client: TavilyClient):
        """While in fallback mode, safe_search returns instantly with a message."""
        for _ in range(3):
            client._record_failure()

        results, error = await client.safe_search("F1 news")

        assert results == []
        assert error is not None
        assert "temporarily unavailable" in error

    async def test_search_api_error_degrades_gracefully(self, client: TavilyClient):
        """A SearchAPIError yields empty results plus a user-facing message."""
        client.search = AsyncMock(side_effect=SearchAPIError("boom"))  # type: ignore[method-assign]

        results, error = await client.safe_search("F1 news")

        assert results == []
        assert error is not None
        assert "temporarily unavailable" in error

    async def test_rate_limit_error_degrades_gracefully(self, client: TavilyClient):
        """A RateLimitError yields empty results plus a rate-limit message."""
        client.search = AsyncMock(  # type: ignore[method-assign]
            side_effect=RateLimitError("slow down", retry_after=10)
        )

        results, error = await client.safe_search("F1 news")

        assert results == []
        assert error is not None
        assert "rate limit" in error.lower()

    async def test_unexpected_error_degrades_gracefully(self, client: TavilyClient):
        """Any unexpected exception still returns instead of raising."""
        client.search = AsyncMock(side_effect=RuntimeError("surprise"))  # type: ignore[method-assign]

        results, error = await client.safe_search("F1 news")

        assert results == []
        assert error is not None
        assert "unexpected" in error.lower()

    async def test_successful_search_returns_results(self, client: TavilyClient):
        """A healthy search returns results and no error."""
        expected = [{"content": "race recap", "url": "https://formula1.com"}]
        client.search = AsyncMock(return_value=expected)  # type: ignore[method-assign]

        results, error = await client.safe_search("F1 news")

        assert results == expected
        assert error is None
