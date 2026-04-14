"""FastAPI application for ChatFormula1 agent API.

This module implements the REST API layer for the ChatFormula1 chatbot,
providing endpoints for chat interactions, health checks, and admin operations.
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

import structlog
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


# Global state for dependencies
app_state = {
    "vector_store": None,
    "tavily_client": None,
    "agent_graph": None,
    "background_tasks": {},  # Track background tasks
    "task_queue": None,  # Background task queue
}


async def _process_background_tasks():
    """Process background tasks from the queue.

    This coroutine runs continuously, processing tasks from the queue
    in the background without blocking API requests.
    """
    logger.info("background_task_processor_started")

    while True:
        try:
            # Get task from queue (wait up to 1 second)
            try:
                task_data = await asyncio.wait_for(
                    app_state["task_queue"].get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                # No tasks in queue, continue loop
                continue

            task_id = task_data.get("task_id")
            task_type = task_data.get("type")
            task_func = task_data.get("func")
            task_args = task_data.get("args", ())
            task_kwargs = task_data.get("kwargs", {})

            logger.info(
                "processing_background_task",
                task_id=task_id,
                task_type=task_type,
            )

            # Update task status
            app_state["background_tasks"][task_id] = {
                "status": "running",
                "type": task_type,
                "started_at": time.time(),
            }

            try:
                # Execute task
                if asyncio.iscoroutinefunction(task_func):
                    result = await task_func(*task_args, **task_kwargs)
                else:
                    result = task_func(*task_args, **task_kwargs)

                # Update task status
                app_state["background_tasks"][task_id] = {
                    "status": "completed",
                    "type": task_type,
                    "started_at": app_state["background_tasks"][task_id]["started_at"],
                    "completed_at": time.time(),
                    "result": result,
                }

                logger.info(
                    "background_task_completed",
                    task_id=task_id,
                    task_type=task_type,
                )

            except Exception as e:
                # Update task status with error
                app_state["background_tasks"][task_id] = {
                    "status": "failed",
                    "type": task_type,
                    "started_at": app_state["background_tasks"][task_id]["started_at"],
                    "failed_at": time.time(),
                    "error": str(e),
                }

                logger.error(
                    "background_task_failed",
                    task_id=task_id,
                    task_type=task_type,
                    error=str(e),
                )

            # Mark task as done in queue
            app_state["task_queue"].task_done()

        except asyncio.CancelledError:
            logger.info("background_task_processor_cancelled")
            break
        except Exception as e:
            logger.error(
                "background_task_processor_error",
                error=str(e),
                exc_info=True,
            )
            # Continue processing despite errors
            await asyncio.sleep(1)


async def submit_background_task(
    task_type: str,
    task_func,
    *args,
    **kwargs,
) -> str:
    """Submit a task to the background queue.

    Args:
        task_type: Type/name of the task
        task_func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Task ID for tracking
    """
    task_id = str(uuid.uuid4())

    task_data = {
        "task_id": task_id,
        "type": task_type,
        "func": task_func,
        "args": args,
        "kwargs": kwargs,
    }

    # Add to queue
    await app_state["task_queue"].put(task_data)

    # Initialize task status
    app_state["background_tasks"][task_id] = {
        "status": "queued",
        "type": task_type,
        "queued_at": time.time(),
    }

    logger.info(
        "background_task_submitted",
        task_id=task_id,
        task_type=task_type,
    )

    return task_id


def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a background task.

    Args:
        task_id: Task ID to check

    Returns:
        Task status dictionary
    """
    return app_state["background_tasks"].get(
        task_id,
        {"status": "not_found"},
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.

    Handles startup and shutdown events for initializing and cleaning up
    application dependencies.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    config = get_settings()
    logger.info(
        "api_starting",
        app_name=config.app_name,
        environment=config.environment,
        host=config.api_host,
        port=config.api_port,
    )

    try:
        # Initialize dependencies
        from src.agent.graph import F1AgentGraph
        from src.search.tavily_client import TavilyClient
        from src.vector_store.manager import VectorStoreManager

        logger.info("initializing_dependencies")

        # Initialize vector store
        vector_store = VectorStoreManager(config)
        await vector_store.initialize()
        app_state["vector_store"] = vector_store
        logger.info("vector_store_initialized")

        # Initialize Tavily client
        tavily_client = TavilyClient(config)
        app_state["tavily_client"] = tavily_client
        logger.info("tavily_client_initialized")

        # Initialize agent graph
        agent_graph = F1AgentGraph(
            config=config,
            vector_store=vector_store,
            tavily_client=tavily_client,
        )
        agent_graph.compile()
        app_state["agent_graph"] = agent_graph
        logger.info("agent_graph_initialized")

        # Initialize background task queue
        app_state["task_queue"] = asyncio.Queue()
        logger.info("background_task_queue_initialized")

        # Start background task processor
        task_processor = asyncio.create_task(_process_background_tasks())
        app_state["task_processor"] = task_processor
        logger.info("background_task_processor_started")

        logger.info("api_startup_complete")

    except Exception as e:
        logger.error("api_startup_failed", error=str(e), exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("api_shutting_down")

    # Stop background task processor
    if "task_processor" in app_state and app_state["task_processor"]:
        try:
            logger.info("stopping_background_task_processor")
            app_state["task_processor"].cancel()
            try:
                await app_state["task_processor"]
            except asyncio.CancelledError:
                pass
        except Exception as e:
            logger.error("task_processor_cleanup_failed", error=str(e))

    # Clean up resources
    if app_state["vector_store"]:
        try:
            # Close vector store connections if needed
            logger.info("closing_vector_store")
            await app_state["vector_store"].close()
        except Exception as e:
            logger.error("vector_store_cleanup_failed", error=str(e))

    logger.info("api_shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    config = get_settings()

    # Create FastAPI app with OpenAPI documentation
    app = FastAPI(
        title="ChatFormula1 API",
        description=(
            "AI-powered Formula 1 expert chatbot API with RAG architecture. "
            "Provides real-time F1 information, predictions, and insights through "
            "conversational AI."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    if config.enable_cors:
        cors_origins = config.cors_allow_origins
        if not config.is_development:
            # In production, only allow configured origins
            cors_origins = [
                origin
                for origin in cors_origins
                if not origin.startswith("http://localhost")
            ]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=[
                "X-Request-ID",
                "X-RateLimit-Limit-Minute",
                "X-RateLimit-Remaining-Minute",
                "X-RateLimit-Limit-Hour",
                "X-RateLimit-Remaining-Hour",
            ],
        )

    # Add security middleware
    from src.security.middleware import SecurityMiddleware

    app.add_middleware(
        SecurityMiddleware,
        enable_rate_limiting=config.enable_rate_limiting,
        enable_input_validation=config.enable_input_validation,
        requests_per_minute=config.rate_limit_per_minute,
        requests_per_hour=config.rate_limit_per_hour,
        strict_validation=config.strict_input_validation,
    )

    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests with timing and metadata.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        from src.config.logging import clear_context, set_request_id

        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Set request ID in context for correlation
        set_request_id(request_id)

        # Log request
        start_time = time.time()
        logger.info(
            "http_request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params) if request.query_params else None,
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                "http_request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Clear context after request
            clear_context()

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )

            # Clear context after error
            clear_context()

            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": str(e) if config.is_development else "An error occurred",
                },
                headers={"X-Request-ID": request_id},
            )

    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors.

        Args:
            request: HTTP request that caused the error
            exc: Exception that was raised

        Returns:
            JSON error response
        """
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            "unhandled_exception",
            request_id=request_id,
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "request_id": request_id,
                "message": str(exc) if config.is_development else "An error occurred",
            },
            headers={"X-Request-ID": request_id},
        )

    # Register routers
    from src.api.routes import admin, chat, health

    app.include_router(health.router, tags=["Health"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

    logger.info(
        "fastapi_app_created",
        title=app.title,
        version=app.version,
        docs_url=app.docs_url,
    )

    return app


# Create app instance
app = create_app()


def main() -> None:
    """Run the FastAPI application with uvicorn.

    This is the entry point for the f1-api CLI command.
    """
    config = get_settings()

    logger.info(
        "starting_uvicorn_server",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_reload,
    )

    uvicorn.run(
        "src.api.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_reload,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
