# Chat P1 API

FastAPI-based REST API for the Chat P1 chatbot system.

## Features

- **Chat Endpoints**: Send messages and receive responses from the F1 expert chatbot
- **Streaming Support**: Real-time streaming responses using Server-Sent Events
- **Session Management**: Maintain conversation context across multiple interactions
- **Health Checks**: Monitor API and dependency health
- **Admin Endpoints**: Data ingestion, statistics, and configuration validation
- **OpenAPI Documentation**: Auto-generated API docs at `/docs`

## Quick Start

### Running the API

```bash
# Using Poetry
poetry run f1-api

# Or directly with Python
python -m src.api.main

# Or with uvicorn
uvicorn src.api.main:app --reload
```

The API will start on `http://localhost:8000` by default.

### Configuration

Set the following environment variables in your `.env` file:

```env
# Required API Keys
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
TAVILY_API_KEY=your_tavily_key

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## API Endpoints

### Health & Info

#### `GET /`
Root endpoint with API information.

**Response:**
```json
{
  "name": "Chat P1",
  "version": "0.1.0",
  "status": "running",
  "docs": "/docs",
  "health": "/health"
}
```

#### `GET /health`
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": {
    "vector_store": "healthy",
    "tavily_client": "healthy",
    "agent_graph": "healthy"
  }
}
```

### Chat Endpoints

#### `POST /api/chat`
Send a message to the chatbot.

**Request:**
```json
{
  "message": "Who won the 2024 Monaco Grand Prix?",
  "session_id": "optional-session-id",
  "stream": false
}
```

**Response:**
```json
{
  "response": "Max Verstappen won the 2024 Monaco Grand Prix...",
  "session_id": "session_abc123",
  "metadata": {
    "generation_successful": true,
    "response_length": 150
  }
}
```

#### `POST /api/chat/stream`
Send a message and receive a streaming response.

**Request:**
```json
{
  "message": "Tell me about Lewis Hamilton's career",
  "session_id": "optional-session-id"
}
```

**Response:** Server-Sent Events stream
```
data: {"type": "node", "node": "analyze_query"}

data: {"type": "token", "content": "Lewis"}

data: {"type": "token", "content": " Hamilton"}

data: {"type": "complete", "response": "Lewis Hamilton is...", "metadata": {...}, "session_id": "session_abc123"}

data: {"type": "done"}
```

#### `GET /api/chat/history/{session_id}`
Retrieve conversation history for a session.

**Response:**
```json
{
  "session_id": "session_abc123",
  "messages": [
    {
      "role": "user",
      "content": "Who won the 2024 Monaco GP?",
      "timestamp": null
    },
    {
      "role": "assistant",
      "content": "Max Verstappen won...",
      "timestamp": null
    }
  ],
  "message_count": 2
}
```

#### `DELETE /api/chat/session/{session_id}`
Clear a conversation session.

**Response:**
```json
{
  "session_id": "session_abc123",
  "message": "Session cleared successfully"
}
```

#### `GET /api/chat/sessions`
List all active sessions.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_abc123",
      "created": true
    }
  ],
  "total_count": 1
}
```

### Admin Endpoints

#### `GET /api/admin/health`
Detailed health check with dependency information.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": {
    "vector_store": {
      "status": "healthy",
      "index_name": "f1-knowledge",
      "details": {...}
    },
    "tavily_client": {
      "status": "healthy",
      "configured": true
    },
    "agent_graph": {
      "status": "healthy",
      "compiled": true
    },
    "openai": {
      "status": "configured",
      "model": "gpt-4-turbo",
      "embedding_model": "text-embedding-3-small"
    }
  }
}
```

#### `GET /api/admin/stats`
Get vector store statistics.

**Response:**
```json
{
  "index_name": "f1-knowledge",
  "dimension": 1536,
  "total_vectors": 1250,
  "namespaces": ["default"],
  "metadata": {
    "total_vector_count": 1250,
    "dimension": 1536,
    "index_fullness": 0.05,
    "namespaces": {...}
  }
}
```

#### `POST /api/admin/ingest`
Start a background data ingestion task.

**Request:**
```json
{
  "source_path": "data/historical_features.csv",
  "source_type": "auto",
  "batch_size": 100,
  "overwrite": false
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Ingestion task 550e8400-e29b-41d4-a716-446655440000 has been queued"
}
```

#### `GET /api/admin/config/validate`
Validate application configuration.

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "Auto-reload is enabled in production environment"
  ],
  "config_summary": {
    "openai_configured": true,
    "pinecone_configured": true,
    "tavily_configured": true,
    "environment": "production",
    "log_level": "INFO"
  }
}
```

#### `GET /api/admin/config`
Get non-sensitive configuration summary.

**Response:**
```json
{
  "app_name": "Chat P1",
  "version": "0.1.0",
  "environment": "development",
  "models": {
    "llm": "gpt-4-turbo",
    "embedding": "text-embedding-3-small",
    "temperature": 0.7
  },
  "vector_store": {
    "index_name": "f1-knowledge",
    "dimension": 1536,
    "top_k": 5
  },
  "search": {
    "max_results": 5,
    "search_depth": "advanced"
  },
  "conversation": {
    "max_history": 10
  },
  "retry": {
    "max_retries": 3,
    "retry_delay": 1.0
  }
}
```

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## CORS Configuration

The API is configured with CORS middleware to allow requests from:

- `http://localhost:3000` (Next.js dev server)
- `http://localhost:8501` (Streamlit)
- `http://localhost:8000` (API itself)
- `https://f1-agent-vdeg.onrender.com` (Production frontend)

In production, only the production frontend is allowed.

## Request Logging

All requests are automatically logged with:
- Request ID (added to `X-Request-ID` header)
- Method and path
- Client host
- Status code
- Duration in milliseconds

## Error Handling

The API includes comprehensive error handling:

- **500 Internal Server Error**: Unhandled exceptions
- **503 Service Unavailable**: Dependencies not initialized
- **404 Not Found**: Session or resource not found
- **422 Validation Error**: Invalid request data

All errors include a `request_id` for tracking.

## Session Management

Sessions are stored in-memory by default. For production, consider:
- Using Redis for distributed session storage
- Implementing session expiration
- Adding authentication/authorization

## Background Tasks

The `/api/admin/ingest` endpoint uses FastAPI's background tasks for long-running operations. Task status tracking can be implemented using:
- Redis for task state
- Celery for distributed task queue
- Database for persistent task history

## Development

### Running with Auto-reload

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Chat message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who is the current F1 champion?"}'

# Streaming chat
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Ferrari"}' \
  --no-buffer
```

## Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production` in `.env`
2. Set `API_RELOAD=false`
3. Use a production ASGI server (uvicorn with workers)
4. Set up proper secrets management
5. Configure monitoring and logging
6. Use Redis for session storage
7. Set up rate limiting
8. Enable HTTPS

Example production command:
```bash
uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Health     │  │     Chat     │  │    Admin     │      │
│  │   Routes     │  │    Routes    │  │   Routes     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Middleware Layer                         │   │
│  │  - CORS                                               │   │
│  │  - Request Logging                                    │   │
│  │  - Exception Handling                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ LangGraph   │  │  Pinecone   │  │   Tavily    │
│   Agent     │  │ Vector DB   │  │ Search API  │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Next Steps

- Implement authentication/authorization
- Add rate limiting per user/IP
- Set up Redis for session storage
- Add WebSocket support for real-time updates
- Implement task status tracking for ingestion
- Add metrics collection (Prometheus)
- Set up monitoring and alerting
- Add API versioning
