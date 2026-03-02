"""Unit tests for document processing."""

import pytest
from langchain_core.documents import Document

from src.config.settings import Settings
from src.ingestion.document_processor import (DocumentProcessingError,
                                              DocumentProcessor)


@pytest.mark.unit
class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""

    def test_initialization(self, test_settings: Settings):
        """Test processor initialization."""
        processor = DocumentProcessor(test_settings)

        assert processor.config == test_settings
        assert processor.text_splitter is not None
        assert len(processor._seen_hashes) == 0

    def test_process_text_documents_basic(self, test_settings: Settings):
        """Test basic text document processing."""
        processor = DocumentProcessor(test_settings)

        texts = [
            "Lewis Hamilton is a seven-time world champion.",
            "Max Verstappen won the 2021 championship.",
        ]

        docs = processor.process_text_documents(texts, chunk=False)

        assert len(docs) == 2
        assert all(isinstance(doc, Document) for doc in docs)
        assert docs[0].page_content == texts[0]
        assert docs[1].page_content == texts[1]

    def test_process_text_documents_with_metadata(self, test_settings: Settings):
        """Test text processing with metadata."""
        processor = DocumentProcessor(test_settings)

        texts = ["Test content"]
        metadatas = [{"category": "test", "year": 2024}]

        docs = processor.process_text_documents(texts, metadatas=metadatas, chunk=False)

        assert len(docs) == 1
        assert docs[0].metadata["category"] == "test"
        assert docs[0].metadata["year"] == 2024

    def test_process_text_documents_metadata_mismatch(self, test_settings: Settings):
        """Test error when metadata count doesn't match text count."""
        processor = DocumentProcessor(test_settings)

        texts = ["Text 1", "Text 2"]
        metadatas = [{"category": "test"}]  # Only one metadata

        with pytest.raises(DocumentProcessingError) as exc_info:
            processor.process_text_documents(texts, metadatas=metadatas)

        assert "must match" in str(exc_info.value).lower()

    def test_chunk_documents(self, test_settings: Settings):
        """Test document chunking."""
        processor = DocumentProcessor(test_settings)

        # Create a long document that will be chunked
        long_text = " ".join(
            ["This is sentence number {}.".format(i) for i in range(100)]
        )
        docs = [Document(page_content=long_text, metadata={"source": "test"})]

        chunked = processor.chunk_documents(docs)

        # Should create multiple chunks
        assert len(chunked) > 1

        # All chunks should have metadata
        for chunk in chunked:
            assert "chunk_index" in chunk.metadata
            assert "is_chunked" in chunk.metadata
            assert chunk.metadata["source"] == "test"

    def test_deduplicate_documents(self, test_settings: Settings):
        """Test document deduplication."""
        processor = DocumentProcessor(test_settings)

        # Create duplicate documents
        docs = [
            Document(page_content="Duplicate content", metadata={}),
            Document(page_content="Unique content", metadata={}),
            Document(page_content="Duplicate content", metadata={}),  # Duplicate
        ]

        unique_docs = processor.deduplicate_documents(docs)

        assert len(unique_docs) == 2
        assert unique_docs[0].page_content == "Duplicate content"
        assert unique_docs[1].page_content == "Unique content"

    def test_process_race_results(self, test_settings: Settings):
        """Test race result processing."""
        processor = DocumentProcessor(test_settings)

        race_data = [
            {
                "race_id": "2021_monaco",
                "driver_id": "verstappen",
                "constructor_id": "red_bull",
                "season": 2021,
                "round": 5,
                "circuit_id": "monaco",
                "quali_pos": 1,
                "grid_pos": 1,
                "finish_position": 1,
                "points": 25,
                "podium_finish": 1,
                "top_10_finish": 1,
            }
        ]

        docs = processor.process_race_results(race_data, chunk=False)

        assert len(docs) == 1
        assert "verstappen" in docs[0].page_content.lower()
        assert "monaco" in docs[0].page_content.lower()
        assert docs[0].metadata["category"] == "race_result"
        assert docs[0].metadata["season"] == 2021
        assert docs[0].metadata["driver_id"] == "verstappen"

    def test_process_driver_data(self, test_settings: Settings):
        """Test driver data processing."""
        processor = DocumentProcessor(test_settings)

        driver_data = [
            {
                "id": "hamilton",
                "code": "HAM",
                "number": 44,
                "name": "Lewis Hamilton",
                "constructor": "Mercedes",
                "nationality": "British",
            }
        ]

        docs = processor.process_driver_data(driver_data)

        assert len(docs) == 1
        assert "Lewis Hamilton" in docs[0].page_content
        assert "HAM" in docs[0].page_content
        assert docs[0].metadata["category"] == "driver_info"
        assert docs[0].metadata["driver_id"] == "hamilton"

    def test_process_race_info(self, test_settings: Settings):
        """Test race information processing."""
        processor = DocumentProcessor(test_settings)

        race_data = [
            {
                "id": "monaco_2024",
                "name": "Monaco Grand Prix",
                "circuit": "Circuit de Monaco",
                "country": "Monaco",
                "date": "2024-05-26",
                "season": 2024,
                "round": 8,
            }
        ]

        docs = processor.process_race_info(race_data)

        assert len(docs) == 1
        assert "Monaco Grand Prix" in docs[0].page_content
        assert "Circuit de Monaco" in docs[0].page_content
        assert docs[0].metadata["category"] == "race_info"
        assert docs[0].metadata["year"] == 2024

    def test_clean_text(self, test_settings: Settings):
        """Test text cleaning."""
        processor = DocumentProcessor(test_settings)

        dirty_text = "  Multiple   spaces   and\n\nnewlines  "
        clean_text = processor._clean_text(dirty_text)

        assert clean_text == "Multiple spaces and newlines"

    def test_clean_text_empty(self, test_settings: Settings):
        """Test cleaning empty text."""
        processor = DocumentProcessor(test_settings)

        assert processor._clean_text("") == ""
        assert processor._clean_text("   ") == ""

    def test_hash_document(self, test_settings: Settings):
        """Test document hashing."""
        processor = DocumentProcessor(test_settings)

        doc1 = Document(page_content="Same content", metadata={})
        doc2 = Document(page_content="Same content", metadata={"different": "metadata"})
        doc3 = Document(page_content="Different content", metadata={})

        hash1 = processor._hash_document(doc1)
        hash2 = processor._hash_document(doc2)
        hash3 = processor._hash_document(doc3)

        # Same content should have same hash regardless of metadata
        assert hash1 == hash2
        # Different content should have different hash
        assert hash1 != hash3

    def test_clear_deduplication_cache(self, test_settings: Settings):
        """Test clearing deduplication cache."""
        processor = DocumentProcessor(test_settings)

        # Add some documents to build cache
        docs = [
            Document(page_content="Doc 1", metadata={}),
            Document(page_content="Doc 2", metadata={}),
        ]
        processor.deduplicate_documents(docs)

        assert len(processor._seen_hashes) == 2

        processor.clear_deduplication_cache()

        assert len(processor._seen_hashes) == 0

    def test_get_stats(self, test_settings: Settings):
        """Test getting processing statistics."""
        processor = DocumentProcessor(test_settings)

        # Process some documents
        docs = [Document(page_content="Test", metadata={})]
        processor.deduplicate_documents(docs)

        stats = processor.get_stats()

        assert "unique_documents_seen" in stats
        assert "chunk_size" in stats
        assert "chunk_overlap" in stats
        assert stats["unique_documents_seen"] == 1
        assert stats["chunk_size"] == test_settings.chunk_size

    def test_process_with_chunking(self, test_settings: Settings):
        """Test processing with automatic chunking."""
        processor = DocumentProcessor(test_settings)

        # Create long text that will be chunked
        long_text = " ".join(["Sentence {}.".format(i) for i in range(200)])
        texts = [long_text]

        docs = processor.process_text_documents(texts, chunk=True)

        # Should create multiple chunks
        assert len(docs) > 1

        # All chunks should have chunking metadata
        for doc in docs:
            assert doc.metadata.get("is_chunked") is True
            assert "chunk_index" in doc.metadata

    def test_process_empty_text_list(self, test_settings: Settings):
        """Test processing empty text list."""
        processor = DocumentProcessor(test_settings)

        docs = processor.process_text_documents([], chunk=False)

        assert len(docs) == 0

    def test_process_race_results_with_missing_fields(self, test_settings: Settings):
        """Test race result processing with missing optional fields."""
        processor = DocumentProcessor(test_settings)

        race_data = [
            {
                "race_id": "2021_monaco",
                "driver_id": "verstappen",
                "constructor_id": "red_bull",
                "season": 2021,
                "round": 5,
                "circuit_id": "monaco",
                # Missing optional fields
            }
        ]

        docs = processor.process_race_results(race_data, chunk=False)

        assert len(docs) == 1
        assert "verstappen" in docs[0].page_content.lower()
        assert docs[0].metadata["season"] == 2021


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
