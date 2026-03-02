"""Ingestion pipeline orchestration for F1 knowledge base."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog
from langchain_core.documents import Document

from src.config.settings import Settings, get_settings
from src.exceptions import ChatFormula1Error
from src.ingestion.data_loader import (
    DataLoader,
    DriverSchema,
    RaceResultSchema,
    RaceSchema,
)
from src.ingestion.document_processor import DocumentProcessor
from src.ingestion.metadata_enricher import MetadataEnricher
from src.vector_store.manager import VectorStoreManager

logger = structlog.get_logger(__name__)


class IngestionPipelineError(ChatFormula1Error):
    """Exception raised when ingestion pipeline fails."""

    pass


class IngestionPipeline:
    """Orchestrate end-to-end data ingestion workflow.

    Pipeline stages:
    1. Load data from sources (CSV/JSON)
    2. Process into documents with chunking
    3. Enrich metadata
    4. Embed and upsert to vector store

    Supports:
    - Full ingestion of all data
    - Incremental updates
    - Progress tracking and logging
    - Error recovery
    """

    def __init__(
        self,
        config: Optional[Settings] = None,
        data_dir: Optional[Union[str, Path]] = None,
    ):
        """Initialize IngestionPipeline.

        Args:
            config: Application settings (defaults to get_settings())
            data_dir: Base directory for data files (defaults to 'data/')
        """
        self.config = config or get_settings()
        self.logger = logger.bind(component="ingestion_pipeline")

        # Initialize components
        self.data_loader = DataLoader(data_dir)
        self.document_processor = DocumentProcessor(self.config)
        self.metadata_enricher = MetadataEnricher()
        self.vector_store: Optional[VectorStoreManager] = None

        # Track ingestion progress
        self._progress = {
            "total_files": 0,
            "files_processed": 0,
            "total_documents": 0,
            "documents_ingested": 0,
            "errors": [],
        }

        self.logger.info("ingestion_pipeline_initialized")

    async def initialize_vector_store(self) -> None:
        """Initialize vector store connection.

        Raises:
            IngestionPipelineError: If vector store initialization fails
        """
        try:
            self.vector_store = VectorStoreManager(self.config)
            await self.vector_store.initialize()
            self.logger.info("vector_store_initialized_for_ingestion")
        except Exception as e:
            self.logger.error("vector_store_init_failed", error=str(e))
            raise IngestionPipelineError(
                f"Failed to initialize vector store: {e}"
            ) from e

    async def ingest_all(
        self,
        race_results_file: Optional[str] = "historical_features.csv",
        drivers_file: Optional[str] = "drivers.json",
        races_file: Optional[str] = "races.json",
        batch_size: int = 100,
        show_progress: bool = True,
    ) -> Dict[str, Any]:
        """Ingest all F1 data sources into vector store.

        Args:
            race_results_file: Path to race results CSV file
            drivers_file: Path to drivers JSON file
            races_file: Path to races JSON file
            batch_size: Batch size for vector store ingestion
            show_progress: Whether to log progress

        Returns:
            Dictionary containing ingestion statistics

        Raises:
            IngestionPipelineError: If ingestion fails
        """
        self.logger.info(
            "starting_full_ingestion",
            race_results=race_results_file,
            drivers=drivers_file,
            races=races_file,
        )

        # Ensure vector store is initialized
        if self.vector_store is None:
            await self.initialize_vector_store()

        all_documents: List[Document] = []

        # Ingest race results
        if race_results_file:
            try:
                docs = await self._ingest_race_results(
                    race_results_file, show_progress=show_progress
                )
                all_documents.extend(docs)
                self._progress["files_processed"] += 1
            except Exception as e:
                error_msg = f"Failed to ingest race results: {e}"
                self.logger.error("race_results_ingestion_failed", error=str(e))
                self._progress["errors"].append(error_msg)

        # Ingest driver data
        if drivers_file:
            try:
                docs = await self._ingest_drivers(
                    drivers_file, show_progress=show_progress
                )
                all_documents.extend(docs)
                self._progress["files_processed"] += 1
            except Exception as e:
                error_msg = f"Failed to ingest drivers: {e}"
                self.logger.error("drivers_ingestion_failed", error=str(e))
                self._progress["errors"].append(error_msg)

        # Ingest race info
        if races_file:
            try:
                docs = await self._ingest_races(races_file, show_progress=show_progress)
                all_documents.extend(docs)
                self._progress["files_processed"] += 1
            except Exception as e:
                error_msg = f"Failed to ingest races: {e}"
                self.logger.error("races_ingestion_failed", error=str(e))
                self._progress["errors"].append(error_msg)

        # Upsert all documents to vector store
        if all_documents:
            try:
                self.logger.info(
                    "upserting_to_vector_store", total_documents=len(all_documents)
                )

                assert self.vector_store is not None
                ids = await self.vector_store.add_documents(
                    documents=all_documents,
                    batch_size=batch_size,
                    show_progress=show_progress,
                )

                self._progress["documents_ingested"] = len(ids)

                self.logger.info(
                    "vector_store_ingestion_complete", documents_ingested=len(ids)
                )

            except Exception as e:
                error_msg = f"Failed to upsert to vector store: {e}"
                self.logger.error("vector_store_upsert_failed", error=str(e))
                self._progress["errors"].append(error_msg)
                raise IngestionPipelineError(error_msg) from e

        # Get final statistics
        stats = self.get_stats()

        self.logger.info("full_ingestion_complete", stats=stats)

        return stats

    async def ingest_from_source(
        self,
        source_path: str,
        source_type: str = "auto",
        batch_size: int = 100,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Ingest data from a specific source file or directory.

        Args:
            source_path: Path to data source file or directory
            source_type: Source type ('csv', 'json', 'text', or 'auto')
            batch_size: Batch size for vector store ingestion
            overwrite: Whether to overwrite existing data

        Returns:
            Dictionary containing ingestion statistics

        Raises:
            IngestionPipelineError: If ingestion fails
        """
        self.logger.info(
            "starting_source_ingestion",
            source_path=source_path,
            source_type=source_type,
            overwrite=overwrite,
        )

        # Ensure vector store is initialized
        if self.vector_store is None:
            await self.initialize_vector_store()

        path = Path(source_path)

        # Auto-detect source type if needed
        if source_type == "auto":
            if path.suffix == ".csv":
                source_type = "csv"
            elif path.suffix == ".json":
                source_type = "json"
            else:
                source_type = "text"

        all_documents: List[Document] = []

        try:
            # Process based on source type and file name
            if source_type == "csv" or "historical_features" in path.name:
                docs = await self._ingest_race_results(source_path)
            elif "driver" in path.name.lower():
                docs = await self._ingest_drivers(source_path)
            elif "race" in path.name.lower():
                docs = await self._ingest_races(source_path)
            else:
                # Generic text ingestion
                self.logger.info("ingesting_generic_text", source_path=source_path)
                # For now, just log - could implement generic text loading
                raise IngestionPipelineError(
                    f"Unsupported file type or name pattern: {source_path}"
                )

            all_documents.extend(docs)
            self._progress["files_processed"] += 1

        except Exception as e:
            error_msg = f"Failed to ingest {source_path}: {e}"
            self.logger.error("source_ingestion_failed", error=str(e))
            self._progress["errors"].append(error_msg)
            raise IngestionPipelineError(error_msg) from e

        # Upsert documents to vector store
        if all_documents:
            try:
                assert self.vector_store is not None
                ids = await self.vector_store.add_documents(
                    documents=all_documents,
                    batch_size=batch_size,
                    show_progress=True,
                )

                self._progress["documents_ingested"] = len(ids)

                self.logger.info(
                    "source_ingestion_complete",
                    documents_ingested=len(ids),
                )

            except Exception as e:
                error_msg = f"Failed to upsert to vector store: {e}"
                self.logger.error("vector_store_upsert_failed", error=str(e))
                self._progress["errors"].append(error_msg)
                raise IngestionPipelineError(error_msg) from e

        return self.get_stats()

    async def ingest_incremental(
        self,
        file_paths: List[str],
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """Ingest only files that have been modified since last load.

        Args:
            file_paths: List of file paths to check for updates
            batch_size: Batch size for vector store ingestion

        Returns:
            Dictionary containing ingestion statistics

        Raises:
            IngestionPipelineError: If ingestion fails
        """
        self.logger.info(
            "starting_incremental_ingestion", files_to_check=len(file_paths)
        )

        # Ensure vector store is initialized
        if self.vector_store is None:
            await self.initialize_vector_store()

        all_documents: List[Document] = []
        files_updated = 0

        for file_path in file_paths:
            # Check if file needs reload
            if not self.data_loader.needs_reload(file_path):
                self.logger.debug("file_not_modified", file_path=file_path)
                continue

            files_updated += 1

            # Determine file type and ingest
            path = Path(file_path)

            try:
                if "historical_features" in path.name or "race" in path.name.lower():
                    if path.suffix == ".csv":
                        docs = await self._ingest_race_results(file_path)
                    else:
                        docs = await self._ingest_races(file_path)
                elif "driver" in path.name.lower():
                    docs = await self._ingest_drivers(file_path)
                else:
                    self.logger.warning("unknown_file_type", file_path=file_path)
                    continue

                all_documents.extend(docs)
                self._progress["files_processed"] += 1

            except Exception as e:
                error_msg = f"Failed to ingest {file_path}: {e}"
                self.logger.error(
                    "file_ingestion_failed", file_path=file_path, error=str(e)
                )
                self._progress["errors"].append(error_msg)
                continue

        # Upsert updated documents
        if all_documents:
            try:
                assert self.vector_store is not None
                ids = await self.vector_store.add_documents(
                    documents=all_documents,
                    batch_size=batch_size,
                    show_progress=True,
                )

                self._progress["documents_ingested"] = len(ids)

            except Exception as e:
                error_msg = f"Failed to upsert to vector store: {e}"
                self.logger.error("vector_store_upsert_failed", error=str(e))
                self._progress["errors"].append(error_msg)
                raise IngestionPipelineError(error_msg) from e

        stats = self.get_stats()
        stats["files_updated"] = files_updated

        self.logger.info("incremental_ingestion_complete", stats=stats)

        return stats

    async def _ingest_race_results(
        self,
        file_path: str,
        show_progress: bool = True,
    ) -> List[Document]:
        """Ingest race results from CSV file.

        Args:
            file_path: Path to race results CSV file
            show_progress: Whether to log progress

        Returns:
            List of processed documents
        """
        if show_progress:
            self.logger.info("ingesting_race_results", file_path=file_path)

        # Load data
        race_data = self.data_loader.load_csv(
            file_path,
            schema=RaceResultSchema,
            validate=False,  # Flexible validation for historical data
        )

        if show_progress:
            self.logger.info("race_data_loaded", records=len(race_data))

        # Process into documents
        documents = self.document_processor.process_race_results(
            race_data,
            chunk=True,
        )

        # Enrich metadata
        documents = self.metadata_enricher.enrich_documents(documents)

        self._progress["total_documents"] += len(documents)

        if show_progress:
            self.logger.info("race_results_processed", documents=len(documents))

        return documents

    async def _ingest_drivers(
        self,
        file_path: str,
        show_progress: bool = True,
    ) -> List[Document]:
        """Ingest driver data from JSON file.

        Args:
            file_path: Path to drivers JSON file
            show_progress: Whether to log progress

        Returns:
            List of processed documents
        """
        if show_progress:
            self.logger.info("ingesting_drivers", file_path=file_path)

        # Load data
        driver_data = self.data_loader.load_json(
            file_path,
            schema=DriverSchema,
            validate=False,  # Flexible validation
        )

        # Ensure it's a list
        if not isinstance(driver_data, list):
            driver_data = [driver_data]

        if show_progress:
            self.logger.info("driver_data_loaded", drivers=len(driver_data))

        # Process into documents
        documents = self.document_processor.process_driver_data(driver_data)

        # Enrich metadata
        documents = self.metadata_enricher.enrich_documents(documents)

        self._progress["total_documents"] += len(documents)

        if show_progress:
            self.logger.info("drivers_processed", documents=len(documents))

        return documents

    async def _ingest_races(
        self,
        file_path: str,
        show_progress: bool = True,
    ) -> List[Document]:
        """Ingest race information from JSON file.

        Args:
            file_path: Path to races JSON file
            show_progress: Whether to log progress

        Returns:
            List of processed documents
        """
        if show_progress:
            self.logger.info("ingesting_races", file_path=file_path)

        # Load data
        race_data = self.data_loader.load_json(
            file_path,
            schema=RaceSchema,
            validate=False,  # Flexible validation
        )

        # Ensure it's a list
        if not isinstance(race_data, list):
            race_data = [race_data]

        if show_progress:
            self.logger.info("race_data_loaded", races=len(race_data))

        # Process into documents
        documents = self.document_processor.process_race_info(race_data)

        # Enrich metadata
        documents = self.metadata_enricher.enrich_documents(documents)

        self._progress["total_documents"] += len(documents)

        if show_progress:
            self.logger.info("races_processed", documents=len(documents))

        return documents

    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion pipeline statistics.

        Returns:
            Dictionary containing pipeline stats
        """
        stats = self._progress.copy()

        # Add component stats
        stats["processor_stats"] = self.document_processor.get_stats()
        stats["enricher_stats"] = self.metadata_enricher.get_stats()
        stats["loader_state"] = self.data_loader.get_load_state()

        return stats

    def reset_progress(self) -> None:
        """Reset progress tracking."""
        self._progress = {
            "total_files": 0,
            "files_processed": 0,
            "total_documents": 0,
            "documents_ingested": 0,
            "errors": [],
        }
        self.logger.info("progress_reset")

    async def close(self) -> None:
        """Clean up resources."""
        if self.vector_store:
            await self.vector_store.close()
        self.logger.info("ingestion_pipeline_closed")
