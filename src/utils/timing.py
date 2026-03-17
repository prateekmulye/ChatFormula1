"""Performance timing utilities for observability."""

import time
from contextlib import contextmanager
from typing import Any, Generator, Optional

import structlog

logger = structlog.get_logger(__name__)


@contextmanager
def log_performance(
    operation: str,
    **extra_context: Any,
) -> Generator[None, None, None]:
    """Context manager for logging operation performance timing.

    Usage:
        with log_performance("vector_search", query="F1 standings"):
            results = await vector_store.search(query)

    Args:
        operation: Name of the operation being timed
        **extra_context: Additional context to include in logs

    Yields:
        None
    """
    start_time = time.time()

    logger.debug(
        "operation_started",
        operation=operation,
        **extra_context,
    )

    try:
        yield

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "operation_completed",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            **extra_context,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        logger.error(
            "operation_failed",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            error=str(e),
            **extra_context,
            exc_info=True,
        )
        raise


class PerformanceTimer:
    """Timer for tracking operation performance with multiple checkpoints.

    Usage:
        timer = PerformanceTimer("rag_pipeline")
        timer.checkpoint("query_analysis")
        # ... do work ...
        timer.checkpoint("vector_search")
        # ... do work ...
        timer.finish()
    """

    def __init__(self, operation: str, **context: Any):
        """Initialize performance timer.

        Args:
            operation: Name of the operation being timed
            **context: Additional context for logging
        """
        self.operation = operation
        self.context = context
        self.start_time = time.time()
        self.last_checkpoint = self.start_time
        self.checkpoints: list[dict[str, Any]] = []

        logger.debug(
            "timer_started",
            operation=operation,
            **context,
        )

    def checkpoint(self, name: str, **extra_context: Any) -> float:
        """Record a checkpoint with elapsed time since last checkpoint.

        Args:
            name: Name of the checkpoint
            **extra_context: Additional context for this checkpoint

        Returns:
            Duration in milliseconds since last checkpoint
        """
        current_time = time.time()
        duration_ms = (current_time - self.last_checkpoint) * 1000

        checkpoint_data = {
            "name": name,
            "duration_ms": round(duration_ms, 2),
            "total_elapsed_ms": round((current_time - self.start_time) * 1000, 2),
            **extra_context,
        }

        self.checkpoints.append(checkpoint_data)
        self.last_checkpoint = current_time

        logger.debug(
            "timer_checkpoint",
            operation=self.operation,
            checkpoint=name,
            duration_ms=round(duration_ms, 2),
            **self.context,
            **extra_context,
        )

        return duration_ms

    def finish(self, success: bool = True, **extra_context: Any) -> float:
        """Finish timing and log final results.

        Args:
            success: Whether the operation completed successfully
            **extra_context: Additional context for final log

        Returns:
            Total duration in milliseconds
        """
        total_duration_ms = (time.time() - self.start_time) * 1000

        log_method = logger.info if success else logger.error

        log_method(
            "timer_finished",
            operation=self.operation,
            total_duration_ms=round(total_duration_ms, 2),
            checkpoints=self.checkpoints,
            success=success,
            **self.context,
            **extra_context,
        )

        return total_duration_ms
