"""Tests for configuration management."""

import pytest

from chatf1_agent.settings import Settings, get_settings


@pytest.mark.unit
def test_settings_loads_from_environment(test_settings: Settings):
    """Settings load correctly from environment variables."""
    assert test_settings.openai_api_key == "test-openai-key"
    assert test_settings.pinecone_api_key == "test-pinecone-key"
    assert test_settings.tavily_api_key == "test-tavily-key"
    assert test_settings.internal_api_token == "test-internal-token"
    assert test_settings.environment == "test"


@pytest.mark.unit
def test_settings_default_values(test_settings: Settings):
    """Defaults match the v2 architecture: gpt-4o-mini everywhere."""
    assert test_settings.generation_model == "gpt-4o-mini"
    assert test_settings.analysis_model == "gpt-4o-mini"
    assert test_settings.openai_embedding_model == "text-embedding-3-small"
    assert test_settings.pinecone_index_name == "f1-knowledge"
    assert test_settings.app_name == "ChatFormula1"
    assert test_settings.log_level == "DEBUG"
    assert test_settings.max_conversation_history == 10


@pytest.mark.unit
def test_settings_validation_constraints(test_settings: Settings):
    """Field constraints hold for the loaded settings."""
    assert 0.0 <= test_settings.openai_temperature <= 2.0
    assert 1 <= test_settings.tavily_max_results <= 10
    assert test_settings.max_conversation_history >= 1
    assert test_settings.vector_search_top_k >= 1


@pytest.mark.unit
def test_settings_work_without_api_keys(monkeypatch: pytest.MonkeyPatch):
    """Settings construct cleanly with no credentials at all."""
    for key in (
        "OPENAI_API_KEY",
        "PINECONE_API_KEY",
        "TAVILY_API_KEY",
        "INTERNAL_API_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    assert settings.openai_api_key == ""
    assert settings.generation_model == "gpt-4o-mini"


@pytest.mark.unit
def test_require_raises_for_missing_credentials(monkeypatch: pytest.MonkeyPatch):
    """require() rejects missing and placeholder credentials."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError, match="openai_api_key"):
        settings.require("openai_api_key")

    placeholder = Settings(_env_file=None, openai_api_key="your_openai_api_key_here")
    with pytest.raises(ValueError, match="openai_api_key"):
        placeholder.require("openai_api_key")


@pytest.mark.unit
def test_require_passes_for_set_credentials(test_settings: Settings):
    """require() is a no-op when credentials are present."""
    test_settings.require("openai_api_key", "pinecone_api_key", "tavily_api_key")


@pytest.mark.unit
def test_tavily_domain_list_parsing(monkeypatch: pytest.MonkeyPatch):
    """Domain lists parse from comma-separated and JSON env strings."""
    monkeypatch.setenv("TAVILY_INCLUDE_DOMAINS", "formula1.com,fia.com")
    settings = Settings(_env_file=None)
    assert settings.tavily_include_domains == ["formula1.com", "fia.com"]

    monkeypatch.setenv("TAVILY_INCLUDE_DOMAINS", '["autosport.com"]')
    settings = Settings(_env_file=None)
    assert settings.tavily_include_domains == ["autosport.com"]

    monkeypatch.setenv("TAVILY_INCLUDE_DOMAINS", "")
    settings = Settings(_env_file=None)
    assert settings.tavily_include_domains == []


@pytest.mark.unit
def test_get_settings_is_cached():
    """get_settings returns the same cached instance."""
    first = get_settings()
    second = get_settings()
    assert first is second
