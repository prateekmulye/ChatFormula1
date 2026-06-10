"""Tavily web search client built on the langchain-tavily package.

Provides real-time F1 information with rate limiting, TTL caching,
retry with exponential backoff, and graceful degradation when the API
is unavailable.
"""

import asyncio
import time
from collections import deque
from typing import Any, cast

import structlog
from langchain_core.documents import Document
from langchain_tavily import TavilySearch
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from chatf1_agent.caching import CacheManager, get_cache_manager
from chatf1_agent.exceptions import RateLimitError, SearchAPIError
from chatf1_agent.settings import Settings

logger = structlog.get_logger(__name__)


class TavilyClient:
    """Tavily search client with F1-specific defaults.

    Features:
    - Domain filtering for trusted F1 sources
    - Token-bucket rate limiting
    - Retry with exponential backoff
    - Graceful degradation (fallback mode) after consecutive failures
    - TTL caching of search results
    """

    def __init__(
        self,
        settings: Settings,
        rate_limit_requests: int = 60,
        rate_limit_window: float = 60.0,
        enable_cache: bool = True,
    ) -> None:
        """Initialize the Tavily client.

        Args:
            settings: Application settings
            rate_limit_requests: Maximum requests per time window
            rate_limit_window: Time window in seconds for rate limiting
            enable_cache: Whether to enable result caching
        """
        settings.require("tavily_api_key")
        self.settings = settings
        self._search_tool: TavilySearch | None = None

        # Rate limiting using a token bucket over a sliding window
        self._rate_limit_requests = rate_limit_requests
        self._rate_limit_window = rate_limit_window
        self._request_timestamps: deque[float] = deque()
        self._rate_limit_lock = asyncio.Lock()

        # Fallback handling
        self._fallback_mode = False
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        self._last_failure_time: float | None = None
        self._fallback_cooldown = 300.0  # 5 minutes

        # Caching
        self._enable_cache = enable_cache
        self._cache_manager: CacheManager | None = (
            get_cache_manager() if enable_cache else None
        )

        logger.info(
            "tavily_client_initialized",
            max_results=settings.tavily_max_results,
            search_depth=settings.tavily_search_depth,
            include_domains_count=len(settings.tavily_include_domains),
            rate_limit_requests=rate_limit_requests,
            rate_limit_window=rate_limit_window,
            cache_enabled=enable_cache,
        )

    @property
    def is_available(self) -> bool:
        """Check if the Tavily API is available (not in fallback mode)."""
        if self._fallback_mode and self._last_failure_time:
            time_since_failure = time.time() - self._last_failure_time
            if time_since_failure > self._fallback_cooldown:
                logger.info(
                    "exiting_fallback_mode",
                    cooldown_elapsed=time_since_failure,
                )
                self._fallback_mode = False
                self._consecutive_failures = 0

        return not self._fallback_mode

    def _record_failure(self) -> None:
        """Record a search failure and potentially enter fallback mode."""
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        if self._consecutive_failures >= self._max_consecutive_failures:
            if not self._fallback_mode:
                logger.warning(
                    "entering_fallback_mode",
                    consecutive_failures=self._consecutive_failures,
                    cooldown_seconds=self._fallback_cooldown,
                )
                self._fallback_mode = True

    def _record_success(self) -> None:
        """Record a successful search and reset the failure counter."""
        if self._consecutive_failures > 0:
            logger.info(
                "search_recovered",
                previous_failures=self._consecutive_failures,
            )
        self._consecutive_failures = 0
        if self._fallback_mode:
            logger.info("exiting_fallback_mode_after_success")
            self._fallback_mode = False

    def get_fallback_message(self) -> str:
        """Get the user-facing message shown while in fallback mode."""
        if not self._fallback_mode:
            return ""

        time_remaining = 0
        if self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            time_remaining = max(0, int(self._fallback_cooldown - elapsed))

        return (
            "Real-time search is temporarily unavailable. "
            "Responses will be based on historical knowledge only. "
            f"Retrying in approximately {time_remaining // 60} minutes."
        )

    def _build_search_tool(
        self,
        max_results: int | None = None,
        search_depth: str | None = None,
    ) -> TavilySearch:
        """Build a TavilySearch tool with optional overrides."""
        return TavilySearch(
            tavily_api_key=self.settings.tavily_api_key,
            max_results=max_results or self.settings.tavily_max_results,
            search_depth=search_depth or self.settings.tavily_search_depth,
            include_domains=list(self.settings.tavily_include_domains),
            exclude_domains=list(self.settings.tavily_exclude_domains),
        )

    @property
    def search_tool(self) -> TavilySearch:
        """Get or lazily create the default Tavily search tool."""
        if self._search_tool is None:
            self._search_tool = self._build_search_tool()
        return self._search_tool

    async def _check_rate_limit(self) -> None:
        """Enforce the sliding-window rate limit.

        Raises:
            RateLimitError: If the rate limit is exceeded
        """
        async with self._rate_limit_lock:
            current_time = time.time()

            while (
                self._request_timestamps
                and current_time - self._request_timestamps[0] > self._rate_limit_window
            ):
                self._request_timestamps.popleft()

            if len(self._request_timestamps) >= self._rate_limit_requests:
                oldest_timestamp = self._request_timestamps[0]
                wait_time = self._rate_limit_window - (current_time - oldest_timestamp)

                logger.warning(
                    "rate_limit_exceeded",
                    requests_in_window=len(self._request_timestamps),
                    wait_time=wait_time,
                )

                raise RateLimitError(
                    "Tavily API rate limit exceeded",
                    retry_after=int(wait_time) + 1,
                    details={
                        "requests_in_window": len(self._request_timestamps),
                        "rate_limit": self._rate_limit_requests,
                        "window_seconds": self._rate_limit_window,
                    },
                )

            self._request_timestamps.append(current_time)

    @staticmethod
    def _extract_results(raw: Any) -> list[dict[str, Any]]:
        """Normalize a TavilySearch response into a list of result dicts.

        langchain-tavily returns ``{"query": ..., "results": [...], ...}``;
        this extracts the results list defensively.
        """
        if isinstance(raw, dict):
            results = raw.get("results", [])
            return results if isinstance(results, list) else []
        if isinstance(raw, list):
            return raw
        return []

    @retry(
        retry=retry_if_exception_type((SearchAPIError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        max_results: int | None = None,
        search_depth: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Search for F1 information with rate limiting and caching.

        Args:
            query: Search query
            max_results: Override default max results
            search_depth: Override default search depth ("basic" or "advanced")
            use_cache: Whether to use cached results if available

        Returns:
            List of search results with content, URL, and metadata

        Raises:
            SearchAPIError: If the search fails
            RateLimitError: If the rate limit is exceeded
        """
        final_max_results = max_results or self.settings.tavily_max_results
        final_search_depth = search_depth or self.settings.tavily_search_depth

        cache_key = None
        if use_cache and self._cache_manager:
            cache_key = self._cache_manager.get_search_cache_key(
                query=query,
                max_results=final_max_results,
                search_depth=final_search_depth,
            )
            cached_results = self._cache_manager.search_cache.get(cache_key)
            if cached_results is not None:
                logger.info("tavily_search_cache_hit", query=query)
                return cast(list[dict[str, Any]], cached_results)

        try:
            await self._check_rate_limit()

            logger.info("tavily_search_started", query=query)

            if max_results is not None or search_depth is not None:
                search_tool = self._build_search_tool(
                    max_results=final_max_results,
                    search_depth=final_search_depth,
                )
            else:
                search_tool = self.search_tool

            raw = await search_tool.ainvoke({"query": query})
            results = self._extract_results(raw)

            logger.info(
                "tavily_search_completed",
                query=query,
                results_count=len(results),
            )

            if cache_key and self._cache_manager:
                self._cache_manager.search_cache.set(cache_key, results)
                logger.debug("tavily_search_results_cached", query=query)

            self._record_success()
            return results

        except RateLimitError:
            self._record_failure()
            raise
        except Exception as e:
            self._record_failure()
            logger.error(
                "tavily_search_failed",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SearchAPIError(
                f"Tavily search failed for query: {query}",
                details={"query": query, "error": str(e)},
                original_error=e,
            ) from e

    async def safe_search(
        self,
        query: str,
        max_results: int | None = None,
        search_depth: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Search with graceful degradation — never raises.

        Args:
            query: Search query
            max_results: Override default max results
            search_depth: Override default search depth

        Returns:
            Tuple of (results, error_message):
            - results: List of search results (empty if failed)
            - error_message: User-facing error message (None if successful)
        """
        if not self.is_available:
            error_msg = self.get_fallback_message()
            logger.info("search_skipped_fallback_mode", query=query)
            return [], error_msg

        try:
            results = await self.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
            )
            return results, None

        except RateLimitError:
            logger.warning("safe_search_rate_limited", query=query)
            return [], (
                "Search rate limit reached. Please wait a moment before "
                "trying again. Using historical knowledge for now."
            )

        except SearchAPIError as e:
            logger.warning("safe_search_failed", query=query, error=str(e))
            return [], (
                "Real-time search is temporarily unavailable. "
                "Responses will be based on historical knowledge only."
            )

        except Exception as e:
            logger.error(
                "safe_search_unexpected_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            return [], (
                "An unexpected error occurred with real-time search. "
                "Using historical knowledge only."
            )

    async def get_latest_f1_news(
        self,
        topic: str | None = None,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Get the latest F1 news articles.

        Args:
            topic: Specific F1 topic (e.g. "race results", "driver transfers")
            max_results: Number of articles to retrieve

        Returns:
            List of news articles with content and metadata
        """
        query = f"Formula 1 {topic} latest news" if topic else "Formula 1 latest news"

        logger.info("fetching_latest_f1_news", topic=topic, max_results=max_results)

        return await self.search(query=query, max_results=max_results)

    def _parse_and_normalize_result(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Parse and normalize a single Tavily search result.

        Args:
            result: Raw search result from the Tavily API

        Returns:
            Normalized result dictionary or None if invalid
        """
        try:
            content = result.get("raw_content") or result.get("content", "")

            if not content or not content.strip():
                logger.debug(
                    "skipping_empty_result",
                    url=result.get("url", "unknown"),
                )
                return None

            url = result.get("url", "")
            if not url:
                logger.warning("result_missing_url", title=result.get("title", ""))
                return None

            normalized = {
                "content": content.strip(),
                "url": url,
                "title": result.get("title", "").strip(),
                "score": float(result.get("score", 0.0)),
                "published_date": result.get("published_date", ""),
                "raw_content": result.get("raw_content", ""),
            }

            if not 0.0 <= normalized["score"] <= 1.0:
                logger.warning(
                    "invalid_score",
                    url=url,
                    score=normalized["score"],
                )
                normalized["score"] = max(0.0, min(1.0, normalized["score"]))

            return normalized

        except Exception as e:
            logger.error(
                "result_parsing_failed",
                error=str(e),
                result_keys=list(result.keys()),
            )
            return None

    def _deduplicate_results(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove duplicate results based on URL and content prefix.

        Args:
            results: List of normalized search results

        Returns:
            Deduplicated list of results
        """
        seen_urls: set[str] = set()
        seen_content_hashes: set[int] = set()
        deduplicated = []

        for result in results:
            url = result["url"]
            content = result["content"]

            if url in seen_urls:
                logger.debug("duplicate_url_skipped", url=url)
                continue

            content_hash = hash(content[:500])
            if content_hash in seen_content_hashes:
                logger.debug("duplicate_content_skipped", url=url)
                continue

            seen_urls.add(url)
            seen_content_hashes.add(content_hash)
            deduplicated.append(result)

        if len(deduplicated) < len(results):
            logger.info(
                "results_deduplicated",
                original_count=len(results),
                deduplicated_count=len(deduplicated),
                removed=len(results) - len(deduplicated),
            )

        return deduplicated

    def convert_to_documents(
        self,
        search_results: list[dict[str, Any]],
        deduplicate: bool = True,
    ) -> list[Document]:
        """Convert Tavily search results to LangChain Documents.

        Args:
            search_results: List of search results from Tavily
            deduplicate: Whether to remove duplicate results

        Returns:
            List of Document objects ready for vector store ingestion
        """
        documents = []
        normalized_results = []

        for result in search_results:
            normalized = self._parse_and_normalize_result(result)
            if normalized:
                normalized_results.append(normalized)

        if deduplicate:
            normalized_results = self._deduplicate_results(normalized_results)

        for result in normalized_results:
            doc = Document(
                page_content=result["content"],
                metadata={
                    "source": result["url"],
                    "title": result["title"],
                    "score": result["score"],
                    "published_date": result["published_date"],
                    "source_type": "tavily_search",
                    "has_raw_content": bool(result["raw_content"]),
                },
            )
            documents.append(doc)

        logger.info(
            "search_results_converted_to_documents",
            results_count=len(search_results),
            normalized_count=len(normalized_results),
            documents_count=len(documents),
        )

        return documents
