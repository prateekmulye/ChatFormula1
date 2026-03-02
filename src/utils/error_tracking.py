"""Comprehensive error tracking, categorization, and alerting."""

import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from ..config.logging import get_logger
from ..exceptions import (AgentError, AuthenticationError, ChatFormula1Error,
                          ConfigurationError, DataIngestionError, LLMError,
                          RateLimitError, SearchAPIError, TimeoutError,
                          ValidationError, VectorStoreError)

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization and alerting."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK = "network"
    VALIDATION = "validation"
    DATA = "data"
    AGENT = "agent"
    LLM = "llm"
    VECTOR_STORE = "vector_store"
    SEARCH_API = "search_api"
    UNKNOWN = "unknown"


class ErrorMetrics:
    """Track error metrics for monitoring and alerting."""

    def __init__(self) -> None:
        """Initialize error metrics."""
        self._error_counts: dict[str, int] = defaultdict(int)
        self._error_by_category: dict[ErrorCategory, int] = defaultdict(int)
        self._error_by_severity: dict[ErrorSeverity, int] = defaultdict(int)
        self._recent_errors: list[dict[str, Any]] = []
        self._max_recent_errors = 100
        self._start_time = datetime.now()

    def record_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record an error occurrence.

        Args:
            error: The exception that occurred
            category: Error category
            severity: Error severity
            context: Additional context information
        """
        error_type = type(error).__name__
        self._error_counts[error_type] += 1
        self._error_by_category[category] += 1
        self._error_by_severity[severity] += 1

        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": str(error),
            "category": category.value,
            "severity": severity.value,
            "context": context or {},
        }

        self._recent_errors.append(error_record)

        # Keep only recent errors
        if len(self._recent_errors) > self._max_recent_errors:
            self._recent_errors = self._recent_errors[-self._max_recent_errors :]

    def get_error_count(self, error_type: Optional[str] = None) -> int:
        """Get total error count or count for specific error type.

        Args:
            error_type: Optional error type to filter by

        Returns:
            Error count
        """
        if error_type:
            return self._error_counts.get(error_type, 0)
        return sum(self._error_counts.values())

    def get_category_counts(self) -> dict[str, int]:
        """Get error counts by category.

        Returns:
            Dictionary of category to count
        """
        return {cat.value: count for cat, count in self._error_by_category.items()}

    def get_severity_counts(self) -> dict[str, int]:
        """Get error counts by severity.

        Returns:
            Dictionary of severity to count
        """
        return {sev.value: count for sev, count in self._error_by_severity.items()}

    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent error records.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent error records
        """
        return self._recent_errors[-limit:]

    def get_error_rate(self, window_minutes: int = 5) -> float:
        """Calculate error rate over time window.

        Args:
            window_minutes: Time window in minutes

        Returns:
            Errors per minute
        """
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [
            e
            for e in self._recent_errors
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
        return len(recent) / window_minutes if window_minutes > 0 else 0

    def reset(self) -> None:
        """Reset all metrics."""
        self._error_counts.clear()
        self._error_by_category.clear()
        self._error_by_severity.clear()
        self._recent_errors.clear()
        self._start_time = datetime.now()
        logger.info("error_metrics_reset")


# Global error metrics instance
_error_metrics = ErrorMetrics()


def get_error_metrics() -> ErrorMetrics:
    """Get global error metrics instance."""
    return _error_metrics


def categorize_error(error: Exception) -> ErrorCategory:
    """Categorize an error based on its type.

    Args:
        error: Exception to categorize

    Returns:
        Error category
    """
    error_type_map = {
        ConfigurationError: ErrorCategory.CONFIGURATION,
        AuthenticationError: ErrorCategory.AUTHENTICATION,
        RateLimitError: ErrorCategory.RATE_LIMIT,
        TimeoutError: ErrorCategory.TIMEOUT,
        ValidationError: ErrorCategory.VALIDATION,
        DataIngestionError: ErrorCategory.DATA,
        AgentError: ErrorCategory.AGENT,
        LLMError: ErrorCategory.LLM,
        VectorStoreError: ErrorCategory.VECTOR_STORE,
        SearchAPIError: ErrorCategory.SEARCH_API,
    }

    for error_type, category in error_type_map.items():
        if isinstance(error, error_type):
            return category

    # Check for common network errors
    if isinstance(error, (ConnectionError, OSError)):
        return ErrorCategory.NETWORK

    return ErrorCategory.UNKNOWN


def determine_severity(error: Exception, category: ErrorCategory) -> ErrorSeverity:
    """Determine error severity based on type and category.

    Args:
        error: Exception to evaluate
        category: Error category

    Returns:
        Error severity
    """
    # Critical errors that require immediate attention
    if isinstance(error, (ConfigurationError, AuthenticationError)):
        return ErrorSeverity.CRITICAL

    # High priority errors
    if category in (ErrorCategory.LLM, ErrorCategory.AGENT):
        return ErrorSeverity.ERROR

    # Medium priority errors
    if category in (ErrorCategory.RATE_LIMIT, ErrorCategory.TIMEOUT):
        return ErrorSeverity.WARNING

    # Lower priority errors
    if category in (ErrorCategory.VALIDATION, ErrorCategory.DATA):
        return ErrorSeverity.INFO

    # Default to error
    return ErrorSeverity.ERROR


def log_error_with_context(
    error: Exception,
    context: Optional[dict[str, Any]] = None,
    include_traceback: bool = True,
) -> None:
    """Log error with comprehensive context and categorization.

    Args:
        error: Exception to log
        context: Additional context information
        include_traceback: Whether to include full traceback
    """
    category = categorize_error(error)
    severity = determine_severity(error, category)

    # Build log context
    log_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "category": category.value,
        "severity": severity.value,
    }

    # Add custom context
    if context:
        log_context["context"] = context

    # Add details from ChatFormula1Error
    if isinstance(error, ChatFormula1Error):
        if error.details:
            log_context["error_details"] = error.details
        if error.original_error:
            log_context["original_error"] = {
                "type": type(error.original_error).__name__,
                "message": str(error.original_error),
            }

    # Add traceback if requested
    if include_traceback:
        log_context["traceback"] = traceback.format_exc()

    # Log based on severity
    if severity == ErrorSeverity.CRITICAL:
        logger.critical("error_occurred", **log_context)
    elif severity == ErrorSeverity.ERROR:
        logger.error("error_occurred", **log_context)
    elif severity == ErrorSeverity.WARNING:
        logger.warning("error_occurred", **log_context)
    else:
        logger.info("error_occurred", **log_context)

    # Record in metrics
    metrics = get_error_metrics()
    metrics.record_error(error, category, severity, context)

    # Check alert thresholds
    check_alert_thresholds(category, severity)


def check_alert_thresholds(category: ErrorCategory, severity: ErrorSeverity) -> None:
    """Check if error metrics exceed alert thresholds.

    Args:
        category: Error category
        severity: Error severity
    """
    metrics = get_error_metrics()

    # Critical error threshold: any critical error triggers alert
    if severity == ErrorSeverity.CRITICAL:
        logger.critical(
            "alert_critical_error",
            category=category.value,
            total_critical_errors=metrics.get_severity_counts().get("critical", 0),
        )

    # Error rate threshold: > 10 errors per minute
    error_rate = metrics.get_error_rate(window_minutes=5)
    if error_rate > 10:
        logger.error(
            "alert_high_error_rate",
            error_rate=error_rate,
            window_minutes=5,
            recent_errors=metrics.get_recent_errors(limit=5),
        )

    # Category-specific thresholds
    category_counts = metrics.get_category_counts()

    # Rate limit errors: > 5 in last 5 minutes
    if category == ErrorCategory.RATE_LIMIT:
        rate_limit_count = category_counts.get("rate_limit", 0)
        if rate_limit_count > 5:
            logger.warning(
                "alert_rate_limit_threshold",
                rate_limit_count=rate_limit_count,
                category=category.value,
            )

    # LLM errors: > 3 in last 5 minutes
    if category == ErrorCategory.LLM:
        llm_error_count = category_counts.get("llm", 0)
        if llm_error_count > 3:
            logger.error(
                "alert_llm_error_threshold",
                llm_error_count=llm_error_count,
                category=category.value,
            )

    # Vector store errors: > 3 in last 5 minutes
    if category == ErrorCategory.VECTOR_STORE:
        vector_error_count = category_counts.get("vector_store", 0)
        if vector_error_count > 3:
            logger.error(
                "alert_vector_store_threshold",
                vector_error_count=vector_error_count,
                category=category.value,
            )


def create_error_summary() -> dict[str, Any]:
    """Create summary of error metrics for monitoring.

    Returns:
        Dictionary containing error summary
    """
    metrics = get_error_metrics()

    return {
        "total_errors": metrics.get_error_count(),
        "error_rate_5min": metrics.get_error_rate(window_minutes=5),
        "by_category": metrics.get_category_counts(),
        "by_severity": metrics.get_severity_counts(),
        "recent_errors": metrics.get_recent_errors(limit=10),
        "timestamp": datetime.now().isoformat(),
    }


def log_error_summary() -> None:
    """Log current error summary for monitoring."""
    summary = create_error_summary()
    logger.info("error_summary", **summary)
