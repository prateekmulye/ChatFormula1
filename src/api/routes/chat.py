"""Chat endpoints for ChatFormula1 API.

This module provides endpoints for chat interactions, including message processing,
streaming responses, and conversation management.
"""

import json
from typing import Any, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field, field_validator

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()


# Request/Response Models
class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(
        None, description="Session ID for conversation continuity"
    )
    stream: bool = Field(default=False, description="Enable streaming response")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate and sanitize message."""
        from src.security.input_validation import validate_query

        # Validate input
        validation_result = validate_query(v, strict_mode=False)

        if not validation_result.valid:
            raise ValueError(f"Invalid message: {', '.join(validation_result.errors)}")

        # Return sanitized input
        return validation_result.sanitized_input or v


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )


class ConversationHistoryResponse(BaseModel):
    """Conversation history response model."""

    session_id: str = Field(..., description="Session ID")
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    message_count: int = Field(..., description="Total message count")


class SessionClearResponse(BaseModel):
    """Session clear response model."""

    session_id: str = Field(..., description="Cleared session ID")
    message: str = Field(..., description="Confirmation message")


# In-memory session storage (replace with Redis in production)
session_storage: dict[str, MemorySaver] = {}


def get_or_create_session(session_id: str) -> MemorySaver:
    """Get existing session or create new one.

    Args:
        session_id: Session identifier

    Returns:
        MemorySaver instance for the session
    """
    if session_id not in session_storage:
        session_storage[session_id] = MemorySaver()
        logger.info("session_created", session_id=session_id)
    return session_storage[session_id]


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send chat message",
    description="Send a message to the ChatFormula1 chatbot and receive a response",
)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """Process chat message and return response.

    Args:
        request: Chat request with message and session info
        http_request: FastAPI request object for accessing state

    Returns:
        ChatResponse with assistant's reply

    Raises:
        HTTPException: If agent is not initialized or processing fails
    """
    from src.api.main import app_state

    # Get agent graph
    agent_graph = app_state.get("agent_graph")
    if not agent_graph:
        logger.error("agent_not_initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent is not initialized. Please try again later.",
        )

    # Generate session ID if not provided
    session_id = request.session_id or f"session_{http_request.state.request_id}"

    # Get or create session checkpointer
    checkpointer = get_or_create_session(session_id)

    # Recompile graph with session checkpointer
    compiled_graph = agent_graph.graph.compile(checkpointer=checkpointer)

    logger.info(
        "processing_chat_message",
        session_id=session_id,
        message_length=len(request.message),
        stream=request.stream,
    )

    try:
        # Prepare initial state
        initial_state = {
            "query": request.message,
            "messages": [],
            "intent": None,
            "entities": {},
            "retrieved_docs": [],
            "search_results": [],
            "context": "",
            "response": None,
            "metadata": {},
        }

        # Configure for session
        config = {
            "configurable": {
                "thread_id": session_id,
            }
        }

        # Invoke agent graph
        result = await compiled_graph.ainvoke(initial_state, config=config)

        # Extract response
        response_text = result.get(
            "response", "I apologize, but I couldn't generate a response."
        )
        metadata = result.get("metadata", {})

        logger.info(
            "chat_message_processed",
            session_id=session_id,
            response_length=len(response_text),
            metadata=metadata,
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            metadata=metadata,
        )

    except Exception as e:
        logger.error(
            "chat_processing_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
    summary="Send chat message with streaming",
    description="Send a message and receive a streaming response using Server-Sent Events",
)
async def chat_stream(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """Process chat message and stream response.

    Args:
        request: Chat request with message and session info
        http_request: FastAPI request object for accessing state

    Returns:
        StreamingResponse with Server-Sent Events

    Raises:
        HTTPException: If agent is not initialized or processing fails
    """
    from src.api.main import app_state

    # Get agent graph
    agent_graph = app_state.get("agent_graph")
    if not agent_graph:
        logger.error("agent_not_initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent is not initialized. Please try again later.",
        )

    # Generate session ID if not provided
    session_id = request.session_id or f"session_{http_request.state.request_id}"

    # Get or create session checkpointer
    checkpointer = get_or_create_session(session_id)

    # Recompile graph with session checkpointer
    compiled_graph = agent_graph.graph.compile(checkpointer=checkpointer)

    logger.info(
        "processing_chat_stream",
        session_id=session_id,
        message_length=len(request.message),
    )

    async def event_generator():
        """Generate Server-Sent Events for streaming response."""
        try:
            # Prepare initial state
            initial_state = {
                "query": request.message,
                "messages": [],
                "intent": None,
                "entities": {},
                "retrieved_docs": [],
                "search_results": [],
                "context": "",
                "response": None,
                "metadata": {},
            }

            # Configure for session
            config = {
                "configurable": {
                    "thread_id": session_id,
                }
            }

            # Stream events from graph
            async for event in compiled_graph.astream_events(
                initial_state, config=config, version="v1"
            ):
                event_type = event.get("event")

                # Send node updates
                if event_type == "on_chain_start":
                    node_name = event.get("name", "")
                    if node_name:
                        yield f"data: {json.dumps({'type': 'node', 'node': node_name})}\n\n"

                # Send LLM token streams
                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        content = chunk.content
                        if content:
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                # Send final result
                elif event_type == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    if output and isinstance(output, dict):
                        response_text = output.get("response")
                        metadata = output.get("metadata", {})
                        if response_text:
                            yield f"data: {json.dumps({'type': 'complete', 'response': response_text, 'metadata': metadata, 'session_id': session_id})}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            logger.info(
                "chat_stream_completed",
                session_id=session_id,
            )

        except Exception as e:
            logger.error(
                "chat_stream_failed",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id,
        },
    )


@router.get(
    "/chat/history/{session_id}",
    response_model=ConversationHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation history",
    description="Retrieve conversation history for a specific session",
)
async def get_conversation_history(session_id: str) -> ConversationHistoryResponse:
    """Get conversation history for a session.

    Args:
        session_id: Session identifier

    Returns:
        ConversationHistoryResponse with message history

    Raises:
        HTTPException: If session not found
    """
    logger.info("retrieving_conversation_history", session_id=session_id)

    # Check if session exists
    if session_id not in session_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    checkpointer = session_storage[session_id]

    try:
        # Get checkpoint data
        config = {"configurable": {"thread_id": session_id}}
        checkpoint = checkpointer.get(config)

        messages = []
        if checkpoint:
            # Extract messages from checkpoint
            state = checkpoint.get("channel_values", {})
            state_messages = state.get("messages", [])

            # Convert to ChatMessage format
            for msg in state_messages:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    messages.append(
                        ChatMessage(
                            role=(
                                "user" if isinstance(msg, HumanMessage) else "assistant"
                            ),
                            content=msg.content,
                        )
                    )

        logger.info(
            "conversation_history_retrieved",
            session_id=session_id,
            message_count=len(messages),
        )

        return ConversationHistoryResponse(
            session_id=session_id,
            messages=messages,
            message_count=len(messages),
        )

    except Exception as e:
        logger.error(
            "conversation_history_retrieval_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}",
        )


@router.delete(
    "/chat/session/{session_id}",
    response_model=SessionClearResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear conversation session",
    description="Clear conversation history and reset session",
)
async def clear_session(session_id: str) -> SessionClearResponse:
    """Clear conversation session.

    Args:
        session_id: Session identifier to clear

    Returns:
        SessionClearResponse with confirmation

    Raises:
        HTTPException: If session not found
    """
    logger.info("clearing_session", session_id=session_id)

    # Check if session exists
    if session_id not in session_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    try:
        # Remove session from storage
        del session_storage[session_id]

        logger.info("session_cleared", session_id=session_id)

        return SessionClearResponse(
            session_id=session_id,
            message="Session cleared successfully",
        )

    except Exception as e:
        logger.error(
            "session_clear_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear session: {str(e)}",
        )


@router.get(
    "/chat/sessions",
    status_code=status.HTTP_200_OK,
    summary="List active sessions",
    description="Get list of all active conversation sessions",
)
async def list_sessions() -> dict[str, Any]:
    """List all active sessions.

    Returns:
        Dictionary with session information
    """
    logger.info("listing_sessions")

    sessions = [
        {
            "session_id": session_id,
            "created": True,  # Could add timestamp tracking
        }
        for session_id in session_storage.keys()
    ]

    return {
        "sessions": sessions,
        "total_count": len(sessions),
    }


@router.get(
    "/chat/rate-limit",
    status_code=status.HTTP_200_OK,
    summary="Get rate limit status",
    description="Get current rate limit status for the client",
)
async def get_rate_limit_status(request: Request) -> dict[str, Any]:
    """Get rate limit status for the current client.

    Args:
        request: FastAPI request

    Returns:
        Dictionary with rate limit information
    """
    from src.security.rate_limiting import get_rate_limiter

    config = get_settings()

    if not config.enable_rate_limiting:
        return {
            "enabled": False,
            "message": "Rate limiting is disabled",
        }

    rate_limiter = get_rate_limiter()
    rate_info = rate_limiter.get_rate_limit_info(request)

    logger.debug(
        "rate_limit_status_retrieved",
        client_id=rate_info["client_id"],
    )

    return {
        "enabled": True,
        **rate_info,
    }
