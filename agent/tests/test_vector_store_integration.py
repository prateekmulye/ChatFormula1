"""Integration tests for vector store operations.

These tests require actual Pinecone credentials and will create/use a test index.
Mark as integration tests to skip in unit test runs.
"""

import pytest
from langchain_core.documents import Document

from src.config.settings import Settings
from src.exceptions import VectorStoreError
from src.vector_store.manager import VectorStoreManager


@pytest.mark.integration
@pytest.mark.asyncio
class TestVectorStoreIntegration:
    """Integration tests for VectorStoreManager."""

    @pytest.fixture
    async def vector_store(self, test_settings: Settings):
        """Create vector store manager for testing."""
        # Skip if no real API keys
        if test_settings.pinecone_api_key.startswith("test-"):
            pytest.skip("Skipping integration test - no real Pinecone API key")

        manager = VectorStoreManager(test_settings)

        try:
            await manager.initialize()
            yield manager
        finally:
            # Cleanup if needed
            pass

    async def test_vector_store_initialization(self, vector_store: VectorStoreManager):
        """Test vector store can be initialized."""
        assert vector_store is not None
        assert vector_store.index_name is not None

    async def test_add_and_search_documents(self, vector_store: VectorStoreManager):
        """Test adding documents and searching."""
        # Create test documents
        docs = [
            Document(
                page_content="Lewis Hamilton won the 2020 F1 World Championship.",
                metadata={
                    "year": 2020,
                    "category": "championship",
                    "driver": "hamilton",
                },
            ),
            Document(
                page_content="Max Verstappen won the 2021 F1 World Championship.",
                metadata={
                    "year": 2021,
                    "category": "championship",
                    "driver": "verstappen",
                },
            ),
        ]

        # Add documents
        doc_ids = await vector_store.add_documents(docs)

        assert len(doc_ids) == 2

        # Search for documents
        results = await vector_store.similarity_search(
            query="Who won the 2021 championship?", top_k=2
        )

        assert len(results) > 0
        # Should find Verstappen document
        assert any("Verstappen" in doc.page_content for doc in results)

    async def test_search_with_metadata_filter(self, vector_store: VectorStoreManager):
        """Test searching with metadata filters."""
        # Add test documents
        docs = [
            Document(
                page_content="2020 championship data",
                metadata={"year": 2020, "category": "championship"},
            ),
            Document(
                page_content="2021 championship data",
                metadata={"year": 2021, "category": "championship"},
            ),
        ]

        await vector_store.add_documents(docs)

        # Search with year filter
        results = await vector_store.similarity_search(
            query="championship", top_k=5, filters={"year": 2021}
        )

        # Should only return 2021 documents
        for doc in results:
            if "year" in doc.metadata:
                assert doc.metadata["year"] == 2021

    async def test_health_check(self, vector_store: VectorStoreManager):
        """Test health check functionality."""
        is_healthy = await vector_store.health_check()

        assert is_healthy is True

    async def test_get_stats(self, vector_store: VectorStoreManager):
        """Test getting vector store statistics."""
        stats = await vector_store.get_stats()

        assert "total_vectors" in stats or "dimension" in stats
        assert isinstance(stats, dict)


@pytest.mark.integration
@pytest.mark.asyncio
class TestVectorStoreErrorHandling:
    """Integration tests for error handling."""

    async def test_invalid_api_key(self):
        """Test handling of invalid API key."""
        import os

        from src.config.settings import Settings

        # Create settings with invalid key
        os.environ["PINECONE_API_KEY"] = "invalid_key"
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["PINECONE_ENVIRONMENT"] = "test"
        os.environ["TAVILY_API_KEY"] = "test-key"

        from src.config.settings import get_settings

        get_settings.cache_clear()

        settings = Settings()

        # Should raise error on initialization
        with pytest.raises(VectorStoreError):
            manager = VectorStoreManager(settings)
            await manager.initialize()

    async def test_search_empty_query(self, test_settings: Settings):
        """Test searching with empty query."""
        if test_settings.pinecone_api_key.startswith("test-"):
            pytest.skip("Skipping integration test - no real Pinecone API key")

        manager = VectorStoreManager(test_settings)
        await manager.initialize()

        # Empty query should handle gracefully
        results = await manager.similarity_search(query="", top_k=5)

        # Should return empty or handle gracefully
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
