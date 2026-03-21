"""Fallback mechanisms for graceful degradation when services are unavailable."""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Generic, Optional, TypeVar

from ..config.logging import get_logger
from ..exceptions import LLMError, SearchAPIError, VectorStoreError

logger = get_logger(__name__)

T = TypeVar("T")


class ServiceMode(Enum):
    """Service operation modes."""

    FULL = "full"  # All services available
    DEGRADED = "degraded"  # Some services unavailable
    MINIMAL = "minimal"  # Only core services available


class CachedResponse:
    """Cached response with expiration."""

    def __init__(self, data: Any, ttl_seconds: int = 300) -> None:
        """Initialize cached response.

        Args:
            data: Response data to cache
            ttl_seconds: Time to live in seconds
        """
        self.data = data
        self.cached_at = datetime.now()
        self.expires_at = self.cached_at + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() > self.expires_at

    def get_age_seconds(self) -> float:
        """Get age of cached data in seconds."""
        return (datetime.now() - self.cached_at).total_seconds()


class ResponseCache:
    """Simple in-memory cache for fallback responses."""

    def __init__(self, default_ttl: int = 300) -> None:
        """Initialize response cache.

        Args:
            default_ttl: Default time to live in seconds
        """
        self._cache: dict[str, CachedResponse] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get cached response if available and not expired.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found or expired
        """
        if key not in self._cache:
            return None

        cached = self._cache[key]
        if cached.is_expired():
            del self._cache[key]
            logger.debug("cache_expired", key=key)
            return None

        logger.info(
            "cache_hit",
            key=key,
            age_seconds=cached.get_age_seconds(),
        )
        return cached.data

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Store response in cache.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (uses default if not specified)
        """
        ttl = ttl or self._default_ttl
        self._cache[key] = CachedResponse(data, ttl)
        logger.debug("cache_set", key=key, ttl=ttl)

    def clear(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
        logger.info("cache_cleared")

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, cached in self._cache.items() if cached.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug("cache_cleanup", removed_count=len(expired_keys))

        return len(expired_keys)


# Global cache instance
_response_cache = ResponseCache(default_ttl=900)  # 15 minutes default


def get_response_cache() -> ResponseCache:
    """Get global response cache instance."""
    return _response_cache


class FallbackChain(Generic[T]):
    """Chain of fallback strategies for resilient service calls.

    Attempts primary function, then falls back through a chain of alternatives
    if the primary fails. Supports caching and degraded mode notifications.
    """

    def __init__(
        self,
        primary: Callable[..., T],
        fallbacks: list[Callable[..., T]],
        cache_key_fn: Optional[Callable[..., str]] = None,
        use_cache: bool = True,
    ) -> None:
        """Initialize fallback chain.

        Args:
            primary: Primary function to call
            fallbacks: List of fallback functions in order of preference
            cache_key_fn: Function to generate cache key from args
            use_cache: Whether to use response caching
        """
        self.primary = primary
        self.fallbacks = fallbacks
        self.cache_key_fn = cache_key_fn
        self.use_cache = use_cache
        self._cache = get_response_cache()

    async def execute(self, *args: Any, **kwargs: Any) -> tuple[T, ServiceMode]:
        """Execute with fallback chain.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tuple of (result, service_mode)

        Raises:
            Exception: If all attempts fail
        """
        # Try to get from cache first
        cache_key = None
        if self.use_cache and self.cache_key_fn:
            cache_key = self.cache_key_fn(*args, **kwargs)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.info(
                    "fallback_cache_hit",
                    function=self.primary.__name__,
                )
                return cached, ServiceMode.FULL

        # Try primary function
        try:
            logger.debug(
                "fallback_primary_attempt",
                function=self.primary.__name__,
            )

            if asyncio.iscoroutinefunction(self.primary):
                result = await self.primary(*args, **kwargs)
            else:
                result = self.primary(*args, **kwargs)

            # Cache successful result
            if self.use_cache and cache_key:
                self._cache.set(cache_key, result)

            logger.info(
                "fallback_primary_success",
                function=self.primary.__name__,
            )
            return result, ServiceMode.FULL

        except Exception as primary_error:
            logger.warning(
                "fallback_primary_failed",
                function=self.primary.__name__,
                error=str(primary_error),
                error_type=type(primary_error).__name__,
            )

            # Try fallbacks in order
            for i, fallback in enumerate(self.fallbacks):
                try:
                    logger.info(
                        "fallback_attempt",
                        function=fallback.__name__,
                        fallback_index=i,
                    )

                    if asyncio.iscoroutinefunction(fallback):
                        result = await fallback(*args, **kwargs)
                    else:
                        result = fallback(*args, **kwargs)

                    logger.info(
                        "fallback_success",
                        function=fallback.__name__,
                        fallback_index=i,
                    )

                    # Determine service mode based on which fallback succeeded
                    mode = ServiceMode.DEGRADED if i == 0 else ServiceMode.MINIMAL
                    return result, mode

                except Exception as fallback_error:
                    logger.warning(
                        "fallback_failed",
                        function=fallback.__name__,
                        fallback_index=i,
                        error=str(fallback_error),
                        error_type=type(fallback_error).__name__,
                    )
                    continue

            # All attempts failed
            logger.error(
                "fallback_exhausted",
                primary_function=self.primary.__name__,
                fallback_count=len(self.fallbacks),
                primary_error=str(primary_error),
            )
            raise primary_error


async def tavily_search_with_fallback(
    search_fn: Callable[..., Any],
    vector_search_fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> tuple[Any, ServiceMode]:
    """Execute Tavily search with vector store fallback.

    Args:
        search_fn: Tavily search function
        vector_search_fn: Vector store search function
        *args: Search arguments
        **kwargs: Search keyword arguments

    Returns:
        Tuple of (results, service_mode)
    """

    async def vector_only_fallback(*args: Any, **kwargs: Any) -> Any:
        """Fallback to vector store only."""
        logger.info("tavily_fallback_vector_only")
        return await vector_search_fn(*args, **kwargs)

    async def cached_fallback(*args: Any, **kwargs: Any) -> Any:
        """Fallback to cached response."""
        cache = get_response_cache()
        query = kwargs.get("query") or (args[0] if args else "")
        cache_key = f"tavily_search:{query}"
        cached = cache.get(cache_key)

        if cached:
            logger.info("tavily_fallback_cache")
            return cached

        raise SearchAPIError("No cached response available")

    chain = FallbackChain(
        primary=search_fn,
        fallbacks=[vector_only_fallback, cached_fallback],
        cache_key_fn=lambda *args, **kwargs: f"tavily:{kwargs.get('query', args[0] if args else '')}",
        use_cache=True,
    )

    return await chain.execute(*args, **kwargs)


async def vector_search_with_fallback(
    vector_search_fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> tuple[Any, ServiceMode]:
    """Execute vector search with cache fallback.

    Args:
        vector_search_fn: Vector store search function
        *args: Search arguments
        **kwargs: Search keyword arguments

    Returns:
        Tuple of (results, service_mode)
    """

    async def cached_fallback(*args: Any, **kwargs: Any) -> Any:
        """Fallback to cached response."""
        cache = get_response_cache()
        query = kwargs.get("query") or (args[0] if args else "")
        cache_key = f"vector_search:{query}"
        cached = cache.get(cache_key)

        if cached:
            logger.info("vector_fallback_cache")
            return cached

        raise VectorStoreError("No cached response available")

    chain = FallbackChain(
        primary=vector_search_fn,
        fallbacks=[cached_fallback],
        cache_key_fn=lambda *args, **kwargs: f"vector:{kwargs.get('query', args[0] if args else '')}",
        use_cache=True,
    )

    return await chain.execute(*args, **kwargs)


async def llm_generate_with_fallback(
    generate_fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> tuple[Any, ServiceMode]:
    """Execute LLM generation with cache fallback.

    Args:
        generate_fn: LLM generation function
        *args: Generation arguments
        **kwargs: Generation keyword arguments

    Returns:
        Tuple of (results, service_mode)
    """

    async def cached_fallback(*args: Any, **kwargs: Any) -> Any:
        """Fallback to cached response."""
        cache = get_response_cache()
        prompt = kwargs.get("prompt") or (args[0] if args else "")
        # Use first 100 chars of prompt for cache key
        cache_key = f"llm:{prompt[:100]}"
        cached = cache.get(cache_key)

        if cached:
            logger.info("llm_fallback_cache")
            return cached

        raise LLMError("No cached response available")

    chain = FallbackChain(
        primary=generate_fn,
        fallbacks=[cached_fallback],
        cache_key_fn=lambda *args, **kwargs: f"llm:{str(kwargs.get('prompt', args[0] if args else ''))[:100]}",
        use_cache=True,
    )

    return await chain.execute(*args, **kwargs)


def get_degraded_mode_message(mode: ServiceMode, service: str) -> str:
    """Get user-friendly message for degraded mode.

    Args:
        mode: Current service mode
        service: Name of the service

    Returns:
        User-friendly message
    """
    if mode == ServiceMode.FULL:
        return ""

    messages = {
        ServiceMode.DEGRADED: {
            "tavily": "⚠️ Real-time search is temporarily unavailable. Using historical data only.",
            "vector": "⚠️ Historical data search is temporarily unavailable. Using real-time data only.",
            "llm": "⚠️ AI generation is experiencing delays. Using cached responses when available.",
        },
        ServiceMode.MINIMAL: {
            "tavily": "⚠️ Search services are limited. Showing cached results.",
            "vector": "⚠️ Data services are limited. Showing cached results.",
            "llm": "⚠️ AI services are limited. Showing cached responses.",
        },
    }

    return messages.get(mode, {}).get(
        service, "⚠️ Service is operating in degraded mode."
    )
