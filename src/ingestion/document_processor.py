"""Document processing for text chunking and metadata extraction."""

import hashlib
import re
from typing import Any, Dict, List, Optional, Set

import structlog
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.settings import Settings
from src.exceptions import ChatFormula1Error

logger = structlog.get_logger(__name__)


class DocumentProcessingError(ChatFormula1Error):
    """Exception raised when document processing fails."""

    pass


class DocumentProcessor:
    """Process documents for ingestion into vector store.

    Handles:
    - Text chunking with semantic overlap
    - Metadata extraction from source data
    - Document deduplication
    - Content cleaning and normalization
    """

    def __init__(self, config: Settings):
        """Initialize DocumentProcessor.

        Args:
            config: Application settings containing chunk size and overlap
        """
        self.config = config
        self.logger = logger.bind(component="document_processor")

        # Initialize text splitter with semantic chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",  # Paragraph breaks
                "\n",  # Line breaks
                ". ",  # Sentence breaks
                ", ",  # Clause breaks
                " ",  # Word breaks
                "",  # Character breaks
            ],
            is_separator_regex=False,
        )

        # Track seen document hashes for deduplication
        self._seen_hashes: Set[str] = set()

        self.logger.info(
            "document_processor_initialized",
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def process_race_results(
        self,
        race_data: List[Dict[str, Any]],
        chunk: bool = True,
    ) -> List[Document]:
        """Process race result data into documents.

        Args:
            race_data: List of race result dictionaries
            chunk: Whether to chunk long documents

        Returns:
            List of LangChain Document objects
        """
        documents: List[Document] = []

        self.logger.info("processing_race_results", total_records=len(race_data))

        for record in race_data:
            try:
                # Create narrative text from race result
                text = self._create_race_result_text(record)

                # Extract metadata
                metadata = self._extract_race_metadata(record)

                # Create document
                doc = Document(page_content=text, metadata=metadata)

                documents.append(doc)

            except Exception as e:
                self.logger.error(
                    "race_result_processing_failed", record=record, error=str(e)
                )
                continue

        # Chunk if requested
        if chunk:
            documents = self.chunk_documents(documents)

        # Deduplicate
        documents = self.deduplicate_documents(documents)

        self.logger.info(
            "race_results_processed",
            input_records=len(race_data),
            output_documents=len(documents),
        )

        return documents

    def process_driver_data(
        self,
        driver_data: List[Dict[str, Any]],
    ) -> List[Document]:
        """Process driver data into documents.

        Args:
            driver_data: List of driver dictionaries

        Returns:
            List of LangChain Document objects
        """
        documents: List[Document] = []

        self.logger.info("processing_driver_data", total_drivers=len(driver_data))

        for driver in driver_data:
            try:
                # Create narrative text about driver
                text = self._create_driver_text(driver)

                # Extract metadata
                metadata = self._extract_driver_metadata(driver)

                # Create document
                doc = Document(page_content=text, metadata=metadata)

                documents.append(doc)

            except Exception as e:
                self.logger.error(
                    "driver_processing_failed", driver=driver, error=str(e)
                )
                continue

        # Deduplicate
        documents = self.deduplicate_documents(documents)

        self.logger.info(
            "driver_data_processed",
            input_drivers=len(driver_data),
            output_documents=len(documents),
        )

        return documents

    def process_race_info(
        self,
        race_data: List[Dict[str, Any]],
    ) -> List[Document]:
        """Process race information into documents.

        Args:
            race_data: List of race dictionaries

        Returns:
            List of LangChain Document objects
        """
        documents: List[Document] = []

        self.logger.info("processing_race_info", total_races=len(race_data))

        for race in race_data:
            try:
                # Create narrative text about race
                text = self._create_race_info_text(race)

                # Extract metadata
                metadata = self._extract_race_info_metadata(race)

                # Create document
                doc = Document(page_content=text, metadata=metadata)

                documents.append(doc)

            except Exception as e:
                self.logger.error(
                    "race_info_processing_failed", race=race, error=str(e)
                )
                continue

        # Deduplicate
        documents = self.deduplicate_documents(documents)

        self.logger.info(
            "race_info_processed",
            input_races=len(race_data),
            output_documents=len(documents),
        )

        return documents

    def process_text_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        chunk: bool = True,
    ) -> List[Document]:
        """Process raw text documents.

        Args:
            texts: List of text strings
            metadatas: Optional list of metadata dicts
            chunk: Whether to chunk long documents

        Returns:
            List of LangChain Document objects
        """
        if metadatas and len(metadatas) != len(texts):
            raise DocumentProcessingError(
                f"Metadata count ({len(metadatas)}) must match text count ({len(texts)})"
            )

        documents: List[Document] = []

        for idx, text in enumerate(texts):
            metadata = metadatas[idx] if metadatas else {}

            # Clean text
            cleaned_text = self._clean_text(text)

            if not cleaned_text:
                continue

            doc = Document(page_content=cleaned_text, metadata=metadata)

            documents.append(doc)

        # Chunk if requested
        if chunk:
            documents = self.chunk_documents(documents)

        # Deduplicate
        documents = self.deduplicate_documents(documents)

        self.logger.info(
            "text_documents_processed",
            input_texts=len(texts),
            output_documents=len(documents),
        )

        return documents

    def chunk_documents(
        self,
        documents: List[Document],
    ) -> List[Document]:
        """Chunk documents using semantic text splitter.

        Args:
            documents: List of documents to chunk

        Returns:
            List of chunked documents with preserved metadata
        """
        self.logger.info("chunking_documents", input_documents=len(documents))

        chunked_docs = self.text_splitter.split_documents(documents)

        # Add chunk metadata
        for idx, doc in enumerate(chunked_docs):
            doc.metadata["chunk_index"] = idx
            doc.metadata["is_chunked"] = True

        self.logger.info(
            "documents_chunked",
            input_documents=len(documents),
            output_chunks=len(chunked_docs),
        )

        return chunked_docs

    def deduplicate_documents(
        self,
        documents: List[Document],
    ) -> List[Document]:
        """Remove duplicate documents based on content hash.

        Args:
            documents: List of documents to deduplicate

        Returns:
            List of unique documents
        """
        unique_docs: List[Document] = []
        duplicates_found = 0

        for doc in documents:
            doc_hash = self._hash_document(doc)

            if doc_hash not in self._seen_hashes:
                self._seen_hashes.add(doc_hash)
                unique_docs.append(doc)
            else:
                duplicates_found += 1

        if duplicates_found > 0:
            self.logger.info(
                "documents_deduplicated",
                input_documents=len(documents),
                unique_documents=len(unique_docs),
                duplicates_removed=duplicates_found,
            )

        return unique_docs

    def _create_race_result_text(self, record: Dict[str, Any]) -> str:
        """Create narrative text from race result record.

        Args:
            record: Race result dictionary

        Returns:
            Formatted text describing the race result
        """
        parts = []

        # Basic race info
        race_id = record.get("race_id", "")
        season = record.get("season", "")
        round_num = record.get("round", "")
        circuit = record.get("circuit_id", "")

        parts.append(
            f"Race: {race_id} - Season {season}, Round {round_num} at {circuit}"
        )

        # Driver and team
        driver = record.get("driver_id", "")
        constructor = record.get("constructor_id", "")
        parts.append(f"Driver: {driver} ({constructor})")

        # Qualifying and grid
        quali_pos = record.get("quali_pos")
        grid_pos = record.get("grid_pos")
        if quali_pos:
            parts.append(f"Qualified: P{quali_pos}")
        if grid_pos:
            parts.append(f"Grid Position: P{grid_pos}")

        # Race result
        finish_pos = record.get("finish_position")
        points = record.get("points")
        if finish_pos:
            parts.append(f"Finished: P{finish_pos}")
        if points:
            parts.append(f"Points: {points}")

        # Achievements
        if record.get("podium_finish"):
            parts.append("Podium finish")
        if record.get("top_10_finish"):
            parts.append("Top 10 finish")

        return ". ".join(parts) + "."

    def _create_driver_text(self, driver: Dict[str, Any]) -> str:
        """Create narrative text from driver data.

        Args:
            driver: Driver dictionary

        Returns:
            Formatted text describing the driver
        """
        parts = []

        name = driver.get("name", "")
        code = driver.get("code", "")
        number = driver.get("number")

        parts.append(f"Driver: {name} ({code})")

        if number:
            parts.append(f"Number: {number}")

        constructor = driver.get("constructor")
        if constructor:
            parts.append(f"Team: {constructor}")

        nationality = driver.get("nationality")
        if nationality:
            parts.append(f"Nationality: {nationality}")

        return ". ".join(parts) + "."

    def _create_race_info_text(self, race: Dict[str, Any]) -> str:
        """Create narrative text from race information.

        Args:
            race: Race dictionary

        Returns:
            Formatted text describing the race
        """
        parts = []

        name = race.get("name", "")
        circuit = race.get("circuit", "")
        country = race.get("country", "")

        parts.append(f"Race: {name}")

        if circuit:
            parts.append(f"Circuit: {circuit}")

        if country:
            parts.append(f"Country: {country}")

        date = race.get("date")
        if date:
            parts.append(f"Date: {date}")

        season = race.get("season")
        round_num = race.get("round")
        if season and round_num:
            parts.append(f"Season {season}, Round {round_num}")

        return ". ".join(parts) + "."

    def _extract_race_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from race result record.

        Args:
            record: Race result dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            "category": "race_result",
            "source": "historical_features",
        }

        # Add available fields
        for field in [
            "race_id",
            "driver_id",
            "constructor_id",
            "season",
            "round",
            "circuit_id",
            "finish_position",
        ]:
            if field in record and record[field] is not None:
                metadata[field] = record[field]

        # Add year from season
        if "season" in record:
            metadata["year"] = record["season"]

        return metadata

    def _extract_driver_metadata(self, driver: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from driver data.

        Args:
            driver: Driver dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            "category": "driver_info",
            "source": "driver_data",
        }

        # Add available fields
        for field in ["id", "code", "name", "constructor", "nationality"]:
            if field in driver and driver[field] is not None:
                metadata[field] = driver[field]

        # Use driver ID as driver_id for consistency
        if "id" in driver:
            metadata["driver_id"] = driver["id"]

        return metadata

    def _extract_race_info_metadata(self, race: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from race information.

        Args:
            race: Race dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            "category": "race_info",
            "source": "race_data",
        }

        # Add available fields
        for field in ["id", "name", "circuit", "country", "date", "season", "round"]:
            if field in race and race[field] is not None:
                metadata[field] = race[field]

        # Add year from season
        if "season" in race:
            metadata["year"] = race["season"]

        # Use race ID as race_id for consistency
        if "id" in race:
            metadata["race_id"] = race["id"]

        return metadata

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text.

        Args:
            text: Raw text string

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _hash_document(self, doc: Document) -> str:
        """Generate hash for document content.

        Args:
            doc: Document to hash

        Returns:
            MD5 hash of document content
        """
        content = doc.page_content.encode("utf-8")
        return hashlib.md5(content).hexdigest()

    def clear_deduplication_cache(self) -> None:
        """Clear the deduplication cache."""
        cache_size = len(self._seen_hashes)
        self._seen_hashes.clear()
        self.logger.info("deduplication_cache_cleared", entries_removed=cache_size)

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics.

        Returns:
            Dictionary containing processing stats
        """
        return {
            "unique_documents_seen": len(self._seen_hashes),
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
        }
