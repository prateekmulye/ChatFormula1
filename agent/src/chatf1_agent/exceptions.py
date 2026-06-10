"""Exception hierarchy for the agent service."""

from typing import Any


class ChatFormula1Error(Exception):
    """Base exception for all agent errors.

    Attributes:
        message: Human-readable error message
        details: Additional error details
        original_error: Original exception if this wraps another error
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
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


class VectorStoreError(ChatFormula1Error):
    """Raised on Pinecone vector store failures (connection, index, query)."""


class SearchAPIError(ChatFormula1Error):
    """Raised on Tavily Search API failures (connection, query, parsing)."""


class RateLimitError(ChatFormula1Error):
    """Raised when API rate limits are exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying
    """

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
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
