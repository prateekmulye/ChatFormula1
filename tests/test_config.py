"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.exceptions import ConfigurationError


@pytest.mark.unit
def test_settings_loads_from_environment(test_settings: Settings):
    """Test that settings load correctly from environment variables."""
    assert test_settings.openai_api_key == "test-openai-key"
    assert test_settings.pinecone_api_key == "test-pinecone-key"
    assert test_settings.tavily_api_key == "test-tavily-key"
    assert test_settings.environment == "development"


@pytest.mark.unit
def test_settings_default_values(test_settings: Settings):
    """Test that default values are set correctly."""
    assert test_settings.openai_model == "gpt-4-turbo"
    assert test_settings.openai_embedding_model == "text-embedding-3-small"
    assert test_settings.pinecone_index_name == "f1-knowledge"
    assert test_settings.app_name == "F1-Slipstream"
    assert test_settings.log_level == "DEBUG"
    assert test_settings.max_conversation_history == 10


@pytest.mark.unit
def test_settings_validation_constraints(test_settings: Settings):
    """Test that validation constraints work correctly."""
    assert 0.0 <= test_settings.openai_temperature <= 2.0
    assert 1 <= test_settings.tavily_max_results <= 10
    assert 1024 <= test_settings.api_port <= 65535
    assert test_settings.max_conversation_history >= 1


@pytest.mark.unit
def test_settings_environment_properties(test_settings: Settings):
    """Test environment property helpers."""
    assert test_settings.is_development is True
    assert test_settings.is_production is False


@pytest.mark.unit
def test_settings_rejects_invalid_api_keys():
    """Test that invalid API keys are rejected."""
    import os

    # Test with placeholder value
    os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"
    os.environ["PINECONE_API_KEY"] = "test-pinecone-key"
    os.environ["PINECONE_ENVIRONMENT"] = "test-environment"
    os.environ["TAVILY_API_KEY"] = "test-tavily-key"

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "openai_api_key" in str(exc_info.value).lower()
