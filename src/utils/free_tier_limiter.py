"""
Free Tier Rate Limiter for ChatFormula1
Ensures we stay within free tier limits for all services
"""

import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional


class FreeTierLimiter:
    """
    Rate limiter to stay within free tier limits

    Free Tier Limits:
    - OpenAI: 3 RPM, 200 RPD (requests per day)
    - Pinecone: 10 queries/sec (but we'll be conservative)
    - Tavily: 1000 searches/month (~33/day)
    - Overall: 3 requests/min per user, 100/day per user
    """

    def __init__(self):
        self.lock = threading.Lock()

        # User-level limits
        self.user_requests: Dict[str, list] = defaultdict(list)
        self.user_daily_requests: Dict[str, int] = defaultdict(int)
        self.user_daily_reset: Dict[str, datetime] = {}

        # Global service limits
        self.openai_requests: list = []
        self.openai_daily_count: int = 0
        self.openai_daily_reset: Optional[datetime] = None

        self.tavily_requests: list = []
        self.tavily_daily_count: int = 0
        self.tavily_daily_reset: Optional[datetime] = None

        self.pinecone_requests: list = []

        # Configuration
        self.USER_RPM = 3  # Requests per minute per user
        self.USER_RPD = 100  # Requests per day per user

        self.OPENAI_RPM = 3  # OpenAI free tier
        self.OPENAI_RPD = 150  # Conservative limit

        self.TAVILY_DAILY = 30  # Conservative (1000/month = ~33/day)

        self.PINECONE_RPS = 5  # Queries per second (conservative)

    def _clean_old_requests(self, requests: list, window_seconds: int) -> list:
        """Remove requests older than window"""
        cutoff = time.time() - window_seconds
        return [req for req in requests if req > cutoff]

    def _reset_daily_if_needed(self, user_id: str):
        """Reset daily counters if needed"""
        now = datetime.now()

        # Reset user daily counter
        if user_id in self.user_daily_reset:
            if now >= self.user_daily_reset[user_id]:
                self.user_daily_requests[user_id] = 0
                self.user_daily_reset[user_id] = now + timedelta(days=1)
        else:
            self.user_daily_reset[user_id] = now + timedelta(days=1)

        # Reset OpenAI daily counter
        if self.openai_daily_reset is None or now >= self.openai_daily_reset:
            self.openai_daily_count = 0
            self.openai_daily_reset = now + timedelta(days=1)

        # Reset Tavily daily counter
        if self.tavily_daily_reset is None or now >= self.tavily_daily_reset:
            self.tavily_daily_count = 0
            self.tavily_daily_reset = now + timedelta(days=1)

    def check_user_limit(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if user is within rate limits

        Returns:
            (allowed, error_message)
        """
        with self.lock:
            self._reset_daily_if_needed(user_id)

            now = time.time()

            # Clean old requests
            self.user_requests[user_id] = self._clean_old_requests(
                self.user_requests[user_id], 60
            )

            # Check per-minute limit
            if len(self.user_requests[user_id]) >= self.USER_RPM:
                wait_time = 60 - (now - self.user_requests[user_id][0])
                return (
                    False,
                    f"Rate limit exceeded. Please wait {int(wait_time)} seconds.",
                )

            # Check daily limit
            if self.user_daily_requests[user_id] >= self.USER_RPD:
                reset_time = self.user_daily_reset[user_id]
                hours_until_reset = (reset_time - datetime.now()).seconds // 3600
                return (
                    False,
                    f"Daily limit reached. Resets in {hours_until_reset} hours.",
                )

            # Record request
            self.user_requests[user_id].append(now)
            self.user_daily_requests[user_id] += 1

            return True, None

    def check_openai_limit(self) -> tuple[bool, Optional[str]]:
        """Check if OpenAI API call is allowed"""
        with self.lock:
            self._reset_daily_if_needed("system")

            now = time.time()

            # Clean old requests
            self.openai_requests = self._clean_old_requests(self.openai_requests, 60)

            # Check per-minute limit
            if len(self.openai_requests) >= self.OPENAI_RPM:
                wait_time = 60 - (now - self.openai_requests[0])
                return False, f"OpenAI rate limit. Wait {int(wait_time)}s."

            # Check daily limit
            if self.openai_daily_count >= self.OPENAI_RPD:
                return False, "OpenAI daily limit reached. Try again tomorrow."

            # Record request
            self.openai_requests.append(now)
            self.openai_daily_count += 1

            return True, None

    def check_tavily_limit(self) -> tuple[bool, Optional[str]]:
        """Check if Tavily search is allowed"""
        with self.lock:
            self._reset_daily_if_needed("system")

            # Check daily limit
            if self.tavily_daily_count >= self.TAVILY_DAILY:
                return False, "Daily search limit reached. Using cached data only."

            # Record request
            self.tavily_daily_count += 1

            return True, None

    def check_pinecone_limit(self) -> tuple[bool, Optional[str]]:
        """Check if Pinecone query is allowed"""
        with self.lock:
            now = time.time()

            # Clean old requests (1 second window)
            self.pinecone_requests = self._clean_old_requests(self.pinecone_requests, 1)

            # Check per-second limit
            if len(self.pinecone_requests) >= self.PINECONE_RPS:
                return False, "Vector search rate limit. Please wait."

            # Record request
            self.pinecone_requests.append(now)

            return True, None

    def get_usage_stats(self, user_id: str) -> dict:
        """Get current usage statistics"""
        with self.lock:
            self._reset_daily_if_needed(user_id)

            now = time.time()
            self.user_requests[user_id] = self._clean_old_requests(
                self.user_requests[user_id], 60
            )

            return {
                "user": {
                    "requests_this_minute": len(self.user_requests[user_id]),
                    "requests_today": self.user_daily_requests[user_id],
                    "minute_limit": self.USER_RPM,
                    "daily_limit": self.USER_RPD,
                    "minute_remaining": self.USER_RPM
                    - len(self.user_requests[user_id]),
                    "daily_remaining": self.USER_RPD
                    - self.user_daily_requests[user_id],
                },
                "openai": {
                    "requests_today": self.openai_daily_count,
                    "daily_limit": self.OPENAI_RPD,
                    "remaining": self.OPENAI_RPD - self.openai_daily_count,
                },
                "tavily": {
                    "searches_today": self.tavily_daily_count,
                    "daily_limit": self.TAVILY_DAILY,
                    "remaining": self.TAVILY_DAILY - self.tavily_daily_count,
                },
            }


# Global instance
_limiter: Optional[FreeTierLimiter] = None


def get_limiter() -> FreeTierLimiter:
    """Get or create global rate limiter instance"""
    global _limiter
    if _limiter is None:
        _limiter = FreeTierLimiter()
    return _limiter
