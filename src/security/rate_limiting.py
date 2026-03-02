"""Rate limiting for API endpoints.

This module provides rate limiting functionality to prevent abuse and ensure
fair usage of the API.
"""

import time
from collections import defaultdict
from typing import Optional

import structlog
from fastapi import HTTPException, Request, status

logger = structlog.get_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded. Please try again later.",
        retry_after: Optional[int] = None,
    ):
        """Initialize rate limit exception.

        Args:
            detail: Error message
            retry_after: Seconds until rate limit resets
        """
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        # Refill tokens based on time elapsed
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        self.last_refill = now

        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds until tokens are available
        """
        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """Rate limiter using token bucket algorithm."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: Optional[int] = None,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per client
            requests_per_hour: Maximum requests per hour per client
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size or requests_per_minute

        # Storage for token buckets per client
        # In production, use Redis for distributed rate limiting
        self.minute_buckets: dict[str, TokenBucket] = {}
        self.hour_buckets: dict[str, TokenBucket] = {}

        # Cleanup old buckets periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 3600  # 1 hour

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request.

        Args:
            request: FastAPI request

        Returns:
            Client identifier (IP address or user ID)
        """
        # Try to get user ID from request state (if authenticated)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _cleanup_old_buckets(self) -> None:
        """Clean up old token buckets to prevent memory leaks."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets that haven't been used in the last hour
        cutoff_time = now - 3600

        self.minute_buckets = {
            client_id: bucket
            for client_id, bucket in self.minute_buckets.items()
            if bucket.last_refill > cutoff_time
        }

        self.hour_buckets = {
            client_id: bucket
            for client_id, bucket in self.hour_buckets.items()
            if bucket.last_refill > cutoff_time
        }

        self.last_cleanup = now

        logger.debug(
            "rate_limiter_cleanup",
            minute_buckets=len(self.minute_buckets),
            hour_buckets=len(self.hour_buckets),
        )

    def check_rate_limit(self, request: Request, tokens: int = 1) -> None:
        """Check if request is within rate limits.

        Args:
            request: FastAPI request
            tokens: Number of tokens to consume (default 1)

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        client_id = self._get_client_id(request)

        # Cleanup old buckets periodically
        self._cleanup_old_buckets()

        # Get or create minute bucket
        if client_id not in self.minute_buckets:
            self.minute_buckets[client_id] = TokenBucket(
                capacity=self.burst_size,
                refill_rate=self.requests_per_minute / 60.0,  # tokens per second
            )

        # Get or create hour bucket
        if client_id not in self.hour_buckets:
            self.hour_buckets[client_id] = TokenBucket(
                capacity=self.requests_per_hour,
                refill_rate=self.requests_per_hour / 3600.0,  # tokens per second
            )

        minute_bucket = self.minute_buckets[client_id]
        hour_bucket = self.hour_buckets[client_id]

        # Check minute limit
        if not minute_bucket.consume(tokens):
            retry_after = int(minute_bucket.time_until_available(tokens)) + 1
            logger.warning(
                "rate_limit_exceeded_minute",
                client_id=client_id,
                retry_after=retry_after,
            )
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                retry_after=retry_after,
            )

        # Check hour limit
        if not hour_bucket.consume(tokens):
            retry_after = int(hour_bucket.time_until_available(tokens)) + 1
            logger.warning(
                "rate_limit_exceeded_hour",
                client_id=client_id,
                retry_after=retry_after,
            )
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded: {self.requests_per_hour} requests per hour",
                retry_after=retry_after,
            )

        logger.debug(
            "rate_limit_checked",
            client_id=client_id,
            tokens_consumed=tokens,
            minute_tokens_remaining=minute_bucket.tokens,
            hour_tokens_remaining=hour_bucket.tokens,
        )

    def get_rate_limit_info(self, request: Request) -> dict[str, any]:
        """Get rate limit information for a client.

        Args:
            request: FastAPI request

        Returns:
            Dictionary with rate limit information
        """
        client_id = self._get_client_id(request)

        info = {
            "client_id": client_id,
            "limits": {
                "requests_per_minute": self.requests_per_minute,
                "requests_per_hour": self.requests_per_hour,
                "burst_size": self.burst_size,
            },
            "remaining": {
                "minute": 0,
                "hour": 0,
            },
        }

        # Get remaining tokens
        if client_id in self.minute_buckets:
            minute_bucket = self.minute_buckets[client_id]
            # Refill tokens to get current count
            now = time.time()
            elapsed = now - minute_bucket.last_refill
            current_tokens = min(
                minute_bucket.capacity,
                minute_bucket.tokens + (elapsed * minute_bucket.refill_rate),
            )
            info["remaining"]["minute"] = int(current_tokens)
        else:
            info["remaining"]["minute"] = self.burst_size

        if client_id in self.hour_buckets:
            hour_bucket = self.hour_buckets[client_id]
            # Refill tokens to get current count
            now = time.time()
            elapsed = now - hour_bucket.last_refill
            current_tokens = min(
                hour_bucket.capacity,
                hour_bucket.tokens + (elapsed * hour_bucket.refill_rate),
            )
            info["remaining"]["hour"] = int(current_tokens)
        else:
            info["remaining"]["hour"] = self.requests_per_hour

        return info


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    burst_size: Optional[int] = None,
) -> RateLimiter:
    """Get or create global rate limiter instance.

    Args:
        requests_per_minute: Maximum requests per minute per client
        requests_per_hour: Maximum requests per hour per client
        burst_size: Maximum burst size

    Returns:
        RateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            burst_size=burst_size,
        )
        logger.info(
            "rate_limiter_initialized",
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            burst_size=burst_size or requests_per_minute,
        )

    return _rate_limiter
