"""Tests for exception classes."""

import pytest

from src.exceptions import (AgentError, ChatFormula1Error, ConfigurationError,
                            LLMError, RateLimitError, SearchAPIError,
                            VectorStoreError)


@pytest.mark.unit
def test_base_exception_creation():
    """Test base exception can be created with message."""
    error = ChatFormula1Error("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.details == {}
    assert error.original_error is None


@pytest.mark.unit
def test_exception_with_original_error():
    """Test exception wrapping another exception."""
    original = ValueError("Original error")
    error = ChatFormula1Error("Wrapped error", original_error=original)
    assert error.original_error is original
    assert isinstance(error.original_error, ValueError)


@pytest.mark.unit
def test_configuration_error():
    """Test ConfigurationError subclass."""
    error = ConfigurationError("Config error")
    assert isinstance(error, ChatFormula1Error)
    assert str(error) == "Config error"


@pytest.mark.unit
def test_vector_store_error():
    """Test VectorStoreError subclass."""
    error = VectorStoreError("Vector store error")
    assert isinstance(error, ChatFormula1Error)


@pytest.mark.unit
def test_search_api_error():
    """Test SearchAPIError subclass."""
    error = SearchAPIError("Search API error")
    assert isinstance(error, ChatFormula1Error)


@pytest.mark.unit
def test_llm_error():
    """Test LLMError subclass."""
    error = LLMError("LLM error")
    assert isinstance(error, ChatFormula1Error)


@pytest.mark.unit
def test_agent_error():
    """Test AgentError subclass."""
    error = AgentError("Agent error")
    assert isinstance(error, ChatFormula1Error)


@pytest.mark.unit
def test_rate_limit_error_with_retry_after():
    """Test RateLimitError with retry_after attribute."""
    error = RateLimitError("Rate limit exceeded", retry_after=60)
    assert isinstance(error, ChatFormula1Error)
    assert error.retry_after == 60
