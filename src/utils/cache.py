"""Caching utilities for ChatFormula1 agent.

This module provides in-memory caching for:
- Vector search results
- Tavily search results
- LLM responses for common queries

Uses a simple TTL-based cache with LRU eviction.
"""

import hashlib
import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class TTLCache:
    """Time-To-Live cache with LRU eviction.

    This cache stores items with an expiration time and automatically
    removes expired entries. When the cache is full, it evicts the
    least recently used items.

    Attributes:
        max_size: Maximum number of items to store
        default_ttl: Default time-to-live in seconds
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300) -> None:
        """Initialize TTL cache.

        Args:
            max_size: Maximum number of items to store (default: 1000)
            default_ttl: Default TTL in seconds (default: 300 = 5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

        logger.info(
            "ttl_cache_initialized",
            max_size=max_size,
            default_ttl=default_ttl,
        )

    def _generate_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Hash string to use as cache key
        """
        cache_data = {
            "args": args,
            "kwargs": kwargs,
        }
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _is_expired(self, expiry_time: float) -> bool:
        """Check if an entry has expired.

        Args:
            expiry_time: Expiry timestamp

        Returns:
            True if expired, False otherwise
        """
        return time.time() > expiry_time

    def _evict_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries evicted
        """
        expired_keys = [
            key for key, (_, expiry) in self._cache.items() if self._is_expired(expiry)
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug("expired_entries_evicted", count=len(expired_keys))

        return len(expired_keys)

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            key, _ = self._cache.popitem(last=False)
            logger.debug("lru_entry_evicted", key=key[:16])

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        # Clean up expired entries periodically
        if len(self._cache) > self.max_size * 0.9:
            self._evict_expired()

        if key in self._cache:
            value, expiry = self._cache[key]

            if self._is_expired(expiry):
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                logger.debug("cache_miss_expired", key=key[:16])
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug("cache_hit", key=key[:16])
            return value

        self._misses += 1
        logger.debug("cache_miss", key=key[:16])
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        # Evict LRU if cache is full
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        # Calculate expiry time
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl_seconds

        # Store value
        self._cache[key] = (value, expiry)

        logger.debug(
            "cache_set",
            key=key[:16],
            ttl=ttl_seconds,
            cache_size=len(self._cache),
        )

    def delete(self, key: str) -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug("cache_entry_deleted", key=key[:16])
            return True
        return False

    def clear(self) -> int:
        """Clear all entries from cache.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("cache_cleared", entries_cleared=count)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def __len__(self) -> int:
        """Get number of entries in cache."""
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache (doesn't check expiry)."""
        return key in self._cache


class CacheManager:
    """Manager for multiple caches with different TTLs.

    Provides separate caches for:
    - Vector search results (5 minute TTL)
    - Tavily search results (15 minute TTL)
    - LLM responses (1 hour TTL)
    """

    def __init__(
        self,
        vector_cache_ttl: int = 300,  # 5 minutes
        search_cache_ttl: int = 900,  # 15 minutes
        llm_cache_ttl: int = 3600,  # 1 hour
        max_size: int = 1000,
    ) -> None:
        """Initialize cache manager.

        Args:
            vector_cache_ttl: TTL for vector search results in seconds
            search_cache_ttl: TTL for Tavily search results in seconds
            llm_cache_ttl: TTL for LLM responses in seconds
            max_size: Maximum size for each cache
        """
        self.vector_cache = TTLCache(max_size=max_size, default_ttl=vector_cache_ttl)
        self.search_cache = TTLCache(max_size=max_size, default_ttl=search_cache_ttl)
        self.llm_cache = TTLCache(max_size=max_size, default_ttl=llm_cache_ttl)

        logger.info(
            "cache_manager_initialized",
            vector_ttl=vector_cache_ttl,
            search_ttl=search_cache_ttl,
            llm_ttl=llm_cache_ttl,
            max_size=max_size,
        )

    def get_vector_cache_key(
        self,
        query: str,
        k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate cache key for vector search.

        Args:
            query: Search query
            k: Number of results
            filters: Optional metadata filters

        Returns:
            Cache key string
        """
        return self.vector_cache._generate_key(
            "vector",
            query,
            k,
            filters or {},
        )

    def get_search_cache_key(
        self,
        query: str,
        max_results: int,
        search_depth: str,
    ) -> str:
        """Generate cache key for Tavily search.

        Args:
            query: Search query
            max_results: Maximum results
            search_depth: Search depth

        Returns:
            Cache key string
        """
        return self.search_cache._generate_key(
            "search",
            query,
            max_results,
            search_depth,
        )

    def get_llm_cache_key(
        self,
        query: str,
        context: str,
        model: str,
        temperature: float,
    ) -> str:
        """Generate cache key for LLM response.

        Args:
            query: User query
            context: Context provided to LLM
            model: Model name
            temperature: Temperature setting

        Returns:
            Cache key string
        """
        # Use hash of context to keep key size manageable
        context_hash = hashlib.md5(context.encode()).hexdigest()

        return self.llm_cache._generate_key(
            "llm",
            query,
            context_hash,
            model,
            temperature,
        )

    def clear_all(self) -> Dict[str, int]:
        """Clear all caches.

        Returns:
            Dictionary with counts of cleared entries per cache
        """
        return {
            "vector_cache": self.vector_cache.clear(),
            "search_cache": self.search_cache.clear(),
            "llm_cache": self.llm_cache.clear(),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches.

        Returns:
            Dictionary with stats for each cache
        """
        return {
            "vector_cache": self.vector_cache.get_stats(),
            "search_cache": self.search_cache.get_stats(),
            "llm_cache": self.llm_cache.get_stats(),
        }


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance.

    Returns:
        Global CacheManager instance
    """
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager()
        logger.info("global_cache_manager_created")

    return _cache_manager


def clear_all_caches() -> Dict[str, int]:
    """Clear all caches in the global cache manager.

    Returns:
        Dictionary with counts of cleared entries per cache
    """
    manager = get_cache_manager()
    return manager.clear_all()


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all caches.

    Returns:
        Dictionary with stats for each cache
    """
    manager = get_cache_manager()
    return manager.get_all_stats()
