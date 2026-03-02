"""Monitoring dashboard utilities for visualizing metrics.

This module provides utilities for creating monitoring dashboards
and visualizations of application metrics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from .metrics import get_metrics_collector

logger = structlog.get_logger(__name__)


class MonitoringDashboard:
    """Monitoring dashboard for visualizing application metrics.

    This class provides methods for generating dashboard data
    that can be consumed by frontend visualization libraries.
    """

    def __init__(self):
        """Initialize monitoring dashboard."""
        self.metrics_collector = get_metrics_collector()
        logger.info("monitoring_dashboard_initialized")

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get high-level dashboard summary.

        Returns:
            Dictionary with dashboard summary data
        """
        all_metrics = self.metrics_collector.get_all_metrics()

        # Calculate summary statistics
        latency_stats = all_metrics.get("latency", {}).get("overall", {})
        token_stats = all_metrics.get("token_usage", {})
        api_stats = all_metrics.get("api_calls", {})
        satisfaction_stats = all_metrics.get("user_satisfaction", {})

        # Calculate overall API success rate
        total_api_calls = 0
        total_api_success = 0
        for service_stats in api_stats.values():
            total_api_calls += service_stats.get("total_calls", 0)
            total_api_success += service_stats.get("successful", 0)

        overall_api_success_rate = (
            total_api_success / total_api_calls if total_api_calls > 0 else 0.0
        )

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": {
                "total_operations": sum(
                    all_metrics.get("operation_counts", {}).values()
                ),
                "avg_latency_ms": latency_stats.get("mean_ms", 0),
                "p95_latency_ms": latency_stats.get("p95_ms", 0),
                "api_success_rate": round(overall_api_success_rate, 4),
                "total_cost_usd": token_stats.get("total_cost_usd", 0),
                "user_satisfaction_rate": satisfaction_stats.get(
                    "satisfaction_rate", 0
                ),
            },
            "health_status": self._calculate_health_status(
                latency_stats,
                overall_api_success_rate,
                satisfaction_stats,
            ),
        }

        logger.debug("dashboard_summary_generated")

        return summary

    def get_latency_dashboard(self) -> Dict[str, Any]:
        """Get latency metrics dashboard data.

        Returns:
            Dictionary with latency dashboard data
        """
        all_metrics = self.metrics_collector.get_all_metrics()
        latency_data = all_metrics.get("latency", {})

        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall": latency_data.get("overall", {}),
            "by_operation": latency_data.get("by_operation", {}),
            "charts": {
                "percentiles": self._format_percentile_chart(
                    latency_data.get("overall", {})
                ),
                "by_operation": self._format_operation_comparison_chart(
                    latency_data.get("by_operation", {})
                ),
            },
        }

        logger.debug("latency_dashboard_generated")

        return dashboard

    def get_cost_dashboard(self) -> Dict[str, Any]:
        """Get cost tracking dashboard data.

        Returns:
            Dictionary with cost dashboard data
        """
        token_stats = self.metrics_collector.get_token_usage_stats()

        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_requests": token_stats.get("total_requests", 0),
                "total_tokens": token_stats.get("total_tokens", 0),
                "total_cost_usd": token_stats.get("total_cost_usd", 0),
            },
            "by_model": token_stats.get("by_model", {}),
            "charts": {
                "cost_by_model": self._format_cost_by_model_chart(
                    token_stats.get("by_model", {})
                ),
                "tokens_by_model": self._format_tokens_by_model_chart(
                    token_stats.get("by_model", {})
                ),
            },
            "projections": self._calculate_cost_projections(token_stats),
        }

        logger.debug("cost_dashboard_generated")

        return dashboard

    def get_api_health_dashboard(self) -> Dict[str, Any]:
        """Get API health dashboard data.

        Returns:
            Dictionary with API health dashboard data
        """
        api_stats = self.metrics_collector.get_api_success_rates()

        # Calculate health scores
        health_scores = {}
        for service, stats in api_stats.items():
            success_rate = stats.get("success_rate", 0)

            if success_rate >= 0.99:
                health = "excellent"
            elif success_rate >= 0.95:
                health = "good"
            elif success_rate >= 0.90:
                health = "fair"
            else:
                health = "poor"

            health_scores[service] = {
                "health": health,
                "success_rate": success_rate,
                "total_calls": stats.get("total_calls", 0),
            }

        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": api_stats,
            "health_scores": health_scores,
            "charts": {
                "success_rates": self._format_success_rate_chart(api_stats),
                "call_volume": self._format_call_volume_chart(api_stats),
            },
        }

        logger.debug("api_health_dashboard_generated")

        return dashboard

    def get_user_satisfaction_dashboard(self) -> Dict[str, Any]:
        """Get user satisfaction dashboard data.

        Returns:
            Dictionary with user satisfaction dashboard data
        """
        satisfaction_stats = self.metrics_collector.get_user_satisfaction_stats()

        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": satisfaction_stats,
            "charts": {
                "satisfaction_breakdown": self._format_satisfaction_chart(
                    satisfaction_stats
                ),
            },
            "insights": self._generate_satisfaction_insights(satisfaction_stats),
        }

        logger.debug("user_satisfaction_dashboard_generated")

        return dashboard

    def get_error_rate_dashboard(self) -> Dict[str, Any]:
        """Get error rate visualization dashboard data.

        Returns:
            Dictionary with error rate dashboard data
        """
        from .error_tracking import get_error_metrics

        error_metrics = get_error_metrics()
        error_summary = error_metrics.get_summary()

        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_errors": error_summary.get("total_errors", 0),
                "by_category": error_summary.get("by_category", {}),
                "by_severity": error_summary.get("by_severity", {}),
            },
            "recent_errors": error_summary.get("recent_errors", [])[:10],
            "charts": {
                "by_category": self._format_error_category_chart(
                    error_summary.get("by_category", {})
                ),
                "by_severity": self._format_error_severity_chart(
                    error_summary.get("by_severity", {})
                ),
            },
        }

        logger.debug("error_rate_dashboard_generated")

        return dashboard

    def _calculate_health_status(
        self,
        latency_stats: Dict[str, Any],
        api_success_rate: float,
        satisfaction_stats: Dict[str, Any],
    ) -> str:
        """Calculate overall health status.

        Args:
            latency_stats: Latency statistics
            api_success_rate: Overall API success rate
            satisfaction_stats: User satisfaction statistics

        Returns:
            Health status: "healthy", "degraded", or "unhealthy"
        """
        # Check latency (p95 should be under 3000ms)
        p95_latency = latency_stats.get("p95_ms", 0)
        latency_healthy = p95_latency < 3000

        # Check API success rate (should be above 95%)
        api_healthy = api_success_rate >= 0.95

        # Check user satisfaction (should be above 70%)
        satisfaction_rate = satisfaction_stats.get("satisfaction_rate", 0)
        satisfaction_healthy = satisfaction_rate >= 0.70

        # Determine overall health
        if latency_healthy and api_healthy and satisfaction_healthy:
            return "healthy"
        elif api_success_rate < 0.80 or p95_latency > 5000:
            return "unhealthy"
        else:
            return "degraded"

    def _format_percentile_chart(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format percentile data for charting.

        Args:
            stats: Latency statistics

        Returns:
            Chart data
        """
        if not stats or stats.get("count", 0) == 0:
            return {"labels": [], "values": []}

        return {
            "labels": ["Min", "P50", "P95", "P99", "Max"],
            "values": [
                stats.get("min_ms", 0),
                stats.get("p50_ms", 0),
                stats.get("p95_ms", 0),
                stats.get("p99_ms", 0),
                stats.get("max_ms", 0),
            ],
        }

    def _format_operation_comparison_chart(
        self, by_operation: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format operation comparison data for charting.

        Args:
            by_operation: Statistics by operation

        Returns:
            Chart data
        """
        operations = list(by_operation.keys())
        mean_values = [by_operation[op].get("mean_ms", 0) for op in operations]
        p95_values = [by_operation[op].get("p95_ms", 0) for op in operations]

        return {
            "operations": operations,
            "mean": mean_values,
            "p95": p95_values,
        }

    def _format_cost_by_model_chart(
        self, by_model: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format cost by model data for charting.

        Args:
            by_model: Statistics by model

        Returns:
            Chart data
        """
        models = list(by_model.keys())
        costs = [by_model[model].get("cost_usd", 0) for model in models]

        return {
            "labels": models,
            "values": costs,
        }

    def _format_tokens_by_model_chart(
        self, by_model: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format tokens by model data for charting.

        Args:
            by_model: Statistics by model

        Returns:
            Chart data
        """
        models = list(by_model.keys())
        tokens = [by_model[model].get("total_tokens", 0) for model in models]

        return {
            "labels": models,
            "values": tokens,
        }

    def _calculate_cost_projections(
        self, token_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate cost projections.

        Args:
            token_stats: Token usage statistics

        Returns:
            Cost projections
        """
        total_cost = token_stats.get("total_cost_usd", 0)
        total_requests = token_stats.get("total_requests", 0)

        if total_requests == 0:
            return {
                "cost_per_request": 0,
                "projected_daily": 0,
                "projected_monthly": 0,
            }

        cost_per_request = total_cost / total_requests

        # Assume 1000 requests per day (adjust based on actual usage)
        estimated_daily_requests = 1000

        return {
            "cost_per_request": round(cost_per_request, 6),
            "projected_daily": round(cost_per_request * estimated_daily_requests, 2),
            "projected_monthly": round(
                cost_per_request * estimated_daily_requests * 30, 2
            ),
        }

    def _format_success_rate_chart(
        self, api_stats: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format success rate data for charting.

        Args:
            api_stats: API statistics

        Returns:
            Chart data
        """
        services = list(api_stats.keys())
        success_rates = [
            api_stats[service].get("success_rate", 0) * 100 for service in services
        ]

        return {
            "labels": services,
            "values": success_rates,
        }

    def _format_call_volume_chart(
        self, api_stats: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format call volume data for charting.

        Args:
            api_stats: API statistics

        Returns:
            Chart data
        """
        services = list(api_stats.keys())
        successful = [api_stats[service].get("successful", 0) for service in services]
        failed = [api_stats[service].get("failed", 0) for service in services]

        return {
            "labels": services,
            "successful": successful,
            "failed": failed,
        }

    def _format_satisfaction_chart(
        self, satisfaction_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format satisfaction data for charting.

        Args:
            satisfaction_stats: Satisfaction statistics

        Returns:
            Chart data
        """
        return {
            "labels": ["Positive", "Negative"],
            "values": [
                satisfaction_stats.get("positive", 0),
                satisfaction_stats.get("negative", 0),
            ],
        }

    def _generate_satisfaction_insights(
        self, satisfaction_stats: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from satisfaction data.

        Args:
            satisfaction_stats: Satisfaction statistics

        Returns:
            List of insight strings
        """
        insights = []

        satisfaction_rate = satisfaction_stats.get("satisfaction_rate", 0)
        total_feedback = satisfaction_stats.get("total_feedback", 0)

        if total_feedback == 0:
            insights.append("No user feedback collected yet")
            return insights

        if satisfaction_rate >= 0.90:
            insights.append("Excellent user satisfaction! Keep up the great work.")
        elif satisfaction_rate >= 0.75:
            insights.append("Good user satisfaction, but there's room for improvement.")
        elif satisfaction_rate >= 0.60:
            insights.append(
                "User satisfaction is moderate. Consider investigating common issues."
            )
        else:
            insights.append("User satisfaction is low. Immediate attention needed.")

        if total_feedback < 10:
            insights.append(
                "Limited feedback data. Encourage more users to provide feedback."
            )

        return insights

    def _format_error_category_chart(
        self, by_category: Dict[str, int]
    ) -> Dict[str, Any]:
        """Format error category data for charting.

        Args:
            by_category: Error counts by category

        Returns:
            Chart data
        """
        categories = list(by_category.keys())
        counts = list(by_category.values())

        return {
            "labels": categories,
            "values": counts,
        }

    def _format_error_severity_chart(
        self, by_severity: Dict[str, int]
    ) -> Dict[str, Any]:
        """Format error severity data for charting.

        Args:
            by_severity: Error counts by severity

        Returns:
            Chart data
        """
        severities = list(by_severity.keys())
        counts = list(by_severity.values())

        return {
            "labels": severities,
            "values": counts,
        }


def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get monitoring dashboard instance.

    Returns:
        MonitoringDashboard instance
    """
    return MonitoringDashboard()
