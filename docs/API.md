# Chat P1 API Documentation

Complete API reference for the Chat P1 Agent backend.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [Chat](#chat-endpoints)
  - [Health](#health-endpoints)
  - [Ingestion](#ingestion-endpoints)
  - [Statistics](#statistics-endpoints)
- [Request/Response Formats](#requestresponse-formats)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)
- [WebSocket Support](#websocket-support)

## Overview

The Chat P1 API provides programmatic access to the F1 expert chatbot system. It supports:

- **RESTful endpoints** for chat interactions
- **Streaming responses** for real-time feedback
- **Session management** for conversation context
- **Health monitoring** for system status
- **Data ingestion** for knowledge base updates

### API Version

Current version: `v1`

### Content Type

All requests and responses use `application/json` unless otherwise specified.

## Authentication

### API Key Authentication (Optional)

If authentication is enabled, include your API key in the request header:

```http
Authorization: Bearer YOUR_API_KEY
```

### Session-Based Authentication

For UI applications, session IDs are used to maintain conversation context:

```json
{
  "session_id": "user123"
}
```

## Base URL

### Local Development
```
http://localhost:8000
```

### Production
```
https://api.chatp1.com
```

### API Documentation
Interactive API documentation is available at:
- Swagger UI: `{BASE_URL}/docs`
- ReDoc: `{BASE_URL}/redoc`

## Rate Limiting

### Default Limits

- **Requests per minute**: 60
- **Requests per hour**: 1000
- **Concurrent requests**: 10

### Rate Limit Headers

Response headers include rate limit information:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

### Rate Limit Exceeded

When rate limit is exceeded, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again in 30 seconds.",
  "retry_after": 30
}
```

## Endpoints

### Chat Endpoints

#### POST /chat

Send a chat message and receive a response from the F1 expert agent.

**Request**

```http
POST /chat HTTP/1.1
Content-Type: application/json

{
  "message": "Who won the 2023 Monaco Grand Prix?",
  "session_id": "user123",
  "stream": false,
  "options": {
    "temperature": 0.7,
    "max_tokens": 1000,
    "include_sources": true
  }
}
```

**Request Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | User's chat message |
| `session_id` | string | Yes | Unique session identifier for conversation context |
| `stream` | boolean | No | Enable streaming response (default: false) |
| `options` | object | No | Additional options for response generation |
| `options.temperature` | float | No | LLM temperature (0.0-1.0, default: 0.7) |
| `options.max_tokens` | integer | No | Maximum response tokens (default: 1000) |
| `options.include_sources` | boolean | No | Include source citations (default: true) |

**Response (Non-Streaming)**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "response": "Max Verstappen won the 2023 Monaco Grand Prix, driving for Red Bull Racing...",
  "session_id": "user123",
  "sources": [
    {
      "title": "2023 Monaco Grand Prix Results",
      "url": "https://www.formula1.com/en/results/2023/races/monaco",
      "relevance_score": 0.95,
      "excerpt": "Max Verstappen claimed victory..."
    }
  ],
  "metadata": {
    "intent": "factual_query",
    "entities": {
      "race": "Monaco Grand Prix",
      "year": 2023
    },
    "retrieval_method": "hybrid",
    "response_time_ms": 1250,
    "tokens_used": 450
  }
}
```

**Response (Streaming)**

When `stream: true`, the response is sent as Server-Sent Events (SSE):

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type": "start", "session_id": "user123"}

data: {"type": "token", "content": "Max"}

data: {"type": "token", "content": " Verstappen"}

data: {"type": "token", "content": " won"}

data: {"type": "sources", "sources": [...]}

data: {"type": "end", "metadata": {...}}
```

**Error Response**

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_request",
  "message": "Message cannot be empty",
  "details": {
    "field": "message",
    "constraint": "min_length"
  }
}
```

#### GET /chat/history

Retrieve conversation history for a session.

**Request**

```http
GET /chat/history?session_id=user123&limit=10 HTTP/1.1
```

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session identifier |
| `limit` | integer | No | Maximum messages to return (default: 20) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "session_id": "user123",
  "messages": [
    {
      "role": "user",
      "content": "Who won the 2023 Monaco Grand Prix?",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Max Verstappen won the 2023 Monaco Grand Prix...",
      "timestamp": "2024-01-15T10:30:02Z",
      "sources": [...]
    }
  ],
  "total_messages": 2,
  "has_more": false
}
```

#### DELETE /chat/session

Clear conversation history for a session.

**Request**

```http
DELETE /chat/session?session_id=user123 HTTP/1.1
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message": "Session cleared successfully",
  "session_id": "user123"
}
```

### Health Endpoints

#### GET /health

Check the health status of the API and its dependencies.

**Request**

```http
GET /health HTTP/1.1
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "dependencies": {
    "openai": {
      "status": "healthy",
      "latency_ms": 150
    },
    "pinecone": {
      "status": "healthy",
      "latency_ms": 80,
      "index_stats": {
        "total_vectors": 15420,
        "dimension": 1536
      }
    },
    "tavily": {
      "status": "healthy",
      "latency_ms": 200
    }
  },
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "uptime_seconds": 86400
  }
}
```

**Unhealthy Response**

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "unhealthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "dependencies": {
    "openai": {
      "status": "healthy",
      "latency_ms": 150
    },
    "pinecone": {
      "status": "unhealthy",
      "error": "Connection timeout",
      "latency_ms": 5000
    },
    "tavily": {
      "status": "degraded",
      "error": "Rate limit exceeded",
      "latency_ms": 300
    }
  }
}
```

#### GET /health/ready

Check if the API is ready to accept requests (readiness probe).

**Request**

```http
GET /health/ready HTTP/1.1
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ready": true
}
```

#### GET /health/live

Check if the API is alive (liveness probe).

**Request**

```http
GET /health/live HTTP/1.1
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "alive": true
}
```

### Ingestion Endpoints

#### POST /ingest

Trigger data ingestion to update the knowledge base.

**Request**

```http
POST /ingest HTTP/1.1
Content-Type: application/json

{
  "source": "data/f1_knowledge/",
  "incremental": true,
  "batch_size": 100,
  "options": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "metadata_enrichment": true
  }
}
```

**Request Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | Path to data source directory |
| `incremental` | boolean | No | Only ingest new/updated documents (default: true) |
| `batch_size` | integer | No | Documents per batch (default: 100) |
| `options` | object | No | Ingestion options |

**Response**

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "job_id": "ingest_20240115_103000",
  "status": "processing",
  "message": "Ingestion job started",
  "estimated_duration_seconds": 300
}
```

#### GET /ingest/status

Check the status of an ingestion job.

**Request**

```http
GET /ingest/status?job_id=ingest_20240115_103000 HTTP/1.1
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "job_id": "ingest_20240115_103000",
  "status": "completed",
  "progress": {
    "total_documents": 1000,
    "processed_documents": 1000,
    "failed_documents": 5,
    "percent_complete": 100
  },
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z",
  "duration_seconds": 300,
  "results": {
    "documents_added": 850,
    "documents_updated": 145,
    "documents_skipped": 5,
    "errors": [
      {
        "document": "race_results_2024.csv",
        "error": "Invalid date format"
      }
    ]
  }
}
```

### Statistics Endpoints

#### GET /stats

Get vector store and system statistics.

**Request**

```http
GET /stats HTTP/1.1
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "vector_store": {
    "total_vectors": 15420,
    "dimension": 1536,
    "index_fullness": 0.15,
    "namespaces": {
      "default": 15420
    }
  },
  "usage": {
    "total_queries": 125430,
    "queries_today": 1250,
    "average_response_time_ms": 1200,
    "cache_hit_rate": 0.35
  },
  "costs": {
    "openai_tokens_used": 5420000,
    "estimated_cost_usd": 12.50
  }
}
```

#### GET /stats/queries

Get query statistics and analytics.

**Request**

```http
GET /stats/queries?period=7d HTTP/1.1
```

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `period` | string | No | Time period (1h, 24h, 7d, 30d, default: 24h) |

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "period": "7d",
  "total_queries": 8750,
  "unique_sessions": 450,
  "average_response_time_ms": 1200,
  "p95_response_time_ms": 2500,
  "p99_response_time_ms": 4000,
  "intent_distribution": {
    "factual_query": 5250,
    "prediction": 1750,
    "historical": 1250,
    "conversational": 500
  },
  "top_queries": [
    {
      "query": "current driver standings",
      "count": 125
    },
    {
      "query": "monaco grand prix results",
      "count": 98
    }
  ]
}
```

## Request/Response Formats

### Common Data Types

#### Message Object

```json
{
  "role": "user" | "assistant",
  "content": "string",
  "timestamp": "ISO 8601 datetime",
  "metadata": {
    "intent": "string",
    "entities": {},
    "sources": []
  }
}
```

#### Source Object

```json
{
  "title": "string",
  "url": "string",
  "relevance_score": 0.0-1.0,
  "excerpt": "string",
  "published_date": "ISO 8601 datetime",
  "source_type": "vector_store" | "tavily_search"
}
```

#### Error Object

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "string",
    "constraint": "string"
  },
  "request_id": "string"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async operation) |
| 400 | Bad Request (invalid input) |
| 401 | Unauthorized (missing/invalid auth) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 429 | Too Many Requests (rate limit) |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Error Handling

### Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `invalid_request` | Request validation failed | Check request parameters |
| `authentication_failed` | Invalid API key | Verify API key |
| `rate_limit_exceeded` | Too many requests | Wait and retry |
| `session_not_found` | Session ID not found | Create new session |
| `service_unavailable` | External service down | Check health endpoint |
| `internal_error` | Unexpected server error | Contact support |

### Error Response Format

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "details": {
    "additional": "context"
  },
  "request_id": "req_abc123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Retry Logic

For transient errors (500, 503), implement exponential backoff:

```python
import time
import requests

def make_request_with_retry(url, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [500, 503] and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
```

## Code Examples

### Python

#### Basic Chat Request

```python
import requests

BASE_URL = "http://localhost:8000"

def send_message(message, session_id):
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "message": message,
            "session_id": session_id,
            "stream": False
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
result = send_message(
    "Who won the 2023 championship?",
    "user123"
)
print(result["response"])
```

#### Streaming Chat Request

```python
import requests
import json

def send_streaming_message(message, session_id):
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "message": message,
            "session_id": session_id,
            "stream": True
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                if data['type'] == 'token':
                    print(data['content'], end='', flush=True)
                elif data['type'] == 'end':
                    print()
                    return data['metadata']

# Usage
metadata = send_streaming_message(
    "Predict the next race outcome",
    "user123"
)
```

#### Using the Python SDK

```python
from src.agent.graph import F1AgentGraph
from src.config.settings import Settings

# Initialize
config = Settings()
agent = F1AgentGraph(config)

# Send query
async def chat():
    response = await agent.process_query(
        query="What are the current driver standings?",
        session_id="user123"
    )
    print(response["response"])
    
    # Access sources
    for source in response["sources"]:
        print(f"- {source['title']}: {source['url']}")

# Run
import asyncio
asyncio.run(chat())
```

### JavaScript/TypeScript

```typescript
// Basic chat request
async function sendMessage(message: string, sessionId: string) {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      stream: false,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// Usage
const result = await sendMessage(
  'Who won the 2023 championship?',
  'user123'
);
console.log(result.response);
```

### cURL

```bash
# Basic chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Who won the 2023 championship?",
    "session_id": "user123",
    "stream": false
  }'

# Health check
curl http://localhost:8000/health

# Get conversation history
curl "http://localhost:8000/chat/history?session_id=user123&limit=10"

# Clear session
curl -X DELETE "http://localhost:8000/chat/session?session_id=user123"
```

## WebSocket Support

### Coming Soon

WebSocket support for real-time bidirectional communication is planned for a future release.

**Planned Features**:
- Real-time message streaming
- Live race updates
- Push notifications for new F1 news
- Multi-user chat rooms

## Best Practices

### Session Management

- Use consistent session IDs for conversation continuity
- Clear sessions when conversations end
- Implement session timeout on client side (30 minutes recommended)

### Error Handling

- Always check HTTP status codes
- Implement retry logic for transient errors
- Log error details for debugging
- Display user-friendly error messages

### Performance

- Use streaming for better perceived performance
- Cache responses when appropriate
- Implement request debouncing for user input
- Monitor response times and adjust timeouts

### Security

- Never expose API keys in client-side code
- Use HTTPS in production
- Implement rate limiting on client side
- Validate and sanitize user input

## Changelog

### v0.1.0 (2024-01-15)

- Initial API release
- Chat endpoints with streaming support
- Health monitoring endpoints
- Data ingestion endpoints
- Statistics and analytics endpoints

## Support

For API support:
- **Documentation**: https://docs.chatp1.com
- **Issues**: https://github.com/chatp1/agent/issues
- **Email**: api-support@chatp1.com

---

**Last Updated**: January 15, 2024
