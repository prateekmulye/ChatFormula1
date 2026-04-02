"""Metrics collection for observability and monitoring.

This module provides utilities for tracking application metrics including:
- Query latency
- API success rates
- Token usage and costs
- User satisfaction
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LatencyMetric:
    """Latency metric data."""

    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsageMetric:
    """Token usage and cost metric data."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    timestamp: datetime
    operation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserFeedbackMetric:
    """User satisfaction feedback metric."""

    session_id: str
    message_id: str
    rating: int  # 1 (thumbs down) or 5 (thumbs up)
    timestamp: datetime
    feedback_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Centralized metrics collector for application observability.

    This class collects and aggregates metrics in memory. In production,
    these metrics should be exported to a monitoring system like Prometheus,
    Datadog, or CloudWatch.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._lock = Lock()

        # Latency metrics
        self._latency_metrics: List[LatencyMetric] = []

        # Token usage metrics
        self._token_metrics: List[TokenUsageMetric] = []

        # User feedback metrics
        self._feedback_metrics: List[UserFeedbackMetric] = []

        # API call counters
        self._api_calls: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"success": 0, "failure": 0}
        )

        # Operation counters
        self._operation_counts: Dict[str, int] = defaultdict(int)

        logger.info("metrics_collector_initialized")

    def record_latency(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **metadata: Any,
    ) -> None:
        """Record a latency metric.

        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation succeeded
            **metadata: Additional metadata
        """
        metric = LatencyMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            success=success,
            metadata=metadata,
        )

        with self._lock:
            self._latency_metrics.append(metric)
            self._operation_counts[operation] += 1

        logger.debug(
            "latency_metric_recorded",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
        )

    def record_token_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        operation: str,
        **metadata: Any,
    ) -> None:
        """Record token usage and estimated cost.

        Args:
            model: Model name (e.g., "gpt-4-turbo")
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            operation: Operation name
            **metadata: Additional metadata
        """
        total_tokens = prompt_tokens + completion_tokens

        # Estimate cost based on model pricing (as of 2024)
        cost_per_1k_prompt = self._get_prompt_cost(model)
        cost_per_1k_completion = self._get_completion_cost(model)

        estimated_cost = (prompt_tokens / 1000) * cost_per_1k_prompt + (
            completion_tokens / 1000
        ) * cost_per_1k_completion

        metric = TokenUsageMetric(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            timestamp=datetime.utcnow(),
            operation=operation,
            metadata=metadata,
        )

        with self._lock:
            self._token_metrics.append(metric)

        logger.info(
            "token_usage_recorded",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=round(estimated_cost, 6),
            operation=operation,
        )

    def record_api_call(
        self,
        service: str,
        success: bool,
    ) -> None:
        """Record an API call result.

        Args:
            service: Service name (e.g., "openai", "pinecone", "tavily")
            success: Whether the call succeeded
        """
        status = "success" if success else "failure"

        with self._lock:
            self._api_calls[service][status] += 1

        logger.debug(
            "api_call_recorded",
            service=service,
            success=success,
        )

    def record_user_feedback(
        self,
        session_id: str,
        message_id: str,
        rating: int,
        feedback_text: Optional[str] = None,
        **metadata: Any,
    ) -> None:
        """Record user satisfaction feedback.

        Args:
            session_id: Session identifier
            message_id: Message identifier
            rating: Rating (1 for negative, 5 for positive)
            feedback_text: Optional feedback text
            **metadata: Additional metadata
        """
        if rating not in [1, 5]:
            logger.warning(
                "invalid_rating",
                rating=rating,
                message="Rating must be 1 or 5",
            )
            return

        metric = UserFeedbackMetric(
            session_id=session_id,
            message_id=message_id,
            rating=rating,
            timestamp=datetime.utcnow(),
            feedback_text=feedback_text,
            metadata=metadata,
        )

        with self._lock:
            self._feedback_metrics.append(metric)

        logger.info(
            "user_feedback_recorded",
            session_id=session_id,
            message_id=message_id,
            rating=rating,
            has_text=feedback_text is not None,
        )

    def get_latency_stats(
        self,
        operation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get latency statistics.

        Args:
            operation: Optional operation name to filter by

        Returns:
            Dictionary with latency statistics
        """
        with self._lock:
            metrics = self._latency_metrics

            if operation:
                metrics = [m for m in metrics if m.operation == operation]

            if not metrics:
                return {
                    "count": 0,
                    "operation": operation,
                }

            durations = [m.duration_ms for m in metrics]
            success_count = sum(1 for m in metrics if m.success)

            durations_sorted = sorted(durations)
            count = len(durations_sorted)

            return {
                "count": count,
                "operation": operation,
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
                "mean_ms": round(sum(durations) / count, 2),
                "p50_ms": round(durations_sorted[count // 2], 2),
                "p95_ms": round(durations_sorted[int(count * 0.95)], 2),
                "p99_ms": round(durations_sorted[int(count * 0.99)], 2),
                "success_rate": round(success_count / count, 4),
            }

    def get_token_usage_stats(self) -> Dict[str, Any]:
        """Get token usage and cost statistics.

        Returns:
            Dictionary with token usage statistics
        """
        with self._lock:
            if not self._token_metrics:
                return {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                }

            total_tokens = sum(m.total_tokens for m in self._token_metrics)
            total_cost = sum(m.estimated_cost_usd for m in self._token_metrics)

            # Group by model
            by_model: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "requests": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }
            )

            for metric in self._token_metrics:
                by_model[metric.model]["requests"] += 1
                by_model[metric.model]["total_tokens"] += metric.total_tokens
                by_model[metric.model]["cost_usd"] += metric.estimated_cost_usd

            return {
                "total_requests": len(self._token_metrics),
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "by_model": {
                    model: {
                        "requests": stats["requests"],
                        "total_tokens": stats["total_tokens"],
                        "cost_usd": round(stats["cost_usd"], 4),
                    }
                    for model, stats in by_model.items()
                },
            }

    def get_api_success_rates(self) -> Dict[str, Any]:
        """Get API call success rates.

        Returns:
            Dictionary with success rates by service
        """
        with self._lock:
            result = {}

            for service, counts in self._api_calls.items():
                total = counts["success"] + counts["failure"]
                success_rate = counts["success"] / total if total > 0 else 0.0

                result[service] = {
                    "total_calls": total,
                    "successful": counts["success"],
                    "failed": counts["failure"],
                    "success_rate": round(success_rate, 4),
                }

            return result

    def get_user_satisfaction_stats(self) -> Dict[str, Any]:
        """Get user satisfaction statistics.

        Returns:
            Dictionary with satisfaction statistics
        """
        with self._lock:
            if not self._feedback_metrics:
                return {
                    "total_feedback": 0,
                    "satisfaction_rate": 0.0,
                }

            positive = sum(1 for m in self._feedback_metrics if m.rating == 5)
            total = len(self._feedback_metrics)

            return {
                "total_feedback": total,
                "positive": positive,
                "negative": total - positive,
                "satisfaction_rate": round(positive / total, 4),
            }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in a single dictionary.

        Returns:
            Dictionary with all metrics
        """
        return {
            "latency": {
                "overall": self.get_latency_stats(),
                "by_operation": {
                    op: self.get_latency_stats(op)
                    for op in set(m.operation for m in self._latency_metrics)
                },
            },
            "token_usage": self.get_token_usage_stats(),
            "api_calls": self.get_api_success_rates(),
            "user_satisfaction": self.get_user_satisfaction_stats(),
            "operation_counts": dict(self._operation_counts),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics. Use with caution."""
        with self._lock:
            self._latency_metrics.clear()
            self._token_metrics.clear()
            self._feedback_metrics.clear()
            self._api_calls.clear()
            self._operation_counts.clear()

        logger.warning("metrics_reset", message="All metrics have been reset")

    @staticmethod
    def _get_prompt_cost(model: str) -> float:
        """Get prompt token cost per 1K tokens in USD.

        Args:
            model: Model name

        Returns:
            Cost per 1K prompt tokens
        """
        # Pricing as of 2024 (approximate)
        pricing = {
            "gpt-4-turbo": 0.01,
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0005,
            "gpt-3.5-turbo-16k": 0.003,
        }

        # Default to gpt-4-turbo pricing
        return pricing.get(model, 0.01)

    @staticmethod
    def _get_completion_cost(model: str) -> float:
        """Get completion token cost per 1K tokens in USD.

        Args:
            model: Model name

        Returns:
            Cost per 1K completion tokens
        """
        # Pricing as of 2024 (approximate)
        pricing = {
            "gpt-4-turbo": 0.03,
            "gpt-4": 0.06,
            "gpt-3.5-turbo": 0.0015,
            "gpt-3.5-turbo-16k": 0.004,
        }

        # Default to gpt-4-turbo pricing
        return pricing.get(model, 0.03)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()

    return _metrics_collector
