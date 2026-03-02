"""Retry utilities with exponential backoff and circuit breaker pattern."""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Type, TypeVar

from tenacity import (after_log, before_sleep_log, retry,
                      retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from ..config.logging import get_logger
from ..exceptions import RateLimitError, TimeoutError

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation for preventing cascading failures.

    The circuit breaker monitors failures and opens the circuit after a threshold
    is reached, preventing further calls to the failing service. After a timeout,
    it enters half-open state to test if the service has recovered.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to track for failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = CircuitState.CLOSED
        self._success_count = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return False
        return time.time() - self._last_failure_time >= self.recovery_timeout

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if we should attempt reset
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            logger.info(
                "circuit_breaker_half_open",
                function=func.__name__,
                failure_count=self._failure_count,
            )

        # Reject if circuit is open
        if self._state == CircuitState.OPEN:
            logger.warning(
                "circuit_breaker_open",
                function=func.__name__,
                failure_count=self._failure_count,
            )
            raise Exception(f"Circuit breaker is OPEN for {func.__name__}")

        try:
            result = func(*args, **kwargs)
            self._on_success(func.__name__)
            return result
        except self.expected_exception as e:
            self._on_failure(func.__name__, e)
            raise

    async def call_async(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if we should attempt reset
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            logger.info(
                "circuit_breaker_half_open",
                function=func.__name__,
                failure_count=self._failure_count,
            )

        # Reject if circuit is open
        if self._state == CircuitState.OPEN:
            logger.warning(
                "circuit_breaker_open",
                function=func.__name__,
                failure_count=self._failure_count,
            )
            raise Exception(f"Circuit breaker is OPEN for {func.__name__}")

        try:
            result = await func(*args, **kwargs)
            self._on_success(func.__name__)
            return result
        except self.expected_exception as e:
            self._on_failure(func.__name__, e)
            raise

    def _on_success(self, func_name: str) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= 2:  # Require 2 successes to close
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(
                    "circuit_breaker_closed",
                    function=func_name,
                )
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def _on_failure(self, func_name: str, error: Exception) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        logger.warning(
            "circuit_breaker_failure",
            function=func_name,
            failure_count=self._failure_count,
            error=str(error),
            error_type=type(error).__name__,
        )

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                "circuit_breaker_opened",
                function=func_name,
                failure_count=self._failure_count,
                recovery_timeout=self.recovery_timeout,
            )


# Global circuit breakers for different services
_circuit_breakers: dict[str, CircuitBreaker] = defaultdict(
    lambda: CircuitBreaker(failure_threshold=5, recovery_timeout=60)
)


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for a service.

    Args:
        service_name: Name of the service

    Returns:
        CircuitBreaker instance
    """
    return _circuit_breakers[service_name]


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: int = 2,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    service_name: str | None = None,
    use_circuit_breaker: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exception types to retry on
        service_name: Name of service for circuit breaker (if enabled)
        use_circuit_breaker: Whether to use circuit breaker pattern

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(
            max_attempts=3,
            exceptions=(ConnectionError,),
            service_name="tavily",
            use_circuit_breaker=True
        )
        async def fetch_data():
            # API call that might fail
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        circuit_breaker = None
        if use_circuit_breaker and service_name:
            circuit_breaker = get_circuit_breaker(service_name)

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_delay,
                max=max_delay,
                exp_base=exponential_base,
            ),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG),
            reraise=True,
        )
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            last_error = None

            while attempt < max_attempts:
                attempt += 1
                try:
                    logger.debug(
                        "retry_attempt_start",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                    )

                    if circuit_breaker:
                        result = await circuit_breaker.call_async(func, *args, **kwargs)
                    else:
                        result = await func(*args, **kwargs)

                    if attempt > 1:
                        logger.info(
                            "retry_success",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )

                    return result

                except exceptions as e:
                    last_error = e
                    logger.warning(
                        "retry_attempt_failed",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=str(e),
                        error_type=type(e).__name__,
                        will_retry=attempt < max_attempts,
                    )

                    if attempt >= max_attempts:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            total_attempts=attempt,
                            final_error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise

                    # Calculate backoff delay
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)), max_delay
                    )

                    logger.debug(
                        "retry_backoff",
                        function=func.__name__,
                        delay_seconds=delay,
                        next_attempt=attempt + 1,
                    )

                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_error:
                raise last_error
            raise Exception("Retry logic error")

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_delay,
                max=max_delay,
                exp_base=exponential_base,
            ),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG),
            reraise=True,
        )
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            last_error = None

            while attempt < max_attempts:
                attempt += 1
                try:
                    logger.debug(
                        "retry_attempt_start",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                    )

                    if circuit_breaker:
                        result = circuit_breaker.call(func, *args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    if attempt > 1:
                        logger.info(
                            "retry_success",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )

                    return result

                except exceptions as e:
                    last_error = e
                    logger.warning(
                        "retry_attempt_failed",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=str(e),
                        error_type=type(e).__name__,
                        will_retry=attempt < max_attempts,
                    )

                    if attempt >= max_attempts:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            total_attempts=attempt,
                            final_error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise

                    # Calculate backoff delay
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)), max_delay
                    )

                    logger.debug(
                        "retry_backoff",
                        function=func.__name__,
                        delay_seconds=delay,
                        next_attempt=attempt + 1,
                    )

                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_error:
                raise last_error
            raise Exception("Retry logic error")

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Service-specific retry configurations
OPENAI_RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2,
    "service_name": "openai",
    "use_circuit_breaker": True,
}

PINECONE_RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay": 0.5,
    "max_delay": 30.0,
    "exponential_base": 2,
    "service_name": "pinecone",
    "use_circuit_breaker": True,
}

TAVILY_RETRY_CONFIG = {
    "max_attempts": 2,
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "exponential_base": 2,
    "service_name": "tavily",
    "use_circuit_breaker": True,
}
