"""Base exception classes and error handling framework."""

from typing import Any, Optional


class ChatFormula1Error(Exception):
    """Base exception for all ChatFormula1 application errors.

    Attributes:
        message: Human-readable error message
        details: Additional error details
        original_error: Original exception if this wraps another error
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error details
            original_error: Original exception if wrapping another error
        """
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message

    def __repr__(self) -> str:
        """Return detailed representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"details={self.details!r}, "
            f"original_error={self.original_error!r})"
        )


class ConfigurationError(ChatFormula1Error):
    """Raised when there are configuration-related errors.

    Examples:
        - Missing required environment variables
        - Invalid configuration values
        - Configuration validation failures
    """

    pass


class VectorStoreError(ChatFormula1Error):
    """Raised when there are errors related to Pinecone vector store operations.

    Examples:
        - Connection failures
        - Index not found
        - Upsert/query failures
        - Embedding generation errors
    """

    pass


class SearchAPIError(ChatFormula1Error):
    """Raised when there are errors related to Tavily Search API.

    Examples:
        - API connection failures
        - Rate limit exceeded
        - Invalid search queries
        - Response parsing errors
    """

    pass


class LLMError(ChatFormula1Error):
    """Raised when there are errors related to OpenAI LLM operations.

    Examples:
        - API connection failures
        - Rate limit exceeded
        - Invalid prompts
        - Generation failures
        - Token limit exceeded
    """

    pass


class AgentError(ChatFormula1Error):
    """Raised when there are errors in LangGraph agent execution.

    Examples:
        - State machine errors
        - Tool execution failures
        - Invalid state transitions
        - Node execution errors
    """

    pass


class DataIngestionError(ChatFormula1Error):
    """Raised when there are errors during data ingestion pipeline.

    Examples:
        - Data loading failures
        - Document processing errors
        - Metadata extraction failures
        - Batch processing errors
    """

    pass


class ValidationError(ChatFormula1Error):
    """Raised when data validation fails.

    Examples:
        - Invalid input format
        - Schema validation failures
        - Type mismatches
        - Constraint violations
    """

    pass


class RateLimitError(ChatFormula1Error):
    """Raised when API rate limits are exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Human-readable error message
            retry_after: Seconds to wait before retrying
            details: Additional error details
            original_error: Original exception if wrapping another error
        """
        super().__init__(message, details, original_error)
        self.retry_after = retry_after


class TimeoutError(ChatFormula1Error):
    """Raised when operations exceed timeout limits.

    Examples:
        - API request timeouts
        - Database query timeouts
        - Long-running operations
    """

    pass


class AuthenticationError(ChatFormula1Error):
    """Raised when authentication fails.

    Examples:
        - Invalid API keys
        - Expired credentials
        - Unauthorized access
    """

    pass
