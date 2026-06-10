"""Structured logging configuration using structlog."""

import logging
import sys
from contextvars import ContextVar
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor

# Context variable for request correlation
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    event_dict["app"] = "chatf1-agent"
    return event_dict


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add the correlation request_id to log entries when set."""
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging(log_level: str, json_output: bool = True) -> None:
    """Configure structured logging.

    Args:
        log_level: Standard logging level name (e.g. "INFO").
        json_output: Emit JSON lines (production) instead of pretty console output.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        add_request_id,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        processors.extend(
            [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
        )
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

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
        name: Logger name (typically ``__name__``).

    Returns:
        BoundLogger: Configured logger instance.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def clear_request_id() -> None:
    """Clear the request ID for the current context."""
    request_id_var.set(None)
