"""Structured logging configuration using structlog with JSON formatting."""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor

from .settings import Settings

# Context variables for request correlation
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries.

    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary

    Returns:
        EventDict: Updated event dictionary with app context
    """
    event_dict["app"] = "chatformula1"
    return event_dict


def add_correlation_ids(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add correlation IDs (request_id, session_id) to log entries.

    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary

    Returns:
        EventDict: Updated event dictionary with correlation IDs
    """
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id

    session_id = session_id_var.get()
    if session_id:
        event_dict["session_id"] = session_id

    return event_dict


def setup_logging(log_level: str) -> None:
    """Configure structured logging with JSON formatting."""
    settings = Settings()
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Define processors based on environment
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        add_correlation_ids,
        structlog.processors.StackInfoRenderer(),
    ]

    # Add exception formatting
    if settings.is_development:
        # Pretty console output for development
        processors.extend([structlog.dev.ConsoleRenderer(colors=True)])
    else:
        # JSON output for production
        processors.extend(
            [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context.

    Args:
        request_id: Unique request identifier
    """
    request_id_var.set(request_id)


def set_session_id(session_id: str) -> None:
    """Set the session ID for the current context.

    Args:
        session_id: Unique session identifier
    """
    session_id_var.set(session_id)


def clear_context() -> None:
    """Clear all context variables."""
    request_id_var.set(None)
    session_id_var.set(None)
