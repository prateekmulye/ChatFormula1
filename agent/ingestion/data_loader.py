"""Data loading infrastructure for CSV/JSON sources with validation."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.exceptions import ChatFormula1Error

logger = structlog.get_logger(__name__)


class DataLoadError(ChatFormula1Error):
    """Exception raised when data loading fails."""

    pass


class DataValidationError(ChatFormula1Error):
    """Exception raised when data validation fails."""

    pass


class F1DataSchema(BaseModel):
    """Base schema for F1 data validation."""

    source_file: Optional[str] = Field(None, description="Source file path")
    loaded_at: Optional[datetime] = Field(
        default_factory=datetime.now, description="Timestamp when data was loaded"
    )


class RaceResultSchema(F1DataSchema):
    """Schema for race result data from CSV."""

    race_id: str = Field(..., description="Unique race identifier")
    driver_id: str = Field(..., description="Driver identifier")
    constructor_id: str = Field(..., description="Constructor/team identifier")
    season: int = Field(..., ge=1950, le=2100, description="Season year")
    round: int = Field(..., ge=1, description="Round number")
    circuit_id: str = Field(..., description="Circuit identifier")
    quali_pos: Optional[int] = Field(None, description="Qualifying position")
    grid_pos: Optional[int] = Field(None, description="Grid position")
    finish_position: Optional[int] = Field(None, description="Finish position")
    points: Optional[float] = Field(None, ge=0, description="Points scored")
    points_scored: Optional[int] = Field(None, description="Points scored flag")
    podium_finish: Optional[int] = Field(None, description="Podium finish flag")
    top_10_finish: Optional[int] = Field(None, description="Top 10 finish flag")

    @field_validator("race_id", "driver_id", "constructor_id", "circuit_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Validate that IDs are not empty."""
        if not v or not v.strip():
            raise ValueError("ID fields cannot be empty")
        return v.strip().lower()


class DriverSchema(F1DataSchema):
    """Schema for driver data from JSON."""

    id: str = Field(..., description="Driver identifier")
    code: str = Field(..., description="Driver code (3 letters)")
    number: Optional[int] = Field(None, description="Driver number")
    name: str = Field(..., description="Driver full name")
    constructor: Optional[str] = Field(None, description="Current constructor")
    nationality: Optional[str] = Field(None, description="Driver nationality")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate driver code is 3 letters."""
        if len(v) != 3:
            raise ValueError("Driver code must be 3 letters")
        return v.upper()


class RaceSchema(F1DataSchema):
    """Schema for race data from JSON."""

    id: str = Field(..., description="Race identifier")
    name: str = Field(..., description="Race name")
    circuit: Optional[str] = Field(None, description="Circuit name")
    country: Optional[str] = Field(None, description="Country")
    date: Optional[str] = Field(None, description="Race date")
    season: Optional[int] = Field(None, description="Season year")
    round: Optional[int] = Field(None, description="Round number")


class DataLoader:
    """Load and validate F1 data from various file formats.

    Supports:
    - CSV files (race results, historical features)
    - JSON files (drivers, races, metadata)
    - Incremental loading with state tracking
    """

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        """Initialize DataLoader.

        Args:
            data_dir: Base directory for data files. Defaults to 'data/'
        """
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.logger = logger.bind(component="data_loader")
        self._load_state: Dict[str, datetime] = {}

        if not self.data_dir.exists():
            self.logger.warning("data_directory_not_found", data_dir=str(self.data_dir))

    def load_csv(
        self,
        file_path: Union[str, Path],
        schema: Optional[type[BaseModel]] = None,
        validate: bool = True,
        encoding: str = "utf-8",
    ) -> List[Dict[str, Any]]:
        """Load data from CSV file with optional validation.

        Args:
            file_path: Path to CSV file (relative to data_dir or absolute)
            schema: Optional Pydantic schema for validation
            validate: Whether to validate data against schema
            encoding: File encoding (default: utf-8)

        Returns:
            List of dictionaries containing row data

        Raises:
            DataLoadError: If file cannot be loaded
            DataValidationError: If validation fails
        """
        file_path = self._resolve_path(file_path)

        try:
            self.logger.info("loading_csv", file_path=str(file_path), validate=validate)

            data: List[Dict[str, Any]] = []

            with open(file_path, "r", encoding=encoding) as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(
                    reader, start=2
                ):  # Start at 2 (header is 1)
                    # Clean empty strings to None
                    cleaned_row = {k: (v if v != "" else None) for k, v in row.items()}

                    # Validate if schema provided
                    if validate and schema:
                        try:
                            validated = schema(
                                **cleaned_row, source_file=str(file_path)
                            )
                            data.append(validated.model_dump())
                        except ValidationError as e:
                            self.logger.error(
                                "row_validation_failed",
                                file_path=str(file_path),
                                row_num=row_num,
                                errors=e.errors(),
                            )
                            if validate:
                                raise DataValidationError(
                                    f"Validation failed at row {row_num}: {e}"
                                ) from e
                    else:
                        data.append(cleaned_row)

            self.logger.info(
                "csv_loaded", file_path=str(file_path), rows_loaded=len(data)
            )

            self._update_load_state(file_path)
            return data

        except FileNotFoundError as e:
            self.logger.error("csv_file_not_found", file_path=str(file_path))
            raise DataLoadError(f"CSV file not found: {file_path}") from e
        except csv.Error as e:
            self.logger.error("csv_parse_error", file_path=str(file_path), error=str(e))
            raise DataLoadError(f"Failed to parse CSV: {e}") from e
        except Exception as e:
            self.logger.error("csv_load_failed", file_path=str(file_path), error=str(e))
            raise DataLoadError(f"Failed to load CSV: {e}") from e

    def load_json(
        self,
        file_path: Union[str, Path],
        schema: Optional[type[BaseModel]] = None,
        validate: bool = True,
        encoding: str = "utf-8",
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Load data from JSON file with optional validation.

        Args:
            file_path: Path to JSON file (relative to data_dir or absolute)
            schema: Optional Pydantic schema for validation
            validate: Whether to validate data against schema
            encoding: File encoding (default: utf-8)

        Returns:
            Parsed JSON data (list or dict)

        Raises:
            DataLoadError: If file cannot be loaded
            DataValidationError: If validation fails
        """
        file_path = self._resolve_path(file_path)

        try:
            self.logger.info(
                "loading_json", file_path=str(file_path), validate=validate
            )

            with open(file_path, "r", encoding=encoding) as f:
                data = json.load(f)

            # Validate if schema provided
            if validate and schema:
                if isinstance(data, list):
                    validated_data = []
                    for idx, item in enumerate(data):
                        try:
                            validated = schema(**item, source_file=str(file_path))
                            validated_data.append(validated.model_dump())
                        except ValidationError as e:
                            self.logger.error(
                                "item_validation_failed",
                                file_path=str(file_path),
                                index=idx,
                                errors=e.errors(),
                            )
                            if validate:
                                raise DataValidationError(
                                    f"Validation failed at index {idx}: {e}"
                                ) from e
                    data = validated_data
                else:
                    try:
                        validated = schema(**data, source_file=str(file_path))
                        data = validated.model_dump()
                    except ValidationError as e:
                        self.logger.error(
                            "validation_failed",
                            file_path=str(file_path),
                            errors=e.errors(),
                        )
                        raise DataValidationError(f"Validation failed: {e}") from e

            self.logger.info(
                "json_loaded",
                file_path=str(file_path),
                items_loaded=len(data) if isinstance(data, list) else 1,
            )

            self._update_load_state(file_path)
            return data

        except FileNotFoundError as e:
            self.logger.error("json_file_not_found", file_path=str(file_path))
            raise DataLoadError(f"JSON file not found: {file_path}") from e
        except json.JSONDecodeError as e:
            self.logger.error(
                "json_parse_error", file_path=str(file_path), error=str(e)
            )
            raise DataLoadError(f"Failed to parse JSON: {e}") from e
        except Exception as e:
            self.logger.error(
                "json_load_failed", file_path=str(file_path), error=str(e)
            )
            raise DataLoadError(f"Failed to load JSON: {e}") from e

    def load_multiple(
        self,
        file_patterns: List[str],
        file_type: str = "auto",
        schema: Optional[type[BaseModel]] = None,
        validate: bool = True,
    ) -> Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        """Load multiple files matching patterns.

        Args:
            file_patterns: List of file patterns (supports glob patterns)
            file_type: File type ('csv', 'json', or 'auto' to detect from extension)
            schema: Optional Pydantic schema for validation
            validate: Whether to validate data

        Returns:
            Dictionary mapping file paths to loaded data

        Raises:
            DataLoadError: If any file fails to load
        """
        results: Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]] = {}

        for pattern in file_patterns:
            # Resolve pattern to actual files
            if "*" in pattern or "?" in pattern:
                files = list(self.data_dir.glob(pattern))
            else:
                files = [self._resolve_path(pattern)]

            for file_path in files:
                if not file_path.exists():
                    self.logger.warning("file_not_found", file_path=str(file_path))
                    continue

                # Detect file type
                detected_type = file_type
                if file_type == "auto":
                    detected_type = file_path.suffix.lower().lstrip(".")

                # Load based on type
                try:
                    if detected_type == "csv":
                        data = self.load_csv(file_path, schema, validate)
                    elif detected_type == "json":
                        data = self.load_json(file_path, schema, validate)
                    else:
                        self.logger.warning(
                            "unsupported_file_type",
                            file_path=str(file_path),
                            file_type=detected_type,
                        )
                        continue

                    results[str(file_path)] = data

                except (DataLoadError, DataValidationError) as e:
                    self.logger.error(
                        "file_load_failed", file_path=str(file_path), error=str(e)
                    )
                    # Continue with other files
                    continue

        self.logger.info(
            "multiple_files_loaded",
            files_loaded=len(results),
            total_patterns=len(file_patterns),
        )

        return results

    def needs_reload(self, file_path: Union[str, Path]) -> bool:
        """Check if file needs to be reloaded based on modification time.

        Args:
            file_path: Path to file

        Returns:
            True if file has been modified since last load
        """
        file_path = self._resolve_path(file_path)

        if not file_path.exists():
            return False

        if str(file_path) not in self._load_state:
            return True

        last_loaded = self._load_state[str(file_path)]
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

        return file_mtime > last_loaded

    def load_incremental(
        self,
        file_path: Union[str, Path],
        file_type: str = "auto",
        schema: Optional[type[BaseModel]] = None,
        validate: bool = True,
    ) -> Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]:
        """Load file only if it has been modified since last load.

        Args:
            file_path: Path to file
            file_type: File type ('csv', 'json', or 'auto')
            schema: Optional Pydantic schema for validation
            validate: Whether to validate data

        Returns:
            Loaded data if file was modified, None otherwise

        Raises:
            DataLoadError: If file loading fails
        """
        if not self.needs_reload(file_path):
            self.logger.debug("file_not_modified", file_path=str(file_path))
            return None

        file_path = self._resolve_path(file_path)

        # Detect file type
        detected_type = file_type
        if file_type == "auto":
            detected_type = file_path.suffix.lower().lstrip(".")

        # Load based on type
        if detected_type == "csv":
            return self.load_csv(file_path, schema, validate)
        elif detected_type == "json":
            return self.load_json(file_path, schema, validate)
        else:
            raise DataLoadError(f"Unsupported file type: {detected_type}")

    def _resolve_path(self, file_path: Union[str, Path]) -> Path:
        """Resolve file path relative to data directory.

        Args:
            file_path: File path (relative or absolute)

        Returns:
            Resolved Path object
        """
        path = Path(file_path)

        if path.is_absolute():
            return path

        return self.data_dir / path

    def _update_load_state(self, file_path: Path) -> None:
        """Update load state for a file.

        Args:
            file_path: Path to file
        """
        self._load_state[str(file_path)] = datetime.now()

    def get_load_state(self) -> Dict[str, datetime]:
        """Get current load state for all files.

        Returns:
            Dictionary mapping file paths to last load timestamps
        """
        return self._load_state.copy()

    def clear_load_state(self) -> None:
        """Clear load state, forcing all files to be reloaded."""
        self._load_state.clear()
        self.logger.info("load_state_cleared")
