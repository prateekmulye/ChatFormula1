"""Unit tests for data loading."""

import json
import tempfile
from pathlib import Path

import pytest

from src.ingestion.data_loader import (DataLoader, DataLoadError,
                                       DataValidationError, DriverSchema,
                                       RaceResultSchema, RaceSchema)


@pytest.mark.unit
class TestDataLoader:
    """Tests for DataLoader class."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_csv_file(self, temp_data_dir):
        """Create sample CSV file."""
        csv_path = temp_data_dir / "test_races.csv"
        csv_content = """race_id,driver_id,constructor_id,season,round,circuit_id,quali_pos,grid_pos,finish_position,points
2021_monaco,verstappen,red_bull,2021,5,monaco,1,1,1,25.0
2021_monaco,hamilton,mercedes,2021,5,monaco,2,2,2,18.0
"""
        csv_path.write_text(csv_content)
        return csv_path

    @pytest.fixture
    def sample_json_file(self, temp_data_dir):
        """Create sample JSON file."""
        json_path = temp_data_dir / "test_drivers.json"
        json_data = [
            {
                "id": "hamilton",
                "code": "HAM",
                "number": 44,
                "name": "Lewis Hamilton",
                "constructor": "Mercedes",
                "nationality": "British",
            },
            {
                "id": "verstappen",
                "code": "VER",
                "number": 1,
                "name": "Max Verstappen",
                "constructor": "Red Bull",
                "nationality": "Dutch",
            },
        ]
        json_path.write_text(json.dumps(json_data))
        return json_path

    def test_initialization(self, temp_data_dir):
        """Test loader initialization."""
        loader = DataLoader(temp_data_dir)

        assert loader.data_dir == temp_data_dir
        assert len(loader._load_state) == 0

    def test_initialization_default_dir(self):
        """Test loader with default directory."""
        loader = DataLoader()

        assert loader.data_dir == Path("data")

    def test_load_csv_basic(self, temp_data_dir, sample_csv_file):
        """Test basic CSV loading."""
        loader = DataLoader(temp_data_dir)

        data = loader.load_csv(sample_csv_file, validate=False)

        assert len(data) == 2
        assert data[0]["race_id"] == "2021_monaco"
        assert data[0]["driver_id"] == "verstappen"
        assert data[1]["driver_id"] == "hamilton"

    def test_load_csv_with_validation(self, temp_data_dir, sample_csv_file):
        """Test CSV loading with schema validation."""
        loader = DataLoader(temp_data_dir)

        data = loader.load_csv(sample_csv_file, schema=RaceResultSchema, validate=True)

        assert len(data) == 2
        assert data[0]["season"] == 2021
        assert data[0]["points"] == 25.0

    def test_load_csv_file_not_found(self, temp_data_dir):
        """Test CSV loading with non-existent file."""
        loader = DataLoader(temp_data_dir)

        with pytest.raises(DataLoadError) as exc_info:
            loader.load_csv("nonexistent.csv")

        assert "not found" in str(exc_info.value).lower()

    def test_load_json_basic(self, temp_data_dir, sample_json_file):
        """Test basic JSON loading."""
        loader = DataLoader(temp_data_dir)

        data = loader.load_json(sample_json_file, validate=False)

        assert len(data) == 2
        assert data[0]["id"] == "hamilton"
        assert data[1]["id"] == "verstappen"

    def test_load_json_with_validation(self, temp_data_dir, sample_json_file):
        """Test JSON loading with schema validation."""
        loader = DataLoader(temp_data_dir)

        data = loader.load_json(sample_json_file, schema=DriverSchema, validate=True)

        assert len(data) == 2
        assert data[0]["code"] == "HAM"
        assert data[1]["code"] == "VER"

    def test_load_json_file_not_found(self, temp_data_dir):
        """Test JSON loading with non-existent file."""
        loader = DataLoader(temp_data_dir)

        with pytest.raises(DataLoadError) as exc_info:
            loader.load_json("nonexistent.json")

        assert "not found" in str(exc_info.value).lower()

    def test_load_json_invalid_format(self, temp_data_dir):
        """Test JSON loading with invalid JSON."""
        loader = DataLoader(temp_data_dir)

        invalid_json = temp_data_dir / "invalid.json"
        invalid_json.write_text("{ invalid json }")

        with pytest.raises(DataLoadError) as exc_info:
            loader.load_json(invalid_json)

        assert "parse" in str(exc_info.value).lower()

    def test_load_state_tracking(self, temp_data_dir, sample_csv_file):
        """Test load state tracking."""
        loader = DataLoader(temp_data_dir)

        assert len(loader.get_load_state()) == 0

        loader.load_csv(sample_csv_file, validate=False)

        load_state = loader.get_load_state()
        assert len(load_state) == 1
        assert str(sample_csv_file) in load_state

    def test_needs_reload_new_file(self, temp_data_dir, sample_csv_file):
        """Test needs_reload for new file."""
        loader = DataLoader(temp_data_dir)

        assert loader.needs_reload(sample_csv_file) is True

    def test_needs_reload_after_load(self, temp_data_dir, sample_csv_file):
        """Test needs_reload after loading."""
        loader = DataLoader(temp_data_dir)

        loader.load_csv(sample_csv_file, validate=False)

        # Should not need reload immediately after loading
        assert loader.needs_reload(sample_csv_file) is False

    def test_load_incremental_new_file(self, temp_data_dir, sample_csv_file):
        """Test incremental loading of new file."""
        loader = DataLoader(temp_data_dir)

        data = loader.load_incremental(sample_csv_file, file_type="csv", validate=False)

        assert data is not None
        assert len(data) == 2

    def test_load_incremental_unchanged_file(self, temp_data_dir, sample_csv_file):
        """Test incremental loading of unchanged file."""
        loader = DataLoader(temp_data_dir)

        # Load once
        loader.load_csv(sample_csv_file, validate=False)

        # Try incremental load
        data = loader.load_incremental(sample_csv_file, file_type="csv", validate=False)

        # Should return None since file hasn't changed
        assert data is None

    def test_clear_load_state(self, temp_data_dir, sample_csv_file):
        """Test clearing load state."""
        loader = DataLoader(temp_data_dir)

        loader.load_csv(sample_csv_file, validate=False)
        assert len(loader.get_load_state()) == 1

        loader.clear_load_state()
        assert len(loader.get_load_state()) == 0

    def test_resolve_path_absolute(self, temp_data_dir):
        """Test path resolution with absolute path."""
        loader = DataLoader(temp_data_dir)

        absolute_path = Path("/tmp/test.csv")
        resolved = loader._resolve_path(absolute_path)

        assert resolved == absolute_path

    def test_resolve_path_relative(self, temp_data_dir):
        """Test path resolution with relative path."""
        loader = DataLoader(temp_data_dir)

        relative_path = "test.csv"
        resolved = loader._resolve_path(relative_path)

        assert resolved == temp_data_dir / "test.csv"


@pytest.mark.unit
class TestDataSchemas:
    """Tests for data validation schemas."""

    def test_race_result_schema_valid(self):
        """Test valid race result data."""
        data = {
            "race_id": "2021_monaco",
            "driver_id": "verstappen",
            "constructor_id": "red_bull",
            "season": 2021,
            "round": 5,
            "circuit_id": "monaco",
            "finish_position": 1,
            "points": 25.0,
        }

        result = RaceResultSchema(**data)

        assert result.race_id == "2021_monaco"
        assert result.season == 2021
        assert result.points == 25.0

    def test_race_result_schema_id_normalization(self):
        """Test ID normalization in race result schema."""
        data = {
            "race_id": "  2021_MONACO  ",
            "driver_id": "VERSTAPPEN",
            "constructor_id": "RED_BULL",
            "season": 2021,
            "round": 5,
            "circuit_id": "MONACO",
        }

        result = RaceResultSchema(**data)

        # IDs should be normalized to lowercase and trimmed
        assert result.race_id == "2021_monaco"
        assert result.driver_id == "verstappen"
        assert result.constructor_id == "red_bull"

    def test_race_result_schema_invalid_season(self):
        """Test race result with invalid season."""
        from pydantic import ValidationError

        data = {
            "race_id": "test",
            "driver_id": "test",
            "constructor_id": "test",
            "season": 1900,  # Too old
            "round": 1,
            "circuit_id": "test",
        }

        with pytest.raises(ValidationError):
            RaceResultSchema(**data)

    def test_driver_schema_valid(self):
        """Test valid driver data."""
        data = {
            "id": "hamilton",
            "code": "HAM",
            "number": 44,
            "name": "Lewis Hamilton",
            "constructor": "Mercedes",
            "nationality": "British",
        }

        driver = DriverSchema(**data)

        assert driver.id == "hamilton"
        assert driver.code == "HAM"
        assert driver.number == 44

    def test_driver_schema_code_validation(self):
        """Test driver code validation."""
        from pydantic import ValidationError

        data = {"id": "hamilton", "code": "HAMIL", "name": "Lewis Hamilton"}  # Too long

        with pytest.raises(ValidationError) as exc_info:
            DriverSchema(**data)

        assert "3 letters" in str(exc_info.value).lower()

    def test_driver_schema_code_uppercase(self):
        """Test driver code is converted to uppercase."""
        data = {"id": "hamilton", "code": "ham", "name": "Lewis Hamilton"}  # Lowercase

        driver = DriverSchema(**data)

        assert driver.code == "HAM"

    def test_race_schema_valid(self):
        """Test valid race data."""
        data = {
            "id": "monaco_2024",
            "name": "Monaco Grand Prix",
            "circuit": "Circuit de Monaco",
            "country": "Monaco",
            "date": "2024-05-26",
            "season": 2024,
            "round": 8,
        }

        race = RaceSchema(**data)

        assert race.id == "monaco_2024"
        assert race.name == "Monaco Grand Prix"
        assert race.season == 2024


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
