"""Health check endpoints for ChatFormula1 API.

This module provides health check endpoints for monitoring application status
and dependency health.
"""

from typing import Any

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str
    dependencies: dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Check the health status of the API and its dependencies",
)
async def health_check() -> HealthResponse:
    """Check health status of API and dependencies.

    Returns:
        HealthResponse with status and dependency information
    """
    config = get_settings()

    # Import here to avoid circular dependencies
    from src.api.main import app_state

    # Check dependencies
    dependencies = {}

    # Check vector store
    if app_state.get("vector_store"):
        try:
            # Try to ping vector store
            vector_store = app_state["vector_store"]
            # Simple check - if it's initialized, consider it healthy
            dependencies["vector_store"] = "healthy"
        except Exception as e:
            logger.error("vector_store_health_check_failed", error=str(e))
            dependencies["vector_store"] = f"unhealthy: {str(e)}"
    else:
        dependencies["vector_store"] = "not_initialized"

    # Check Tavily client
    if app_state.get("tavily_client"):
        dependencies["tavily_client"] = "healthy"
    else:
        dependencies["tavily_client"] = "not_initialized"

    # Check agent graph
    if app_state.get("agent_graph"):
        dependencies["agent_graph"] = "healthy"
    else:
        dependencies["agent_graph"] = "not_initialized"

    # Determine overall status
    all_healthy = all(dep_status == "healthy" for dep_status in dependencies.values())
    overall_status = "healthy" if all_healthy else "degraded"

    logger.info(
        "health_check_completed",
        status=overall_status,
        dependencies=dependencies,
    )

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        environment=config.environment,
        dependencies=dependencies,
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
    description="Simple root endpoint that returns API information",
)
async def root() -> dict[str, Any]:
    """Root endpoint with API information.

    Returns:
        Dictionary with API information
    """
    config = get_settings()

    return {
        "name": config.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }
