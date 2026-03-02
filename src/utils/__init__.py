"""Utility functions and helpers."""

from .dashboard import MonitoringDashboard, get_monitoring_dashboard
from .error_tracking import (ErrorCategory, ErrorMetrics, ErrorSeverity,
                             categorize_error, check_alert_thresholds,
                             create_error_summary, determine_severity,
                             get_error_metrics, log_error_summary,
                             log_error_with_context)
from .fallback import (FallbackChain, ResponseCache, ServiceMode,
                       get_degraded_mode_message, get_response_cache,
                       llm_generate_with_fallback, tavily_search_with_fallback,
                       vector_search_with_fallback)
from .metrics import (LatencyMetric, MetricsCollector, TokenUsageMetric,
                      UserFeedbackMetric, get_metrics_collector)
from .retry import (OPENAI_RETRY_CONFIG, PINECONE_RETRY_CONFIG,
                    TAVILY_RETRY_CONFIG, CircuitBreaker, CircuitState,
                    get_circuit_breaker, retry_with_backoff)
from .timing import PerformanceTimer, log_performance

__all__ = [
    # Retry utilities
    "retry_with_backoff",
    "CircuitBreaker",
    "CircuitState",
    "get_circuit_breaker",
    "OPENAI_RETRY_CONFIG",
    "PINECONE_RETRY_CONFIG",
    "TAVILY_RETRY_CONFIG",
    # Fallback utilities
    "FallbackChain",
    "ServiceMode",
    "ResponseCache",
    "get_response_cache",
    "tavily_search_with_fallback",
    "vector_search_with_fallback",
    "llm_generate_with_fallback",
    "get_degraded_mode_message",
    # Error tracking utilities
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorMetrics",
    "get_error_metrics",
    "categorize_error",
    "determine_severity",
    "log_error_with_context",
    "check_alert_thresholds",
    "create_error_summary",
    "log_error_summary",
    # Timing utilities
    "log_performance",
    "PerformanceTimer",
    # Metrics utilities
    "MetricsCollector",
    "LatencyMetric",
    "TokenUsageMetric",
    "UserFeedbackMetric",
    "get_metrics_collector",
    # Dashboard utilities
    "MonitoringDashboard",
    "get_monitoring_dashboard",
]
