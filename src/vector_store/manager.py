"""Vector store manager for Pinecone integration using langchain-pinecone."""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from src.config.settings import Settings
from src.exceptions import VectorStoreError

logger = structlog.get_logger(__name__)


# Optimized batch sizes for different operations
OPTIMAL_EMBEDDING_BATCH_SIZE = 100  # OpenAI embeddings API optimal batch size
OPTIMAL_UPSERT_BATCH_SIZE = 100  # Pinecone upsert optimal batch size
MAX_PARALLEL_BATCHES = 3  # Maximum parallel batch operations


class VectorStoreManager:
    """Manages Pinecone vector store operations with LangChain integration.

    This class provides a high-level interface for:
    - Initializing and managing Pinecone connections
    - Creating and validating indexes
    - Health checking
    - Document embedding and upsertion
    - Semantic search and retrieval

    Uses langchain-pinecone for seamless LangChain integration.
    """

    def __init__(self, config: Settings) -> None:
        """Initialize VectorStoreManager with configuration.

        Args:
            config: Application settings containing Pinecone and OpenAI configuration

        Raises:
            VectorStoreError: If initialization fails
        """
        self.config = config
        self.logger = logger.bind(component="vector_store_manager")

        # Initialize Pinecone client with connection pooling
        try:
            self.pc = Pinecone(
                api_key=config.pinecone_api_key,
                pool_threads=10,  # Connection pool size for parallel operations
            )
            self.logger.info("pinecone_client_initialized", pool_threads=10)
        except Exception as e:
            self.logger.error("pinecone_client_init_failed", error=str(e))
            raise VectorStoreError(f"Failed to initialize Pinecone client: {e}") from e

        # Initialize embeddings with optimized batch processing
        try:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=config.openai_api_key,
                model=config.openai_embedding_model,
                chunk_size=OPTIMAL_EMBEDDING_BATCH_SIZE,  # Optimize batch size
                max_retries=3,  # Add retry logic
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
        self._vector_store: Optional[PineconeVectorStore] = None

        # Use centralized cache manager for better performance
        from src.utils.cache import get_cache_manager

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
        """Initialize vector store with retry logic.

        Creates index if it doesn't exist and initializes PineconeVectorStore.

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
        """Ensure Pinecone index exists, create if necessary.

        Raises:
            VectorStoreError: If index creation or validation fails
        """
        try:
            # Run synchronous Pinecone operations in executor
            existing_indexes = await asyncio.to_thread(
                lambda: [idx.name for idx in self.pc.list_indexes()]
            )

            if self.index_name not in existing_indexes:
                self.logger.info(
                    "creating_index",
                    index_name=self.index_name,
                    dimension=self.config.pinecone_dimension,
                )

                # Create serverless index with optimized parameters
                await asyncio.to_thread(
                    self.pc.create_index,
                    name=self.index_name,
                    dimension=self.config.pinecone_dimension,
                    metric="cosine",  # Cosine similarity for normalized embeddings
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1",
                    ),
                )

                self.logger.info("index_created", index_name=self.index_name)
            else:
                self.logger.info("index_exists", index_name=self.index_name)

            # Validate index configuration
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
        """Initialize PineconeVectorStore instance.

        Raises:
            VectorStoreError: If vector store initialization fails
        """
        try:
            # PineconeVectorStore initialization is synchronous
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
        """Get initialized vector store instance.

        Returns:
            PineconeVectorStore: Initialized vector store

        Raises:
            VectorStoreError: If vector store not initialized
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
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on vector store.

        Returns:
            Dict containing health status information:
                - status: "healthy" or "unhealthy"
                - index_name: Name of the Pinecone index
                - dimension: Vector dimension
                - metric: Distance metric used
                - total_vector_count: Number of vectors in index
                - error: Error message if unhealthy

        """
        try:
            # Check if vector store is initialized
            if self._vector_store is None:
                return {
                    "status": "unhealthy",
                    "error": "Vector store not initialized",
                }

            # Get index stats
            index = self.pc.Index(self.index_name)
            stats = await asyncio.to_thread(index.describe_index_stats)

            # Get index description
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
            error_msg = f"Health check failed: {e}"
            self.logger.error("health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": error_msg,
            }

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about the Pinecone index.

        Returns:
            Dict containing index statistics

        Raises:
            VectorStoreError: If stats retrieval fails
        """
        try:
            index = self.pc.Index(self.index_name)
            stats = await asyncio.to_thread(index.describe_index_stats)

            stats_dict = {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces,
            }

            self.logger.info("index_stats_retrieved", **stats_dict)
            return stats_dict

        except Exception as e:
            self.logger.error("index_stats_failed", error=str(e))
            raise VectorStoreError(f"Failed to get index stats: {e}") from e

    async def add_documents(
        self,
        documents: List[Document],
        batch_size: int = OPTIMAL_UPSERT_BATCH_SIZE,
        show_progress: bool = True,
        parallel: bool = True,
    ) -> List[str]:
        """Embed and add documents to vector store with optimized batch processing.

        Uses OpenAIEmbeddings for embedding generation and PineconeVectorStore's
        native add_documents method for efficient upsertion. Supports parallel
        batch processing for improved throughput.

        Args:
            documents: List of LangChain Document objects to add
            batch_size: Number of documents to process in each batch (default: optimized)
            show_progress: Whether to log progress information
            parallel: Whether to process batches in parallel (default: True)

        Returns:
            List of document IDs that were added

        Raises:
            VectorStoreError: If document addition fails
        """
        if not documents:
            self.logger.warning("add_documents_called_with_empty_list")
            return []

        try:
            total_docs = len(documents)
            all_ids: List[str] = []

            self.logger.info(
                "starting_document_ingestion",
                total_documents=total_docs,
                batch_size=batch_size,
                parallel=parallel,
            )

            # Split documents into batches
            batches = [
                documents[i : i + batch_size] for i in range(0, total_docs, batch_size)
            ]

            if parallel and len(batches) > 1:
                # Process batches in parallel with limited concurrency
                all_ids = await self._process_batches_parallel(batches, show_progress)
            else:
                # Process batches sequentially
                all_ids = await self._process_batches_sequential(batches, show_progress)

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

    async def _process_batches_sequential(
        self,
        batches: List[List[Document]],
        show_progress: bool,
    ) -> List[str]:
        """Process document batches sequentially.

        Args:
            batches: List of document batches
            show_progress: Whether to log progress

        Returns:
            List of document IDs
        """
        all_ids: List[str] = []
        total_batches = len(batches)

        for batch_num, batch in enumerate(batches, 1):
            try:
                ids = await asyncio.to_thread(
                    self.vector_store.add_documents,
                    documents=batch,
                )
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
        batches: List[List[Document]],
        show_progress: bool,
    ) -> List[str]:
        """Process document batches in parallel with limited concurrency.

        Args:
            batches: List of document batches
            show_progress: Whether to log progress

        Returns:
            List of document IDs
        """
        all_ids: List[str] = []
        total_batches = len(batches)

        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(MAX_PARALLEL_BATCHES)

        async def process_batch(batch_num: int, batch: List[Document]) -> List[str]:
            async with semaphore:
                try:
                    ids = await asyncio.to_thread(
                        self.vector_store.add_documents,
                        documents=batch,
                    )

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

        # Process all batches in parallel
        tasks = [process_batch(i + 1, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all IDs
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
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 100,
    ) -> List[str]:
        """Embed and add raw texts to vector store.

        Convenience method for adding texts without creating Document objects.

        Args:
            texts: List of text strings to embed and add
            metadatas: Optional list of metadata dicts (one per text)
            batch_size: Number of texts to process in each batch

        Returns:
            List of document IDs that were added

        Raises:
            VectorStoreError: If text addition fails
        """
        if not texts:
            self.logger.warning("add_texts_called_with_empty_list")
            return []

        if metadatas and len(metadatas) != len(texts):
            raise VectorStoreError(
                f"Metadata count ({len(metadatas)}) must match text count ({len(texts)})"
            )

        try:
            total_texts = len(texts)
            all_ids: List[str] = []

            self.logger.info(
                "starting_text_ingestion",
                total_texts=total_texts,
                batch_size=batch_size,
            )

            # Process texts in batches
            for i in range(0, total_texts, batch_size):
                batch_texts = texts[i : i + batch_size]
                batch_metadatas = metadatas[i : i + batch_size] if metadatas else None

                try:
                    # Use PineconeVectorStore's add_texts method
                    ids = await asyncio.to_thread(
                        self.vector_store.add_texts,
                        texts=batch_texts,
                        metadatas=batch_metadatas,
                    )

                    all_ids.extend(ids)

                    self.logger.info(
                        "text_batch_processed",
                        batch_size=len(batch_texts),
                        texts_processed=len(all_ids),
                    )

                except Exception as e:
                    self.logger.error(
                        "text_batch_failed",
                        batch_size=len(batch_texts),
                        error=str(e),
                    )
                    continue

            self.logger.info(
                "text_ingestion_complete",
                total_texts=total_texts,
                successful_texts=len(all_ids),
            )

            return all_ids

        except VectorStoreError:
            raise
        except Exception as e:
            self.logger.error("text_ingestion_failed", error=str(e))
            raise VectorStoreError(f"Failed to add texts: {e}") from e

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query string.

        Uses OpenAIEmbeddings to generate vector representation.

        Args:
            query: Query string to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            VectorStoreError: If embedding generation fails
        """
        try:
            embedding = await asyncio.to_thread(
                self.embeddings.embed_query,
                query,
            )

            self.logger.debug(
                "query_embedded",
                query_length=len(query),
                embedding_dimension=len(embedding),
            )

            return embedding

        except Exception as e:
            self.logger.error("query_embedding_failed", error=str(e))
            raise VectorStoreError(f"Failed to embed query: {e}") from e

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents.

        Uses OpenAIEmbeddings to generate vector representations.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            VectorStoreError: If embedding generation fails
        """
        try:
            embeddings = await asyncio.to_thread(
                self.embeddings.embed_documents,
                texts,
            )

            self.logger.debug(
                "documents_embedded",
                document_count=len(texts),
                embedding_dimension=len(embeddings[0]) if embeddings else 0,
            )

            return embeddings

        except Exception as e:
            self.logger.error("document_embedding_failed", error=str(e))
            raise VectorStoreError(f"Failed to embed documents: {e}") from e

    def _get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for vector store operations.

        Returns:
            Dictionary with performance metrics
        """
        cache_hit_rate = (
            self._cache_hits / self._query_count if self._query_count > 0 else 0.0
        )
        avg_query_time = (
            self._total_query_time / self._query_count if self._query_count > 0 else 0.0
        )

        return {
            "total_queries": self._query_count,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "average_query_time_ms": avg_query_time * 1000,
        }

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
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> List[Document]:
        """Perform semantic similarity search with optimized caching.

        Uses PineconeVectorStore's similarity_search method with optional
        metadata filtering and intelligent caching.

        Args:
            query: Query string to search for
            k: Number of results to return (default: 5)
            filters: Optional metadata filters in Pinecone filter syntax
                    Example: {"year": 2024, "category": "race_result"}
            use_cache: Whether to use cached results if available

        Returns:
            List of Document objects ranked by similarity

        Raises:
            VectorStoreError: If search fails

        Example:
            >>> docs = await manager.similarity_search(
            ...     "Lewis Hamilton wins",
            ...     k=5,
            ...     filters={"year": {"$gte": 2020}}
            ... )
        """
        import time

        start_time = time.time()

        # Track query metrics
        self._query_count += 1

        # Check cache first using centralized cache manager
        if use_cache:
            cache_key = self._cache_manager.get_vector_cache_key(query, k, filters)
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
                return cached_docs

        try:
            self.logger.info(
                "performing_similarity_search",
                query=query[:100],  # Truncate for logging
                k=k,
                has_filters=filters is not None,
            )

            # Use PineconeVectorStore's similarity_search
            docs = await asyncio.to_thread(
                self.vector_store.similarity_search,
                query=query,
                k=k,
                filter=filters,
            )

            elapsed = time.time() - start_time
            self._total_query_time += elapsed

            self.logger.info(
                "similarity_search_complete",
                results_count=len(docs),
                elapsed_ms=elapsed * 1000,
            )

            # Cache results using centralized cache manager
            if use_cache:
                cache_key = self._cache_manager.get_vector_cache_key(query, k, filters)
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
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """Perform semantic similarity search with relevance scores.

        Uses PineconeVectorStore's similarity_search_with_score method.

        Args:
            query: Query string to search for
            k: Number of results to return (default: 5)
            filters: Optional metadata filters in Pinecone filter syntax

        Returns:
            List of tuples (Document, score) ranked by similarity
            Scores are typically between 0 and 1, with higher being more similar

        Raises:
            VectorStoreError: If search fails

        Example:
            >>> results = await manager.similarity_search_with_score(
            ...     "Max Verstappen championship",
            ...     k=3
            ... )
            >>> for doc, score in results:
            ...     print(f"Score: {score:.3f} - {doc.page_content[:50]}")
        """
        try:
            self.logger.info(
                "performing_similarity_search_with_score",
                query=query[:100],
                k=k,
                has_filters=filters is not None,
            )

            # Use PineconeVectorStore's similarity_search_with_score
            results = await asyncio.to_thread(
                self.vector_store.similarity_search_with_score,
                query=query,
                k=k,
                filter=filters,
            )

            self.logger.info(
                "similarity_search_with_score_complete",
                results_count=len(results),
                scores=[score for _, score in results],
            )

            return results

        except Exception as e:
            self.logger.error("similarity_search_with_score_failed", error=str(e))
            raise VectorStoreError(f"Similarity search with score failed: {e}") from e

    async def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Perform Maximum Marginal Relevance (MMR) search.

        MMR balances relevance with diversity to avoid redundant results.

        Args:
            query: Query string to search for
            k: Number of results to return
            fetch_k: Number of candidates to fetch before MMR reranking
            lambda_mult: Balance between relevance (1.0) and diversity (0.0)
            filters: Optional metadata filters

        Returns:
            List of diverse, relevant Document objects

        Raises:
            VectorStoreError: If search fails
        """
        try:
            self.logger.info(
                "performing_mmr_search",
                query=query[:100],
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
            )

            # Use PineconeVectorStore's max_marginal_relevance_search
            docs = await asyncio.to_thread(
                self.vector_store.max_marginal_relevance_search,
                query=query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
                filter=filters,
            )

            self.logger.info(
                "mmr_search_complete",
                results_count=len(docs),
            )

            return docs

        except Exception as e:
            self.logger.error("mmr_search_failed", error=str(e))
            raise VectorStoreError(f"MMR search failed: {e}") from e

    async def search_by_metadata(
        self,
        filters: Dict[str, Any],
        k: int = 10,
    ) -> List[Document]:
        """Search documents by metadata filters only (no semantic search).

        Useful for retrieving documents by specific attributes like year,
        category, driver, team, etc.

        Args:
            filters: Metadata filters in Pinecone filter syntax
                    Example: {"year": 2024, "driver": "Lewis Hamilton"}
            k: Maximum number of results to return

        Returns:
            List of Document objects matching the filters

        Raises:
            VectorStoreError: If search fails

        Example:
            >>> # Get all race results from 2024
            >>> docs = await manager.search_by_metadata(
            ...     filters={"year": 2024, "category": "race_result"},
            ...     k=20
            ... )
        """
        try:
            self.logger.info(
                "searching_by_metadata",
                filters=filters,
                k=k,
            )

            # Use a broad query with strict filters
            # This effectively does metadata-only search
            docs = await asyncio.to_thread(
                self.vector_store.similarity_search,
                query="",  # Empty query
                k=k,
                filter=filters,
            )

            self.logger.info(
                "metadata_search_complete",
                results_count=len(docs),
            )

            return docs

        except Exception as e:
            self.logger.error("metadata_search_failed", error=str(e))
            raise VectorStoreError(f"Metadata search failed: {e}") from e

    def clear_cache(self) -> None:
        """Clear the vector search cache."""
        cleared = self._cache_manager.vector_cache.clear()
        self.logger.info("vector_cache_cleared", entries_removed=cleared)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for vector store.

        Returns:
            Dictionary with cache and performance statistics
        """
        cache_stats = self._cache_manager.vector_cache.get_stats()
        perf_stats = self._get_performance_stats()

        return {
            "cache": cache_stats,
            "performance": perf_stats,
        }

    async def close(self) -> None:
        """Clean up resources and close connections.

        Should be called when shutting down the application.
        """
        self.logger.info("closing_vector_store_manager")

        # Log final performance stats
        stats = self.get_cache_stats()
        self.logger.info("final_performance_stats", **stats)

        self._vector_store = None
        # Pinecone client doesn't require explicit cleanup
        self.logger.info("vector_store_manager_closed")
