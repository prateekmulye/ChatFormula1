"""Internal FastAPI surface for the agent service.

Three endpoints, all guarded by a static bearer token (``INTERNAL_API_TOKEN``):

- ``POST /internal/chat``   — stateless NDJSON streaming chat (the frozen
  contract documented in docs/STREAMING_PROTOCOL.md)
- ``POST /internal/ingest`` — trigger an ingestion run
- ``GET  /internal/health`` — liveness probe (also used to pre-warm cold starts)

The service holds no conversation state: history arrives in the request
body and the gateway owns the thread.
"""

import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from chatf1_agent.graph import F1AgentGraph
from chatf1_agent.guards import scan_for_prompt_injection
from chatf1_agent.logging import set_request_id, setup_logging
from chatf1_agent.providers import GENERATION_TAG
from chatf1_agent.retrieval.tavily import TavilyClient
from chatf1_agent.retrieval.vector_store import (
    NAMESPACE_NEWS,
    VectorStoreManager,
)
from chatf1_agent.settings import get_settings
from chatf1_agent.state import AgentState

logger = structlog.get_logger(__name__)

# Graph nodes surfaced as node_started events on the stream.
PIPELINE_NODES = frozenset(
    {
        "analyze_query",
        "route",
        "vector_search",
        "tavily_search",
        "parallel_retrieval",
        "rank_context",
        "generate",
        "format_response",
    }
)


class HistoryMessage(BaseModel):
    """One prior conversation turn supplied by the gateway."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request body for POST /internal/chat."""

    message: str = Field(min_length=1, description="Current user message")
    history: list[HistoryMessage] = Field(
        default_factory=list,
        description="Prior turns, oldest first (gateway sends a last-10 window)",
    )
    request_id: str = Field(default="", description="Correlation ID from the gateway")


class IngestRequest(BaseModel):
    """Request body for POST /internal/ingest."""

    source: Literal["static", "news"] = Field(
        default="static",
        description="static = data/ corpus into static_corpus; news = Tavily into news",
    )
    topic: str | None = Field(
        default=None,
        description="Optional topic filter for news ingestion",
    )


def verify_internal_token(
    authorization: str | None = Header(default=None),
) -> None:
    """Validate the static bearer token with a constant-time comparison.

    Raises:
        HTTPException: 503 if the token is not configured, 401 on mismatch.
    """
    expected = get_settings().internal_api_token
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="INTERNAL_API_TOKEN is not configured",
        )

    provided = ""
    if authorization and authorization.startswith("Bearer "):
        provided = authorization.removeprefix("Bearer ")

    if not secrets.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
        )


def _ndjson_line(payload: dict[str, Any]) -> str:
    """Serialize one protocol event as an NDJSON line."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"


def _history_to_messages(history: list[HistoryMessage]) -> list[BaseMessage]:
    """Convert gateway history payload to LangChain messages."""
    messages: list[BaseMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        else:
            messages.append(AIMessage(content=turn.content))
    return messages


async def stream_chat_events(
    graph: F1AgentGraph,
    request: ChatRequest,
) -> AsyncIterator[str]:
    """Run the graph and yield NDJSON protocol events.

    Event order: ``node_started``* → ``sources``? → ``token``* → ``complete``,
    with ``error`` terminating the stream on failure. Tokens are forwarded
    only from the generation-tagged model, so analysis JSON never leaks.
    Cache hits emit zero tokens and a single ``complete`` with ``cached: true``.
    """
    if request.request_id:
        set_request_id(request.request_id)

    verdict = scan_for_prompt_injection(request.message)
    if verdict.flagged:
        yield _ndjson_line(
            {
                "event": "error",
                "code": "validation",
                "message": "Message rejected by prompt-injection guard.",
                "retryable": False,
            }
        )
        return

    state = AgentState(
        query=request.message,
        messages=_history_to_messages(request.history),
        request_id=request.request_id,
    )

    response_text = ""
    cached = False
    usage: dict[str, int] | None = None

    try:
        async for event in graph.compiled_graph.astream_events(state, version="v2"):
            event_type = event["event"]
            name = event.get("name", "")

            if event_type == "on_chain_start" and name in PIPELINE_NODES:
                yield _ndjson_line({"event": "node_started", "node": name})

            elif event_type == "on_chat_model_stream" and GENERATION_TAG in event.get(
                "tags", []
            ):
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield _ndjson_line({"event": "token", "text": chunk.content})

            elif event_type == "on_chain_end" and name == "rank_context":
                output = event["data"].get("output") or {}
                sources = output.get("metadata", {}).get("sources", [])
                yield _ndjson_line({"event": "sources", "items": sources})

            elif event_type == "on_chain_end" and name == "generate":
                output = event["data"].get("output") or {}
                metadata = output.get("metadata", {})
                cached = bool(metadata.get("from_cache", False))
                usage = metadata.get("token_usage") or None
                response_text = output.get("response") or response_text

            elif event_type == "on_chain_end" and name == "format_response":
                output = event["data"].get("output") or {}
                response_text = output.get("response") or response_text

        yield _ndjson_line(
            {
                "event": "complete",
                "content": response_text,
                "cached": cached,
                "usage": usage,
            }
        )

    except Exception as e:
        logger.error(
            "chat_stream_failed",
            error=str(e),
            error_type=type(e).__name__,
            request_id=request.request_id,
        )
        yield _ndjson_line(
            {
                "event": "error",
                "code": "internal",
                "message": "Agent pipeline failed.",
                "retryable": True,
            }
        )


async def _run_news_ingestion(
    tavily_client: TavilyClient,
    vector_store: VectorStoreManager,
    topic: str | None,
) -> None:
    """Fetch latest F1 news via Tavily and upsert into the news namespace."""
    try:
        results = await tavily_client.get_latest_f1_news(topic=topic)
        documents = tavily_client.convert_to_documents(results)
        ids = await vector_store.add_documents(documents, namespace=NAMESPACE_NEWS)
        logger.info("news_ingestion_complete", documents_ingested=len(ids))
    except Exception as e:
        logger.error("news_ingestion_failed", error=str(e))


async def _run_static_ingestion() -> None:
    """Run the offline ingestion pipeline over the data/ corpus."""
    from ingestion.pipeline import IngestionPipeline

    try:
        pipeline = IngestionPipeline(config=get_settings())
        stats = await pipeline.ingest_all()
        logger.info("static_ingestion_complete", stats=stats)
    except Exception as e:
        logger.error("static_ingestion_failed", error=str(e))


def create_app(init_resources: bool = True) -> FastAPI:
    """Create the FastAPI application.

    Args:
        init_resources: Build the graph and external clients during startup.
            Tests pass False and attach fakes to ``app.state`` instead.

    Returns:
        Configured FastAPI app with the three internal endpoints.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings = get_settings()
        setup_logging(settings.log_level, json_output=not settings.is_development)

        if init_resources:
            vector_store = VectorStoreManager(settings)
            await vector_store.initialize()
            tavily_client = TavilyClient(settings)

            app.state.vector_store = vector_store
            app.state.tavily_client = tavily_client
            # Compiled exactly once for the process lifetime.
            app.state.graph = F1AgentGraph(settings, vector_store, tavily_client)

            logger.info("agent_service_started")

        yield

        if init_resources:
            await app.state.vector_store.close()
            logger.info("agent_service_stopped")

    app = FastAPI(
        title="ChatFormula1 Agent",
        description="Internal-only stateless inference engine",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.post("/internal/chat", dependencies=[Depends(verify_internal_token)])
    async def chat(request: ChatRequest) -> StreamingResponse:
        """Stream NDJSON events for one chat turn."""
        return StreamingResponse(
            stream_chat_events(app.state.graph, request),
            media_type="application/x-ndjson",
        )

    @app.post("/internal/ingest", dependencies=[Depends(verify_internal_token)])
    async def ingest(request: IngestRequest) -> dict[str, str]:
        """Kick off an ingestion run in the background."""
        if request.source == "news":
            coro = _run_news_ingestion(
                app.state.tavily_client,
                app.state.vector_store,
                request.topic,
            )
        else:
            coro = _run_static_ingestion()

        task = asyncio.create_task(coro)
        app.state.ingest_task = task  # keep a reference so it isn't GC'd

        logger.info("ingestion_triggered", source=request.source)
        return {"status": "accepted", "source": request.source}

    @app.get("/internal/health", dependencies=[Depends(verify_internal_token)])
    async def health() -> dict[str, str]:
        """Liveness probe; doubles as the cold-start pre-warm target."""
        return {"status": "ok", "service": "chatf1-agent"}

    return app


app = create_app()
