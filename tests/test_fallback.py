"""Unit tests for fallback mechanisms."""

import pytest

from src.exceptions import LLMError, SearchAPIError, VectorStoreError
from src.utils.fallback import (CachedResponse, FallbackChain, ResponseCache,
                                ServiceMode, get_degraded_mode_message,
                                get_response_cache)


@pytest.mark.unit
class TestCachedResponse:
    """Tests for CachedResponse class."""

    def test_cached_response_creation(self):
        """Test creating a cached response."""
        data = {"result": "test"}
        cached = CachedResponse(data, ttl_seconds=60)

        assert cached.data == data
        assert cached.cached_at is not None
        assert cached.expires_at is not None

    def test_cached_response_not_expired(self):
        """Test cached response is not expired immediately."""
        cached = CachedResponse("test", ttl_seconds=60)

        assert cached.is_expired() is False

    def test_cached_response_age(self):
        """Test getting age of cached response."""
        cached = CachedResponse("test", ttl_seconds=60)

        age = cached.get_age_seconds()

        assert age >= 0
        assert age < 1  # Should be very recent


@pytest.mark.unit
class TestResponseCache:
    """Tests for ResponseCache class."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = ResponseCache(default_ttl=300)

        assert cache._default_ttl == 300
        assert len(cache._cache) == 0

    def test_cache_set_and_get(self):
        """Test setting and getting cached values."""
        cache = ResponseCache()

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = ResponseCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_cache_with_custom_ttl(self):
        """Test caching with custom TTL."""
        cache = ResponseCache(default_ttl=300)

        cache.set("key1", "value1", ttl=600)

        # Should be cached
        assert cache.get("key1") == "value1"

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = ResponseCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert len(cache._cache) == 2

        cache.clear()

        assert len(cache._cache) == 0
        assert cache.get("key1") is None

    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = ResponseCache()

        # Add entry with very short TTL
        cache.set("key1", "value1", ttl=0)
        cache.set("key2", "value2", ttl=3600)

        # Cleanup expired
        removed = cache.cleanup_expired()

        # At least one should be removed (key1 with 0 TTL)
        assert removed >= 0
        assert cache.get("key2") == "value2"

    def test_get_response_cache_singleton(self):
        """Test global cache instance."""
        cache1 = get_response_cache()
        cache2 = get_response_cache()

        # Should be same instance
        assert cache1 is cache2


@pytest.mark.unit
class TestFallbackChain:
    """Tests for FallbackChain class."""

    @pytest.mark.asyncio
    async def test_fallback_chain_primary_success(self):
        """Test fallback chain with successful primary."""

        async def primary():
            return "primary_result"

        async def fallback1():
            return "fallback1_result"

        chain = FallbackChain(
            primary=primary,
            fallbacks=[fallback1],
            use_cache=False,
        )

        result, mode = await chain.execute()

        assert result == "primary_result"
        assert mode == ServiceMode.FULL

    @pytest.mark.asyncio
    async def test_fallback_chain_primary_fails(self):
        """Test fallback chain when primary fails."""

        async def primary():
            raise SearchAPIError("Primary failed")

        async def fallback1():
            return "fallback1_result"

        chain = FallbackChain(
            primary=primary,
            fallbacks=[fallback1],
            use_cache=False,
        )

        result, mode = await chain.execute()

        assert result == "fallback1_result"
        assert mode == ServiceMode.DEGRADED

    @pytest.mark.asyncio
    async def test_fallback_chain_all_fail(self):
        """Test fallback chain when all attempts fail."""

        async def primary():
            raise SearchAPIError("Primary failed")

        async def fallback1():
            raise SearchAPIError("Fallback1 failed")

        chain = FallbackChain(
            primary=primary,
            fallbacks=[fallback1],
            use_cache=False,
        )

        with pytest.raises(SearchAPIError):
            await chain.execute()

    @pytest.mark.asyncio
    async def test_fallback_chain_with_args(self):
        """Test fallback chain with arguments."""

        async def primary(x, y):
            return x + y

        async def fallback1(x, y):
            return x * y

        chain = FallbackChain(
            primary=primary,
            fallbacks=[fallback1],
            use_cache=False,
        )

        result, mode = await chain.execute(2, 3)

        assert result == 5
        assert mode == ServiceMode.FULL

    @pytest.mark.asyncio
    async def test_fallback_chain_with_cache(self):
        """Test fallback chain with caching."""
        call_count = 0

        async def primary():
            nonlocal call_count
            call_count += 1
            return "result"

        def cache_key_fn():
            return "test_key"

        chain = FallbackChain(
            primary=primary,
            fallbacks=[],
            cache_key_fn=cache_key_fn,
            use_cache=True,
        )

        # First call
        result1, mode1 = await chain.execute()
        assert result1 == "result"
        assert call_count == 1

        # Second call should use cache
        result2, mode2 = await chain.execute()
        assert result2 == "result"
        assert call_count == 1  # Should not increment

    @pytest.mark.asyncio
    async def test_fallback_chain_multiple_fallbacks(self):
        """Test fallback chain with multiple fallbacks."""

        async def primary():
            raise SearchAPIError("Primary failed")

        async def fallback1():
            raise SearchAPIError("Fallback1 failed")

        async def fallback2():
            return "fallback2_result"

        chain = FallbackChain(
            primary=primary,
            fallbacks=[fallback1, fallback2],
            use_cache=False,
        )

        result, mode = await chain.execute()

        assert result == "fallback2_result"
        assert mode == ServiceMode.MINIMAL


@pytest.mark.unit
class TestServiceMode:
    """Tests for ServiceMode enum."""

    def test_service_mode_values(self):
        """Test service mode enum values."""
        assert ServiceMode.FULL.value == "full"
        assert ServiceMode.DEGRADED.value == "degraded"
        assert ServiceMode.MINIMAL.value == "minimal"

    def test_service_mode_comparison(self):
        """Test service mode comparison."""
        assert ServiceMode.FULL != ServiceMode.DEGRADED
        assert ServiceMode.DEGRADED != ServiceMode.MINIMAL


@pytest.mark.unit
class TestDegradedModeMessages:
    """Tests for degraded mode user messages."""

    def test_full_mode_no_message(self):
        """Test full mode returns empty message."""
        message = get_degraded_mode_message(ServiceMode.FULL, "tavily")

        assert message == ""

    def test_degraded_mode_tavily(self):
        """Test degraded mode message for Tavily."""
        message = get_degraded_mode_message(ServiceMode.DEGRADED, "tavily")

        assert len(message) > 0
        assert "unavailable" in message.lower() or "limited" in message.lower()

    def test_degraded_mode_vector(self):
        """Test degraded mode message for vector store."""
        message = get_degraded_mode_message(ServiceMode.DEGRADED, "vector")

        assert len(message) > 0
        assert "unavailable" in message.lower() or "limited" in message.lower()

    def test_degraded_mode_llm(self):
        """Test degraded mode message for LLM."""
        message = get_degraded_mode_message(ServiceMode.DEGRADED, "llm")

        assert len(message) > 0
        assert "delay" in message.lower() or "limited" in message.lower()

    def test_minimal_mode_messages(self):
        """Test minimal mode messages."""
        services = ["tavily", "vector", "llm"]

        for service in services:
            message = get_degraded_mode_message(ServiceMode.MINIMAL, service)
            assert len(message) > 0
            assert "limited" in message.lower() or "cached" in message.lower()

    def test_unknown_service(self):
        """Test message for unknown service."""
        message = get_degraded_mode_message(ServiceMode.DEGRADED, "unknown")

        assert len(message) > 0
        assert "degraded" in message.lower()


@pytest.mark.unit
class TestFallbackIntegration:
    """Integration tests for fallback mechanisms."""

    @pytest.mark.asyncio
    async def test_sync_function_in_chain(self):
        """Test using synchronous function in fallback chain."""

        def primary():
            return "sync_result"

        async def fallback1():
            return "async_fallback"

        chain = FallbackChain(
            primary=primary,
            fallbacks=[fallback1],
            use_cache=False,
        )

        result, mode = await chain.execute()

        assert result == "sync_result"
        assert mode == ServiceMode.FULL

    @pytest.mark.asyncio
    async def test_mixed_sync_async_fallbacks(self):
        """Test mixing sync and async functions in fallback chain."""

        async def primary():
            raise SearchAPIError("Failed")

        def fallback1():
            raise SearchAPIError("Failed")

        async def fallback2():
            return "async_fallback2"

        chain = FallbackChain(
            primary=primary,
            fallbacks=[fallback1, fallback2],
            use_cache=False,
        )

        result, mode = await chain.execute()

        assert result == "async_fallback2"
        assert mode == ServiceMode.MINIMAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
