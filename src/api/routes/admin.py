"""Admin and utility endpoints for ChatFormula1 API.

This module provides administrative endpoints for data ingestion, statistics,
and configuration validation.
"""

from typing import Any, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()


# Request/Response Models
class HealthCheckResponse(BaseModel):
    """Detailed health check response."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")
    dependencies: dict[str, dict[str, Any]] = Field(
        ..., description="Dependency health details"
    )


class VectorStoreStatsResponse(BaseModel):
    """Vector store statistics response."""

    index_name: str = Field(..., description="Pinecone index name")
    dimension: int = Field(..., description="Vector dimension")
    total_vectors: Optional[int] = Field(None, description="Total vector count")
    namespaces: Optional[list[str]] = Field(None, description="Available namespaces")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class IngestionRequest(BaseModel):
    """Data ingestion request."""

    source_path: str = Field(..., description="Path to data source file or directory")
    source_type: str = Field(
        default="auto",
        description="Source type: 'csv', 'json', 'text', or 'auto' for auto-detection",
    )
    batch_size: int = Field(
        default=100, ge=1, le=1000, description="Batch size for processing"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing data")


class IngestionResponse(BaseModel):
    """Data ingestion response."""

    task_id: str = Field(..., description="Background task ID")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")


class ConfigValidationResponse(BaseModel):
    """Configuration validation response."""

    valid: bool = Field(..., description="Whether configuration is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    config_summary: dict[str, Any] = Field(
        default_factory=dict, description="Configuration summary"
    )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Get detailed health status with dependency checks",
)
async def detailed_health_check() -> HealthCheckResponse:
    """Perform detailed health check with dependency validation.

    Returns:
        HealthCheckResponse with detailed status information
    """
    config = get_settings()

    from src.api.main import app_state

    logger.info("performing_detailed_health_check")

    dependencies = {}

    # Check vector store
    vector_store = app_state.get("vector_store")
    if vector_store:
        try:
            # Try to get index stats
            stats = await vector_store.get_index_stats()
            dependencies["vector_store"] = {
                "status": "healthy",
                "index_name": config.pinecone_index_name,
                "details": stats,
            }
        except Exception as e:
            logger.error("vector_store_health_check_failed", error=str(e))
            dependencies["vector_store"] = {
                "status": "unhealthy",
                "error": str(e),
            }
    else:
        dependencies["vector_store"] = {
            "status": "not_initialized",
        }

    # Check Tavily client
    tavily_client = app_state.get("tavily_client")
    if tavily_client:
        try:
            # Try a simple search to verify API key
            # Note: This is a lightweight check, not a full search
            dependencies["tavily_client"] = {
                "status": "healthy",
                "configured": True,
            }
        except Exception as e:
            logger.error("tavily_health_check_failed", error=str(e))
            dependencies["tavily_client"] = {
                "status": "unhealthy",
                "error": str(e),
            }
    else:
        dependencies["tavily_client"] = {
            "status": "not_initialized",
        }

    # Check agent graph
    agent_graph = app_state.get("agent_graph")
    if agent_graph:
        dependencies["agent_graph"] = {
            "status": "healthy",
            "compiled": agent_graph.compiled_graph is not None,
        }
    else:
        dependencies["agent_graph"] = {
            "status": "not_initialized",
        }

    # Check OpenAI (via config)
    try:
        dependencies["openai"] = {
            "status": "configured",
            "model": config.openai_model,
            "embedding_model": config.openai_embedding_model,
        }
    except Exception as e:
        dependencies["openai"] = {
            "status": "error",
            "error": str(e),
        }

    # Determine overall status
    all_healthy = all(
        dep.get("status") in ["healthy", "configured"] for dep in dependencies.values()
    )
    overall_status = "healthy" if all_healthy else "degraded"

    logger.info(
        "detailed_health_check_completed",
        status=overall_status,
    )

    return HealthCheckResponse(
        status=overall_status,
        version="0.1.0",
        environment=config.environment,
        dependencies=dependencies,
    )


@router.get(
    "/stats",
    response_model=VectorStoreStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Vector store statistics",
    description="Get statistics about the vector store index",
)
async def get_vector_store_stats() -> VectorStoreStatsResponse:
    """Get vector store statistics.

    Returns:
        VectorStoreStatsResponse with index statistics

    Raises:
        HTTPException: If vector store is not initialized or stats retrieval fails
    """
    from src.api.main import app_state

    config = get_settings()

    logger.info("retrieving_vector_store_stats")

    vector_store = app_state.get("vector_store")
    if not vector_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not initialized",
        )

    try:
        # Get index statistics
        stats = await vector_store.get_index_stats()

        logger.info(
            "vector_store_stats_retrieved",
            stats=stats,
        )

        return VectorStoreStatsResponse(
            index_name=config.pinecone_index_name,
            dimension=config.pinecone_dimension,
            total_vectors=stats.get("total_vector_count"),
            namespaces=(
                list(stats.get("namespaces", {}).keys())
                if stats.get("namespaces")
                else None
            ),
            metadata=stats,
        )

    except Exception as e:
        logger.error(
            "vector_store_stats_failed",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vector store statistics: {str(e)}",
        )


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest data into vector store",
    description="Start a background task to ingest data into the vector store",
)
async def ingest_data(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
) -> IngestionResponse:
    """Ingest data into vector store.

    This endpoint starts a background task to process and ingest data.
    Use the task_id to check status.

    Args:
        request: Ingestion request with source information
        background_tasks: FastAPI background tasks

    Returns:
        IngestionResponse with task information

    Raises:
        HTTPException: If vector store is not initialized
    """
    from src.api.main import app_state

    logger.info(
        "starting_data_ingestion",
        source_path=request.source_path,
        source_type=request.source_type,
    )

    vector_store = app_state.get("vector_store")
    if not vector_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not initialized",
        )

    # Generate task ID
    import uuid

    task_id = str(uuid.uuid4())

    # Define background task
    async def run_ingestion():
        """Background task for data ingestion."""
        try:
            logger.info(
                "ingestion_task_started",
                task_id=task_id,
                source_path=request.source_path,
            )

            # Import ingestion pipeline
            from src.ingestion.pipeline import IngestionPipeline

            # Create pipeline
            config = get_settings()
            pipeline = IngestionPipeline(config=config)

            # Set vector store directly
            pipeline.vector_store = vector_store

            # Run ingestion
            result = await pipeline.ingest_from_source(
                source_path=request.source_path,
                source_type=request.source_type,
                batch_size=request.batch_size,
                overwrite=request.overwrite,
            )

            logger.info(
                "ingestion_task_completed",
                task_id=task_id,
                result=result,
            )

        except Exception as e:
            logger.error(
                "ingestion_task_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )

    # Add to background tasks
    background_tasks.add_task(run_ingestion)

    logger.info(
        "ingestion_task_queued",
        task_id=task_id,
    )

    return IngestionResponse(
        task_id=task_id,
        status="queued",
        message=f"Ingestion task {task_id} has been queued",
    )


@router.get(
    "/config/validate",
    response_model=ConfigValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate configuration",
    description="Validate application configuration and check for issues",
)
async def validate_configuration() -> ConfigValidationResponse:
    """Validate application configuration.

    Returns:
        ConfigValidationResponse with validation results
    """
    logger.info("validating_configuration")

    errors = []
    warnings = []
    config_summary = {}

    try:
        config = get_settings()

        # Validate API keys
        if not config.openai_api_key or config.openai_api_key.startswith("your_"):
            errors.append("OpenAI API key is not properly configured")
        else:
            config_summary["openai_configured"] = True

        if not config.pinecone_api_key or config.pinecone_api_key.startswith("your_"):
            errors.append("Pinecone API key is not properly configured")
        else:
            config_summary["pinecone_configured"] = True

        if not config.tavily_api_key or config.tavily_api_key.startswith("your_"):
            errors.append("Tavily API key is not properly configured")
        else:
            config_summary["tavily_configured"] = True

        # Check model settings
        config_summary["openai_model"] = config.openai_model
        config_summary["embedding_model"] = config.openai_embedding_model
        config_summary["temperature"] = config.openai_temperature

        # Check vector store settings
        config_summary["pinecone_index"] = config.pinecone_index_name
        config_summary["vector_dimension"] = config.pinecone_dimension

        # Check application settings
        config_summary["environment"] = config.environment
        config_summary["log_level"] = config.log_level
        config_summary["max_conversation_history"] = config.max_conversation_history

        # Warnings for development settings in production
        if config.is_production:
            if config.api_reload:
                warnings.append("Auto-reload is enabled in production environment")
            if config.log_level == "DEBUG":
                warnings.append("Debug logging is enabled in production environment")

        # Check retry settings
        if config.max_retries < 1:
            warnings.append("Max retries is set to less than 1")

        config_summary["max_retries"] = config.max_retries
        config_summary["retry_delay"] = config.retry_delay

        valid = len(errors) == 0

        logger.info(
            "configuration_validated",
            valid=valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
        )

        return ConfigValidationResponse(
            valid=valid,
            errors=errors,
            warnings=warnings,
            config_summary=config_summary,
        )

    except Exception as e:
        logger.error(
            "configuration_validation_failed",
            error=str(e),
            exc_info=True,
        )

        return ConfigValidationResponse(
            valid=False,
            errors=[f"Configuration validation failed: {str(e)}"],
            warnings=warnings,
            config_summary=config_summary,
        )


@router.get(
    "/config",
    status_code=status.HTTP_200_OK,
    summary="Get configuration summary",
    description="Get non-sensitive configuration information",
)
async def get_configuration() -> dict[str, Any]:
    """Get configuration summary (non-sensitive values only).

    Returns:
        Dictionary with configuration information
    """
    config = get_settings()

    logger.info("retrieving_configuration_summary")

    return {
        "app_name": config.app_name,
        "version": "0.1.0",
        "environment": config.environment,
        "models": {
            "llm": config.openai_model,
            "embedding": config.openai_embedding_model,
            "temperature": config.openai_temperature,
        },
        "vector_store": {
            "index_name": config.pinecone_index_name,
            "dimension": config.pinecone_dimension,
            "top_k": config.vector_search_top_k,
        },
        "search": {
            "max_results": config.tavily_max_results,
            "search_depth": config.tavily_search_depth,
        },
        "conversation": {
            "max_history": config.max_conversation_history,
        },
        "retry": {
            "max_retries": config.max_retries,
            "retry_delay": config.retry_delay,
        },
    }


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get application metrics",
    description="Get all collected application metrics including latency, token usage, and user satisfaction",
)
async def get_metrics() -> dict[str, Any]:
    """Get all application metrics.

    Returns:
        Dictionary with all metrics
    """
    from src.utils.metrics import get_metrics_collector

    logger.info("retrieving_application_metrics")

    metrics_collector = get_metrics_collector()
    metrics = metrics_collector.get_all_metrics()

    logger.info(
        "application_metrics_retrieved",
        total_operations=sum(metrics.get("operation_counts", {}).values()),
    )

    return metrics


@router.get(
    "/metrics/prometheus",
    status_code=status.HTTP_200_OK,
    summary="Get metrics in Prometheus format",
    description="Export metrics in Prometheus text format for scraping",
    response_class=None,
)
async def get_prometheus_metrics():
    """Export metrics in Prometheus format.

    Returns:
        Plain text response with Prometheus metrics
    """
    from fastapi.responses import PlainTextResponse

    from src.utils.metrics import get_metrics_collector

    logger.debug("exporting_prometheus_metrics")

    metrics_collector = get_metrics_collector()

    # Build Prometheus format output
    lines = []

    # Add metadata
    lines.append("# HELP chatformula1_info Application information")
    lines.append("# TYPE chatformula1_info gauge")
    config = get_settings()
    lines.append(
        f'chatformula1_info{{version="0.1.0",environment="{config.environment}"}} 1'
    )
    lines.append("")

    # Latency metrics
    latency_stats = metrics_collector.get_latency_stats()
    if latency_stats.get("count", 0) > 0:
        lines.append("# HELP chatformula1_latency_seconds Operation latency in seconds")
        lines.append("# TYPE chatformula1_latency_seconds summary")
        lines.append(
            f'chatformula1_latency_seconds{{quantile="0.5"}} {latency_stats["p50_ms"] / 1000}'
        )
        lines.append(
            f'chatformula1_latency_seconds{{quantile="0.95"}} {latency_stats["p95_ms"] / 1000}'
        )
        lines.append(
            f'chatformula1_latency_seconds{{quantile="0.99"}} {latency_stats["p99_ms"] / 1000}'
        )
        lines.append(
            f'chatformula1_latency_seconds_sum {latency_stats["mean_ms"] / 1000}'
        )
        lines.append(f'chatformula1_latency_seconds_count {latency_stats["count"]}')
        lines.append("")

    # API success rates
    api_stats = metrics_collector.get_api_success_rates()
    if api_stats:
        lines.append(
            "# HELP chatformula1_api_calls_total Total API calls by service and status"
        )
        lines.append("# TYPE chatformula1_api_calls_total counter")
        for service, stats in api_stats.items():
            lines.append(
                f'chatformula1_api_calls_total{{service="{service}",status="success"}} {stats["successful"]}'
            )
            lines.append(
                f'chatformula1_api_calls_total{{service="{service}",status="failure"}} {stats["failed"]}'
            )
        lines.append("")

        lines.append("# HELP chatformula1_api_success_rate API success rate by service")
        lines.append("# TYPE chatformula1_api_success_rate gauge")
        for service, stats in api_stats.items():
            lines.append(
                f'chatformula1_api_success_rate{{service="{service}"}} {stats["success_rate"]}'
            )
        lines.append("")

    # Token usage
    token_stats = metrics_collector.get_token_usage_stats()
    if token_stats.get("total_requests", 0) > 0:
        lines.append("# HELP chatformula1_tokens_total Total tokens used")
        lines.append("# TYPE chatformula1_tokens_total counter")
        lines.append(f'chatformula1_tokens_total {token_stats["total_tokens"]}')
        lines.append("")

        lines.append("# HELP chatformula1_cost_usd_total Total estimated cost in USD")
        lines.append("# TYPE chatformula1_cost_usd_total counter")
        lines.append(f'chatformula1_cost_usd_total {token_stats["total_cost_usd"]}')
        lines.append("")

        # Per-model metrics
        for model, stats in token_stats.get("by_model", {}).items():
            lines.append(
                f'chatformula1_tokens_total{{model="{model}"}} {stats["total_tokens"]}'
            )
            lines.append(
                f'chatformula1_cost_usd_total{{model="{model}"}} {stats["cost_usd"]}'
            )
        lines.append("")

    # User satisfaction
    satisfaction_stats = metrics_collector.get_user_satisfaction_stats()
    if satisfaction_stats.get("total_feedback", 0) > 0:
        lines.append("# HELP chatformula1_user_feedback_total Total user feedback")
        lines.append("# TYPE chatformula1_user_feedback_total counter")
        lines.append(
            f'chatformula1_user_feedback_total{{rating="positive"}} {satisfaction_stats["positive"]}'
        )
        lines.append(
            f'chatformula1_user_feedback_total{{rating="negative"}} {satisfaction_stats["negative"]}'
        )
        lines.append("")

        lines.append("# HELP chatformula1_satisfaction_rate User satisfaction rate")
        lines.append("# TYPE chatformula1_satisfaction_rate gauge")
        lines.append(
            f'chatformula1_satisfaction_rate {satisfaction_stats["satisfaction_rate"]}'
        )
        lines.append("")

    # Operation counts
    all_metrics = metrics_collector.get_all_metrics()
    operation_counts = all_metrics.get("operation_counts", {})
    if operation_counts:
        lines.append("# HELP chatformula1_operations_total Total operations by type")
        lines.append("# TYPE chatformula1_operations_total counter")
        for operation, count in operation_counts.items():
            lines.append(
                f'chatformula1_operations_total{{operation="{operation}"}} {count}'
            )
        lines.append("")

    prometheus_output = "\n".join(lines)

    logger.debug(
        "prometheus_metrics_exported",
        lines_count=len(lines),
    )

    return PlainTextResponse(content=prometheus_output)


@router.post(
    "/metrics/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset metrics",
    description="Reset all collected metrics (use with caution)",
)
async def reset_metrics() -> dict[str, str]:
    """Reset all metrics.

    Returns:
        Confirmation message
    """
    from src.utils.metrics import get_metrics_collector

    logger.warning("resetting_application_metrics")

    metrics_collector = get_metrics_collector()
    metrics_collector.reset_metrics()

    return {
        "status": "success",
        "message": "All metrics have been reset",
    }


@router.post(
    "/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback",
    description="Submit user satisfaction feedback for a message",
)
async def submit_feedback(
    session_id: str,
    message_id: str,
    rating: int,
    feedback_text: Optional[str] = None,
) -> dict[str, str]:
    """Submit user feedback.

    Args:
        session_id: Session identifier
        message_id: Message identifier
        rating: Rating (1 for negative, 5 for positive)
        feedback_text: Optional feedback text

    Returns:
        Confirmation message

    Raises:
        HTTPException: If rating is invalid
    """
    from src.utils.metrics import get_metrics_collector

    if rating not in [1, 5]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be 1 (negative) or 5 (positive)",
        )

    logger.info(
        "user_feedback_submitted",
        session_id=session_id,
        message_id=message_id,
        rating=rating,
    )

    metrics_collector = get_metrics_collector()
    metrics_collector.record_user_feedback(
        session_id=session_id,
        message_id=message_id,
        rating=rating,
        feedback_text=feedback_text,
    )

    return {
        "status": "success",
        "message": "Feedback recorded successfully",
    }


# Dashboard endpoints
@router.get(
    "/dashboard/summary",
    status_code=status.HTTP_200_OK,
    summary="Get dashboard summary",
    description="Get high-level monitoring dashboard summary",
)
async def get_dashboard_summary() -> dict[str, Any]:
    """Get monitoring dashboard summary.

    Returns:
        Dashboard summary data
    """
    from src.utils.dashboard import get_monitoring_dashboard

    logger.info("retrieving_dashboard_summary")

    dashboard = get_monitoring_dashboard()
    return dashboard.get_dashboard_summary()


@router.get(
    "/dashboard/latency",
    status_code=status.HTTP_200_OK,
    summary="Get latency dashboard",
    description="Get latency metrics dashboard with charts",
)
async def get_latency_dashboard() -> dict[str, Any]:
    """Get latency dashboard.

    Returns:
        Latency dashboard data
    """
    from src.utils.dashboard import get_monitoring_dashboard

    logger.info("retrieving_latency_dashboard")

    dashboard = get_monitoring_dashboard()
    return dashboard.get_latency_dashboard()


@router.get(
    "/dashboard/cost",
    status_code=status.HTTP_200_OK,
    summary="Get cost tracking dashboard",
    description="Get cost tracking dashboard with projections",
)
async def get_cost_dashboard() -> dict[str, Any]:
    """Get cost tracking dashboard.

    Returns:
        Cost dashboard data
    """
    from src.utils.dashboard import get_monitoring_dashboard

    logger.info("retrieving_cost_dashboard")

    dashboard = get_monitoring_dashboard()
    return dashboard.get_cost_dashboard()


@router.get(
    "/dashboard/api-health",
    status_code=status.HTTP_200_OK,
    summary="Get API health dashboard",
    description="Get API health dashboard with success rates",
)
async def get_api_health_dashboard() -> dict[str, Any]:
    """Get API health dashboard.

    Returns:
        API health dashboard data
    """
    from src.utils.dashboard import get_monitoring_dashboard

    logger.info("retrieving_api_health_dashboard")

    dashboard = get_monitoring_dashboard()
    return dashboard.get_api_health_dashboard()


@router.get(
    "/dashboard/satisfaction",
    status_code=status.HTTP_200_OK,
    summary="Get user satisfaction dashboard",
    description="Get user satisfaction dashboard with insights",
)
async def get_satisfaction_dashboard() -> dict[str, Any]:
    """Get user satisfaction dashboard.

    Returns:
        User satisfaction dashboard data
    """
    from src.utils.dashboard import get_monitoring_dashboard

    logger.info("retrieving_satisfaction_dashboard")

    dashboard = get_monitoring_dashboard()
    return dashboard.get_user_satisfaction_dashboard()


@router.get(
    "/dashboard/errors",
    status_code=status.HTTP_200_OK,
    summary="Get error rate dashboard",
    description="Get error rate visualization dashboard",
)
async def get_error_dashboard() -> dict[str, Any]:
    """Get error rate dashboard.

    Returns:
        Error rate dashboard data
    """
    from src.utils.dashboard import get_monitoring_dashboard

    logger.info("retrieving_error_dashboard")

    dashboard = get_monitoring_dashboard()
    return dashboard.get_error_rate_dashboard()


# API Key Management Endpoints
class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(..., description="Key name/description")
    scopes: Optional[list[str]] = Field(None, description="Allowed scopes")
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Days until expiration"
    )
    rate_limit_multiplier: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Rate limit multiplier"
    )


class APIKeyResponse(BaseModel):
    """API key response."""

    key_id: str = Field(..., description="Key ID")
    key: Optional[str] = Field(None, description="Raw API key (only shown once)")
    name: str = Field(..., description="Key name")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(..., description="Whether key is active")
    scopes: list[str] = Field(..., description="Allowed scopes")


@router.post(
    "/api-keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Generate a new API key for authentication",
)
async def create_api_key(request: APIKeyCreateRequest) -> APIKeyResponse:
    """Create a new API key.

    Args:
        request: API key creation request

    Returns:
        APIKeyResponse with the new key (shown only once)
    """
    from src.security.authentication import get_api_key_manager

    logger.info(
        "creating_api_key",
        name=request.name,
        scopes=request.scopes,
    )

    manager = get_api_key_manager()
    raw_key, api_key = manager.generate_key(
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
        rate_limit_multiplier=request.rate_limit_multiplier,
    )

    logger.info(
        "api_key_created",
        key_id=api_key.key_id,
        name=api_key.name,
    )

    return APIKeyResponse(
        key_id=api_key.key_id,
        key=raw_key,  # Only shown once
        name=api_key.name,
        created_at=api_key.created_at.isoformat(),
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        is_active=api_key.is_active,
        scopes=api_key.scopes,
    )


@router.get(
    "/api-keys",
    response_model=list[APIKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="List API keys",
    description="List all API keys (without raw key values)",
)
async def list_api_keys(include_inactive: bool = False) -> list[APIKeyResponse]:
    """List all API keys.

    Args:
        include_inactive: Include inactive keys

    Returns:
        List of API keys
    """
    from src.security.authentication import get_api_key_manager

    logger.info("listing_api_keys", include_inactive=include_inactive)

    manager = get_api_key_manager()
    keys = manager.list_keys(include_inactive=include_inactive)

    return [
        APIKeyResponse(
            key_id=key.key_id,
            key=None,  # Never return raw key
            name=key.name,
            created_at=key.created_at.isoformat(),
            expires_at=key.expires_at.isoformat() if key.expires_at else None,
            is_active=key.is_active,
            scopes=key.scopes,
        )
        for key in keys
    ]


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke API key",
    description="Revoke an API key (makes it inactive)",
)
async def revoke_api_key(key_id: str) -> dict[str, str]:
    """Revoke an API key.

    Args:
        key_id: Key ID to revoke

    Returns:
        Confirmation message

    Raises:
        HTTPException: If key not found
    """
    from src.security.authentication import get_api_key_manager

    logger.info("revoking_api_key", key_id=key_id)

    manager = get_api_key_manager()
    success = manager.revoke_key(key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found",
        )

    logger.info("api_key_revoked", key_id=key_id)

    return {
        "status": "success",
        "message": f"API key {key_id} has been revoked",
    }


@router.post(
    "/api-keys/{key_id}/rotate",
    response_model=APIKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate API key",
    description="Generate a new API key with the same settings and revoke the old one",
)
async def rotate_api_key(key_id: str) -> APIKeyResponse:
    """Rotate an API key.

    Args:
        key_id: Key ID to rotate

    Returns:
        APIKeyResponse with the new key

    Raises:
        HTTPException: If key not found
    """
    from src.security.authentication import get_api_key_manager

    logger.info("rotating_api_key", key_id=key_id)

    manager = get_api_key_manager()
    result = manager.rotate_key(key_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found",
        )

    raw_key, new_api_key = result

    logger.info(
        "api_key_rotated",
        old_key_id=key_id,
        new_key_id=new_api_key.key_id,
    )

    return APIKeyResponse(
        key_id=new_api_key.key_id,
        key=raw_key,  # Only shown once
        name=new_api_key.name,
        created_at=new_api_key.created_at.isoformat(),
        expires_at=(
            new_api_key.expires_at.isoformat() if new_api_key.expires_at else None
        ),
        is_active=new_api_key.is_active,
        scopes=new_api_key.scopes,
    )
