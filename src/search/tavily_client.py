"""Tavily Search API client using langchain-tavily for F1 news and information.

This module provides integration with Tavily's search, map, and crawl capabilities
to retrieve the latest and most accurate F1 news and updates.
"""

import asyncio
import time
from collections import deque
from typing import Any, Optional

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.documents import Document

from ..config.logging import get_logger
from ..config.settings import Settings
from ..exceptions import RateLimitError, SearchAPIError
from ..utils.retry import retry_with_backoff

logger = get_logger(__name__)


class TavilyClient:
    """Client for Tavily Search API with F1-specific optimizations.

    Supports:
    - Standard search for real-time F1 information
    - Deep crawl for comprehensive content extraction
    - Domain filtering for trusted F1 sources
    - Rate limiting with token bucket algorithm
    - Automatic retry with exponential backoff
    - Graceful degradation with fallback handling

    Attributes:
        settings: Application settings
        rate_limit_requests: Maximum requests per minute (default: 60)
        rate_limit_window: Time window in seconds (default: 60)
        fallback_mode: Whether the client is in fallback mode
    """

    def __init__(
        self,
        settings: Settings,
        rate_limit_requests: int = 60,
        rate_limit_window: float = 60.0,
        enable_cache: bool = True,
    ) -> None:
        """Initialize Tavily client with rate limiting and caching.

        Args:
            settings: Application settings
            rate_limit_requests: Maximum requests per time window
            rate_limit_window: Time window in seconds for rate limiting
            enable_cache: Whether to enable result caching
        """
        self.settings = settings
        self._search_tool: Optional[TavilySearchResults] = None

        # Rate limiting using token bucket algorithm
        self._rate_limit_requests = rate_limit_requests
        self._rate_limit_window = rate_limit_window
        self._request_timestamps: deque[float] = deque()
        self._rate_limit_lock = asyncio.Lock()

        # Fallback handling
        self._fallback_mode = False
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        self._last_failure_time: Optional[float] = None
        self._fallback_cooldown = 300.0  # 5 minutes

        # Caching
        self._enable_cache = enable_cache
        if enable_cache:
            from ..utils.cache import get_cache_manager

            self._cache_manager = get_cache_manager()
        else:
            self._cache_manager = None

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
        """Check if Tavily API is available (not in fallback mode).

        Returns:
            True if API is available, False if in fallback mode
        """
        # Check if we should exit fallback mode
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
        """Record a successful search and reset failure counter."""
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
        """Get user-facing message when in fallback mode.

        Returns:
            Human-readable error message explaining the situation
        """
        if not self._fallback_mode:
            return ""

        time_remaining = 0
        if self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            time_remaining = max(0, int(self._fallback_cooldown - elapsed))

        return (
            "⚠️ Real-time search is temporarily unavailable. "
            "Responses will be based on historical knowledge only. "
            f"Retrying in approximately {time_remaining // 60} minutes."
        )

    @property
    def search_tool(self) -> TavilySearchResults:
        """Get or create the Tavily search tool.

        Returns:
            TavilySearchResults: Configured search tool
        """
        if self._search_tool is None:
            self._search_tool = TavilySearchResults(
                api_key=self.settings.tavily_api_key,
                max_results=self.settings.tavily_max_results,
                search_depth=self.settings.tavily_search_depth,
                include_answer=self.settings.tavily_include_answer,
                include_raw_content=self.settings.tavily_include_raw_content,
                include_images=self.settings.tavily_include_images,
                include_domains=self.settings.tavily_include_domains,
                exclude_domains=self.settings.tavily_exclude_domains,
            )
        return self._search_tool

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting using token bucket algorithm.

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        async with self._rate_limit_lock:
            current_time = time.time()

            # Remove timestamps outside the current window
            while (
                self._request_timestamps
                and current_time - self._request_timestamps[0] > self._rate_limit_window
            ):
                self._request_timestamps.popleft()

            # Check if we've exceeded the rate limit
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

            # Add current request timestamp
            self._request_timestamps.append(current_time)

    @retry_with_backoff(
        max_attempts=3,
        exceptions=(SearchAPIError, ConnectionError),
    )
    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        include_answer: Optional[bool] = None,
        include_raw_content: Optional[bool] = None,
        search_depth: Optional[str] = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Search for F1 information using Tavily with rate limiting and caching.

        Args:
            query: Search query
            max_results: Override default max results
            include_answer: Override default include_answer setting
            include_raw_content: Override default include_raw_content setting
            search_depth: Override default search depth ("basic" or "advanced")
            use_cache: Whether to use cached results if available

        Returns:
            List of search results with content, URL, and metadata

        Raises:
            SearchAPIError: If search fails
            RateLimitError: If rate limit is exceeded

        Example:
            results = await client.search("Max Verstappen 2024 championship")
        """
        # Resolve parameters
        final_max_results = max_results or self.settings.tavily_max_results
        final_search_depth = search_depth or self.settings.tavily_search_depth

        # Check cache first
        if use_cache and self._enable_cache and self._cache_manager:
            cache_key = self._cache_manager.get_search_cache_key(
                query=query,
                max_results=final_max_results,
                search_depth=final_search_depth,
            )
            cached_results = self._cache_manager.search_cache.get(cache_key)
            if cached_results is not None:
                logger.info("tavily_search_cache_hit", query=query)
                return cached_results

        try:
            # Check rate limit before making request
            await self._check_rate_limit()

            logger.info("tavily_search_started", query=query)

            # Create a custom search tool if overrides are provided
            if any(
                param is not None
                for param in [
                    max_results,
                    include_answer,
                    include_raw_content,
                    search_depth,
                ]
            ):
                search_tool = TavilySearchResults(
                    api_key=self.settings.tavily_api_key,
                    max_results=final_max_results,
                    search_depth=final_search_depth,
                    include_answer=(
                        include_answer
                        if include_answer is not None
                        else self.settings.tavily_include_answer
                    ),
                    include_raw_content=(
                        include_raw_content
                        if include_raw_content is not None
                        else self.settings.tavily_include_raw_content
                    ),
                    include_images=self.settings.tavily_include_images,
                    include_domains=self.settings.tavily_include_domains,
                    exclude_domains=self.settings.tavily_exclude_domains,
                )
            else:
                search_tool = self.search_tool

            # Execute search
            results = await search_tool.ainvoke({"query": query})

            logger.info(
                "tavily_search_completed",
                query=query,
                results_count=len(results) if isinstance(results, list) else 1,
            )

            # Ensure results is a list
            if not isinstance(results, list):
                results = [results]

            # Cache results
            if use_cache and self._enable_cache and self._cache_manager:
                cache_key = self._cache_manager.get_search_cache_key(
                    query=query,
                    max_results=final_max_results,
                    search_depth=final_search_depth,
                )
                self._cache_manager.search_cache.set(cache_key, results)
                logger.debug("tavily_search_results_cached", query=query)

            # Record success
            self._record_success()

            return results

        except RateLimitError:
            # Re-raise rate limit errors without wrapping
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
            )

    async def safe_search(
        self,
        query: str,
        max_results: Optional[int] = None,
        include_answer: Optional[bool] = None,
        include_raw_content: Optional[bool] = None,
        search_depth: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        """Search with graceful degradation - returns empty results on failure.

        This method never raises exceptions, making it safe for use in agent
        workflows where fallback to vector store is acceptable.

        Args:
            query: Search query
            max_results: Override default max results
            include_answer: Override default include_answer setting
            include_raw_content: Override default include_raw_content setting
            search_depth: Override default search depth ("basic" or "advanced")

        Returns:
            Tuple of (results, error_message):
            - results: List of search results (empty if failed)
            - error_message: User-facing error message (None if successful)

        Example:
            results, error = await client.safe_search("F1 news")
            if error:
                print(f"Search unavailable: {error}")
                # Fall back to vector store only
        """
        # Check if in fallback mode
        if not self.is_available:
            error_msg = self.get_fallback_message()
            logger.info("search_skipped_fallback_mode", query=query)
            return [], error_msg

        try:
            results = await self.search(
                query=query,
                max_results=max_results,
                include_answer=include_answer,
                include_raw_content=include_raw_content,
                search_depth=search_depth,
            )
            return results, None

        except RateLimitError as e:
            error_msg = (
                "⚠️ Search rate limit reached. "
                "Please wait a moment before trying again. "
                "Using historical knowledge for now."
            )
            logger.warning("safe_search_rate_limited", query=query)
            return [], error_msg

        except SearchAPIError as e:
            error_msg = (
                "⚠️ Real-time search is temporarily unavailable. "
                "Responses will be based on historical knowledge only."
            )
            logger.warning(
                "safe_search_failed",
                query=query,
                error=str(e),
            )
            return [], error_msg

        except Exception as e:
            error_msg = (
                "⚠️ An unexpected error occurred with real-time search. "
                "Using historical knowledge only."
            )
            logger.error(
                "safe_search_unexpected_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            return [], error_msg

    async def search_with_context(
        self,
        query: str,
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search with additional context for more relevant results.

        This method enhances the query with contextual information to improve
        search relevance. Rate limiting and retry logic are handled by the
        underlying search method.

        Args:
            query: Search query
            context: Additional context to refine search (e.g., "2024 season")

        Returns:
            Dictionary with search results and AI-generated answer

        Raises:
            SearchAPIError: If search fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            # Enhance query with context
            enhanced_query = f"{query} {context}" if context else query

            logger.info(
                "tavily_contextual_search_started",
                original_query=query,
                context=context,
                enhanced_query=enhanced_query,
            )

            results = await self.search(
                enhanced_query,
                include_answer=True,
                include_raw_content=True,
            )

            return {
                "query": query,
                "context": context,
                "results": results,
            }

        except (SearchAPIError, RateLimitError):
            # Re-raise known errors without wrapping
            raise
        except Exception as e:
            logger.error(
                "tavily_contextual_search_failed",
                query=query,
                context=context,
                error=str(e),
            )
            raise SearchAPIError(
                f"Contextual search failed for query: {query}",
                details={"query": query, "context": context, "error": str(e)},
                original_error=e,
            )

    async def get_latest_f1_news(
        self,
        topic: Optional[str] = None,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Get the latest F1 news articles.

        Args:
            topic: Specific F1 topic (e.g., "race results", "driver transfers")
            max_results: Number of articles to retrieve

        Returns:
            List of news articles with content and metadata

        Example:
            news = await client.get_latest_f1_news("Monaco Grand Prix")
        """
        query = f"Formula 1 {topic} latest news" if topic else "Formula 1 latest news"

        logger.info("fetching_latest_f1_news", topic=topic, max_results=max_results)

        return await self.search(
            query=query,
            max_results=max_results,
            include_raw_content=True,
        )

    async def crawl_f1_source(
        self,
        url: str,
        max_depth: Optional[int] = None,
    ) -> list[Document]:
        """Crawl an F1 website for comprehensive content extraction.

        This is useful for ingesting entire articles or pages into the vector DB.

        Args:
            url: URL to crawl
            max_depth: Maximum crawl depth (default from settings)

        Returns:
            List of Document objects with extracted content

        Raises:
            SearchAPIError: If crawl fails

        Example:
            docs = await client.crawl_f1_source("https://formula1.com/article")
        """
        try:
            depth = max_depth or self.settings.tavily_max_crawl_depth

            logger.info("tavily_crawl_started", url=url, max_depth=depth)

            # Use Tavily's extract endpoint for deep content extraction
            # Note: This requires the raw content to be enabled
            results = await self.search(
                query=url,
                max_results=1,
                include_raw_content=True,
            )

            documents = []
            for result in results:
                if "content" in result or "raw_content" in result:
                    content = result.get("raw_content") or result.get("content", "")
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": result.get("url", url),
                            "title": result.get("title", ""),
                            "score": result.get("score", 0.0),
                            "crawl_depth": depth,
                        },
                    )
                    documents.append(doc)

            logger.info(
                "tavily_crawl_completed",
                url=url,
                documents_extracted=len(documents),
            )

            return documents

        except Exception as e:
            logger.error(
                "tavily_crawl_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SearchAPIError(
                f"Failed to crawl URL: {url}",
                details={"url": url, "error": str(e)},
                original_error=e,
            )

    async def map_f1_domain(
        self,
        domain: str,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Map an F1 domain to discover relevant pages.

        Useful for discovering new content on trusted F1 sources.

        Args:
            domain: Domain to map (e.g., "formula1.com")
            query: Optional query to filter results

        Returns:
            List of discovered pages with metadata

        Example:
            pages = await client.map_f1_domain("autosport.com", "2024 season")
        """
        try:
            search_query = f"site:{domain}"
            if query:
                search_query = f"{query} {search_query}"

            logger.info("tavily_domain_mapping_started", domain=domain, query=query)

            results = await self.search(
                query=search_query,
                max_results=self.settings.tavily_max_results,
                include_raw_content=False,
            )

            logger.info(
                "tavily_domain_mapping_completed",
                domain=domain,
                pages_found=len(results),
            )

            return results

        except Exception as e:
            logger.error(
                "tavily_domain_mapping_failed",
                domain=domain,
                query=query,
                error=str(e),
            )
            raise SearchAPIError(
                f"Failed to map domain: {domain}",
                details={"domain": domain, "query": query, "error": str(e)},
                original_error=e,
            )

    def _parse_and_normalize_result(
        self,
        result: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Parse and normalize a single Tavily search result.

        Args:
            result: Raw search result from Tavily API

        Returns:
            Normalized result dictionary or None if invalid
        """
        try:
            # Extract content (prefer raw_content for completeness)
            content = result.get("raw_content") or result.get("content", "")

            if not content or not content.strip():
                logger.debug(
                    "skipping_empty_result",
                    url=result.get("url", "unknown"),
                )
                return None

            # Extract and validate URL
            url = result.get("url", "")
            if not url:
                logger.warning("result_missing_url", title=result.get("title", ""))
                return None

            # Extract metadata with defaults
            normalized = {
                "content": content.strip(),
                "url": url,
                "title": result.get("title", "").strip(),
                "score": float(result.get("score", 0.0)),
                "published_date": result.get("published_date", ""),
                "raw_content": result.get("raw_content", ""),
            }

            # Validate score is in reasonable range
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
        """Remove duplicate results based on URL and content similarity.

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

            # Check for duplicate URL
            if url in seen_urls:
                logger.debug("duplicate_url_skipped", url=url)
                continue

            # Check for duplicate content (using hash for efficiency)
            content_hash = hash(content[:500])  # Hash first 500 chars
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

        This method:
        1. Parses and normalizes each result
        2. Validates metadata (dates, sources, relevance)
        3. Optionally deduplicates results
        4. Creates LangChain Document objects

        Args:
            search_results: List of search results from Tavily
            deduplicate: Whether to remove duplicate results (default: True)

        Returns:
            List of Document objects ready for vector DB ingestion

        Example:
            results = await client.search("F1 news")
            documents = client.convert_to_documents(results)
        """
        documents = []
        normalized_results = []

        # Parse and normalize each result
        for result in search_results:
            normalized = self._parse_and_normalize_result(result)
            if normalized:
                normalized_results.append(normalized)

        # Deduplicate if requested
        if deduplicate:
            normalized_results = self._deduplicate_results(normalized_results)

        # Convert to Document objects
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
