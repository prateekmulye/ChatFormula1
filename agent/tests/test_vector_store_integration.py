"""Tests for the vector store: deterministic IDs plus live integration.

The deterministic-ID tests run everywhere; the integration tests require
real Pinecone credentials and skip themselves under dummy keys.
"""

import pytest
from langchain_core.documents import Document

from chatf1_agent.retrieval.vector_store import (
    NAMESPACE_NEWS,
    NAMESPACE_STATIC,
    VectorStoreManager,
    content_hash_id,
)
from chatf1_agent.settings import Settings

from .conftest import has_real_api_keys


@pytest.mark.unit
class TestDeterministicIds:
    """Tests for SHA-256 content-hash vector IDs."""

    def test_same_content_same_id(self):
        """Identical content always produces the same ID (idempotent upserts)."""
        content = "Max Verstappen won the 2024 championship."

        assert content_hash_id(content) == content_hash_id(content)

    def test_different_content_different_id(self):
        """Distinct content produces distinct IDs."""
        first = content_hash_id("Hamilton won in 2020.")
        second = content_hash_id("Verstappen won in 2021.")

        assert first != second

    def test_id_is_sha256_hex(self):
        """IDs are 64-character hex SHA-256 digests."""
        vector_id = content_hash_id("any content")

        assert len(vector_id) == 64
        assert all(c in "0123456789abcdef" for c in vector_id)

    def test_known_digest(self):
        """The hash matches a precomputed SHA-256 digest."""
        assert content_hash_id("abc") == (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )


@pytest.mark.unit
class TestNamespaces:
    """Tests for the namespace constants."""

    def test_namespace_values(self):
        """Namespaces match the architecture: static_corpus and news."""
        assert NAMESPACE_STATIC == "static_corpus"
        assert NAMESPACE_NEWS == "news"


@pytest.mark.unit
def test_manager_requires_credentials(monkeypatch: pytest.MonkeyPatch):
    """Construction fails fast without Pinecone/OpenAI keys."""
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError, match="pinecone_api_key"):
        VectorStoreManager(settings)


@pytest.mark.integration
@pytest.mark.asyncio
class TestVectorStoreIntegration:
    """Live Pinecone integration tests (skipped under dummy keys)."""

    @pytest.fixture
    async def vector_store(self, test_settings: Settings):
        """Initialized manager against the real index."""
        if not has_real_api_keys():
            pytest.skip("Skipping integration test - no real API keys")

        manager = VectorStoreManager(test_settings)
        await manager.initialize()
        yield manager
        await manager.close()

    async def test_health_check(self, vector_store: VectorStoreManager):
        """The index reports healthy with the expected dimension."""
        health = await vector_store.health_check()

        assert health["status"] == "healthy"
        assert health["dimension"] == vector_store.config.pinecone_dimension

    async def test_add_and_search_documents(self, vector_store: VectorStoreManager):
        """Documents upsert deterministically and are searchable."""
        docs = [
            Document(
                page_content="Lewis Hamilton won the 2020 F1 World Championship.",
                metadata={"year": 2020, "category": "championship"},
            ),
            Document(
                page_content="Max Verstappen won the 2021 F1 World Championship.",
                metadata={"year": 2021, "category": "championship"},
            ),
        ]

        ids = await vector_store.add_documents(docs, namespace=NAMESPACE_STATIC)

        assert sorted(ids) == sorted(content_hash_id(doc.page_content) for doc in docs)

        results = await vector_store.similarity_search(
            query="Who won the 2021 championship?",
            k=2,
            namespace=NAMESPACE_STATIC,
        )

        assert len(results) > 0
        assert any("Verstappen" in doc.page_content for doc in results)

    async def test_reingest_does_not_duplicate(self, vector_store: VectorStoreManager):
        """Upserting the same document twice yields the same vector ID."""
        doc = Document(
            page_content="Monaco Grand Prix is held on the streets of Monte Carlo.",
            metadata={"category": "circuit"},
        )

        first = await vector_store.add_documents([doc], namespace=NAMESPACE_STATIC)
        second = await vector_store.add_documents([doc], namespace=NAMESPACE_STATIC)

        assert first == second
