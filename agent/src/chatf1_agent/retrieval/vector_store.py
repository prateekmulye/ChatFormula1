"""Pinecone vector store manager with namespaces and deterministic IDs.

Vector IDs are SHA-256 content hashes, so re-ingesting the same document
upserts instead of duplicating — the index can be rebuilt from `data/` at
any time. Documents live in two namespaces: ``static_corpus`` (historical
data ingested offline) and ``news`` (Tavily-sourced articles).
"""

import asyncio
import hashlib
from typing import Any, cast

import structlog
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from chatf1_agent.caching import get_cache_manager
from chatf1_agent.exceptions import VectorStoreError
from chatf1_agent.settings import Settings

logger = structlog.get_logger(__name__)

# Pinecone namespaces
NAMESPACE_STATIC = "static_corpus"
NAMESPACE_NEWS = "news"

# Optimized batch sizes for different operations
OPTIMAL_EMBEDDING_BATCH_SIZE = 100  # OpenAI embeddings API optimal batch size
OPTIMAL_UPSERT_BATCH_SIZE = 100  # Pinecone upsert optimal batch size
MAX_PARALLEL_BATCHES = 3  # Maximum parallel batch operations


def content_hash_id(content: str) -> str:
    """Compute the deterministic SHA-256 vector ID for document content.

    Shared with the ingestion pipeline so re-ingestion upserts in place
    instead of creating duplicate vectors.

    Args:
        content: Document page content.

    Returns:
        Hex-encoded SHA-256 digest of the content.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class VectorStoreManager:
    """Manages Pinecone vector store operations with LangChain integration.

    Provides index lifecycle management, health checks, batched upserts with
    deterministic IDs, and cached semantic search.
    """

    def __init__(self, config: Settings) -> None:
        """Initialize VectorStoreManager with configuration.

        Args:
            config: Application settings containing Pinecone and OpenAI configuration

        Raises:
            VectorStoreError: If initialization fails
        """
        config.require("pinecone_api_key", "openai_api_key")
        self.config = config
        self.logger = logger.bind(component="vector_store_manager")

        try:
            self.pc = Pinecone(
                api_key=config.pinecone_api_key,
                pool_threads=10,  # Connection pool size for parallel operations
            )
            self.logger.info("pinecone_client_initialized", pool_threads=10)
        except Exception as e:
            self.logger.error("pinecone_client_init_failed", error=str(e))
            raise VectorStoreError(f"Failed to initialize Pinecone client: {e}") from e

        try:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=config.openai_api_key,
                model=config.openai_embedding_model,
                chunk_size=OPTIMAL_EMBEDDING_BATCH_SIZE,
                max_retries=3,
            )
            self.logger.info(
                "embeddings_initialized",
                model=config.openai_embedding_model,
                chunk_size=OPTIMAL_EMBEDDING_BATCH_SIZE,
            )
        except Exception as e:
            self.logger.error("embeddings_init_failed", error=str(e))
            raise VectorStoreError(f"Failed to initialize embeddings: {e}") from e

        self.index_name = config.pinecone_index_name
        self._vector_store: PineconeVectorStore | None = None
        self._cache_manager = get_cache_manager()

        # Performance metrics
        self._query_count = 0
        self._cache_hits = 0
        self._total_query_time = 0.0

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def initialize(self) -> None:
        """Initialize the vector store with retry logic.

        Creates the index if it doesn't exist and initializes PineconeVectorStore.

        Raises:
            VectorStoreError: If initialization fails after retries
        """
        try:
            await self._ensure_index_exists()
            await self._initialize_vector_store()
            self.logger.info("vector_store_initialized", index_name=self.index_name)
        except Exception as e:
            self.logger.error(
                "vector_store_init_failed",
                index_name=self.index_name,
                error=str(e),
            )
            raise VectorStoreError(f"Failed to initialize vector store: {e}") from e

    async def _ensure_index_exists(self) -> None:
        """Ensure the Pinecone index exists, creating it if necessary.

        Raises:
            VectorStoreError: If index creation or validation fails
        """
        try:
            existing_indexes = await asyncio.to_thread(
                lambda: [idx.name for idx in self.pc.list_indexes()]
            )

            if self.index_name not in existing_indexes:
                self.logger.info(
                    "creating_index",
                    index_name=self.index_name,
                    dimension=self.config.pinecone_dimension,
                )

                await asyncio.to_thread(
                    self.pc.create_index,
                    name=self.index_name,
                    dimension=self.config.pinecone_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )

                self.logger.info("index_created", index_name=self.index_name)
            else:
                self.logger.info("index_exists", index_name=self.index_name)

            await self._validate_index()

        except Exception as e:
            self.logger.error(
                "index_creation_failed",
                index_name=self.index_name,
                error=str(e),
            )
            raise VectorStoreError(f"Failed to ensure index exists: {e}") from e

    async def _validate_index(self) -> None:
        """Validate index configuration matches expected settings.

        Raises:
            VectorStoreError: If index configuration is invalid
        """
        try:
            index_description = await asyncio.to_thread(
                self.pc.describe_index,
                self.index_name,
            )

            expected_dimension = self.config.pinecone_dimension
            actual_dimension = index_description.dimension

            if actual_dimension != expected_dimension:
                raise VectorStoreError(
                    f"Index dimension mismatch: expected {expected_dimension}, "
                    f"got {actual_dimension}"
                )

            self.logger.info(
                "index_validated",
                index_name=self.index_name,
                dimension=actual_dimension,
                metric=index_description.metric,
            )

        except VectorStoreError:
            raise
        except Exception as e:
            self.logger.error("index_validation_failed", error=str(e))
            raise VectorStoreError(f"Failed to validate index: {e}") from e

    async def _initialize_vector_store(self) -> None:
        """Initialize the PineconeVectorStore instance.

        Raises:
            VectorStoreError: If vector store initialization fails
        """
        try:
            self._vector_store = await asyncio.to_thread(
                PineconeVectorStore,
                index_name=self.index_name,
                embedding=self.embeddings,
                pinecone_api_key=self.config.pinecone_api_key,
            )

            self.logger.info(
                "pinecone_vector_store_initialized",
                index_name=self.index_name,
            )

        except Exception as e:
            self.logger.error("vector_store_creation_failed", error=str(e))
            raise VectorStoreError(f"Failed to create vector store: {e}") from e

    @property
    def vector_store(self) -> PineconeVectorStore:
        """Get the initialized vector store instance.

        Returns:
            PineconeVectorStore: Initialized vector store

        Raises:
            VectorStoreError: If the vector store is not initialized
        """
        if self._vector_store is None:
            raise VectorStoreError(
                "Vector store not initialized. Call initialize() first."
            )
        return self._vector_store

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the vector store.

        Returns:
            Dict with status, index name, dimension, metric, and vector count
            (or an error message when unhealthy).
        """
        try:
            if self._vector_store is None:
                return {
                    "status": "unhealthy",
                    "error": "Vector store not initialized",
                }

            index = self.pc.Index(self.index_name)
            stats = await asyncio.to_thread(index.describe_index_stats)
            description = await asyncio.to_thread(
                self.pc.describe_index,
                self.index_name,
            )

            health_info = {
                "status": "healthy",
                "index_name": self.index_name,
                "dimension": description.dimension,
                "metric": description.metric,
                "total_vector_count": stats.total_vector_count,
            }

            self.logger.info("health_check_passed", **health_info)
            return health_info

        except Exception as e:
            self.logger.error("health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": f"Health check failed: {e}",
            }

    async def add_documents(
        self,
        documents: list[Document],
        namespace: str = NAMESPACE_STATIC,
        batch_size: int = OPTIMAL_UPSERT_BATCH_SIZE,
        show_progress: bool = True,
        parallel: bool = True,
    ) -> list[str]:
        """Embed and upsert documents with deterministic SHA-256 IDs.

        Args:
            documents: LangChain Document objects to add
            namespace: Target Pinecone namespace (static_corpus or news)
            batch_size: Number of documents to process in each batch
            show_progress: Whether to log progress information
            parallel: Whether to process batches in parallel

        Returns:
            List of vector IDs that were upserted

        Raises:
            VectorStoreError: If document addition fails
        """
        if not documents:
            self.logger.warning("add_documents_called_with_empty_list")
            return []

        try:
            total_docs = len(documents)

            self.logger.info(
                "starting_document_ingestion",
                total_documents=total_docs,
                namespace=namespace,
                batch_size=batch_size,
                parallel=parallel,
            )

            batches = [
                documents[i : i + batch_size] for i in range(0, total_docs, batch_size)
            ]

            if parallel and len(batches) > 1:
                all_ids = await self._process_batches_parallel(
                    batches, namespace, show_progress
                )
            else:
                all_ids = await self._process_batches_sequential(
                    batches, namespace, show_progress
                )

            self.logger.info(
                "document_ingestion_complete",
                total_documents=total_docs,
                successful_documents=len(all_ids),
                failed_documents=total_docs - len(all_ids),
            )

            return all_ids

        except Exception as e:
            self.logger.error("document_ingestion_failed", error=str(e))
            raise VectorStoreError(f"Failed to add documents: {e}") from e

    def _upsert_batch(self, batch: list[Document], namespace: str) -> list[str]:
        """Upsert one batch with content-hash IDs (runs in a worker thread)."""
        ids = [content_hash_id(doc.page_content) for doc in batch]
        return self.vector_store.add_documents(
            documents=batch,
            ids=ids,
            namespace=namespace,
        )

    async def _process_batches_sequential(
        self,
        batches: list[list[Document]],
        namespace: str,
        show_progress: bool,
    ) -> list[str]:
        """Process document batches sequentially.

        Args:
            batches: List of document batches
            namespace: Target Pinecone namespace
            show_progress: Whether to log progress

        Returns:
            List of vector IDs
        """
        all_ids: list[str] = []
        total_batches = len(batches)

        for batch_num, batch in enumerate(batches, 1):
            try:
                ids = await asyncio.to_thread(self._upsert_batch, batch, namespace)
                all_ids.extend(ids)

                if show_progress:
                    self.logger.info(
                        "batch_processed",
                        batch_num=batch_num,
                        total_batches=total_batches,
                        batch_size=len(batch),
                        documents_processed=len(all_ids),
                    )
            except Exception as e:
                self.logger.error(
                    "batch_processing_failed",
                    batch_num=batch_num,
                    batch_size=len(batch),
                    error=str(e),
                )
                continue

        return all_ids

    async def _process_batches_parallel(
        self,
        batches: list[list[Document]],
        namespace: str,
        show_progress: bool,
    ) -> list[str]:
        """Process document batches in parallel with limited concurrency.

        Args:
            batches: List of document batches
            namespace: Target Pinecone namespace
            show_progress: Whether to log progress

        Returns:
            List of vector IDs
        """
        all_ids: list[str] = []
        total_batches = len(batches)
        semaphore = asyncio.Semaphore(MAX_PARALLEL_BATCHES)

        async def process_batch(batch_num: int, batch: list[Document]) -> list[str]:
            async with semaphore:
                try:
                    ids = await asyncio.to_thread(self._upsert_batch, batch, namespace)

                    if show_progress:
                        self.logger.info(
                            "batch_processed",
                            batch_num=batch_num,
                            total_batches=total_batches,
                            batch_size=len(batch),
                        )

                    return ids
                except Exception as e:
                    self.logger.error(
                        "batch_processing_failed",
                        batch_num=batch_num,
                        batch_size=len(batch),
                        error=str(e),
                    )
                    return []

        tasks = [process_batch(i + 1, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_ids.extend(result)
            elif isinstance(result, Exception):
                self.logger.error("batch_task_failed", error=str(result))

        return all_ids

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
        use_cache: bool = True,
    ) -> list[Document]:
        """Perform semantic similarity search with caching.

        Args:
            query: Query string to search for
            k: Number of results to return (default: 5)
            filters: Optional metadata filters in Pinecone filter syntax
            namespace: Optional Pinecone namespace to search (None = default)
            use_cache: Whether to use cached results if available

        Returns:
            List of Document objects ranked by similarity

        Raises:
            VectorStoreError: If search fails
        """
        import time

        start_time = time.time()
        self._query_count += 1

        cache_key = self._cache_manager.get_vector_cache_key(
            query, k, {**(filters or {}), "_namespace": namespace}
        )
        if use_cache:
            cached_docs = self._cache_manager.vector_cache.get(cache_key)
            if cached_docs is not None:
                self._cache_hits += 1
                elapsed = time.time() - start_time
                self._total_query_time += elapsed
                self.logger.debug(
                    "vector_search_cache_hit",
                    query=query[:50],
                    elapsed_ms=elapsed * 1000,
                )
                return cast(list[Document], cached_docs)

        try:
            self.logger.info(
                "performing_similarity_search",
                query=query[:100],
                k=k,
                namespace=namespace,
                has_filters=filters is not None,
            )

            docs = await asyncio.to_thread(
                self.vector_store.similarity_search,
                query=query,
                k=k,
                filter=filters,
                namespace=namespace,
            )

            elapsed = time.time() - start_time
            self._total_query_time += elapsed

            self.logger.info(
                "similarity_search_complete",
                results_count=len(docs),
                elapsed_ms=elapsed * 1000,
            )

            if use_cache:
                self._cache_manager.vector_cache.set(cache_key, docs)

            return docs

        except Exception as e:
            self.logger.error("similarity_search_failed", error=str(e))
            raise VectorStoreError(f"Similarity search failed: {e}") from e

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[tuple[Document, float]]:
        """Perform semantic similarity search with relevance scores.

        Args:
            query: Query string to search for
            k: Number of results to return (default: 5)
            filters: Optional metadata filters in Pinecone filter syntax
            namespace: Optional Pinecone namespace to search

        Returns:
            List of (Document, score) tuples ranked by similarity

        Raises:
            VectorStoreError: If search fails
        """
        try:
            self.logger.info(
                "performing_similarity_search_with_score",
                query=query[:100],
                k=k,
                namespace=namespace,
                has_filters=filters is not None,
            )

            results = await asyncio.to_thread(
                self.vector_store.similarity_search_with_score,
                query=query,
                k=k,
                filter=filters,
                namespace=namespace,
            )

            self.logger.info(
                "similarity_search_with_score_complete",
                results_count=len(results),
            )

            return results

        except Exception as e:
            self.logger.error("similarity_search_with_score_failed", error=str(e))
            raise VectorStoreError(f"Similarity search with score failed: {e}") from e

    def get_stats(self) -> dict[str, Any]:
        """Get cache and query performance statistics."""
        cache_hit_rate = (
            self._cache_hits / self._query_count if self._query_count > 0 else 0.0
        )
        avg_query_time = (
            self._total_query_time / self._query_count if self._query_count > 0 else 0.0
        )

        return {
            "cache": self._cache_manager.vector_cache.get_stats(),
            "performance": {
                "total_queries": self._query_count,
                "cache_hits": self._cache_hits,
                "cache_hit_rate": cache_hit_rate,
                "average_query_time_ms": avg_query_time * 1000,
            },
        }

    async def close(self) -> None:
        """Clean up resources on application shutdown."""
        self.logger.info("closing_vector_store_manager", **self.get_stats())
        self._vector_store = None
