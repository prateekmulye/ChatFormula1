# Utility Modules

This directory contains utility modules for error handling, resilience, and monitoring.

## Modules

### retry.py - Retry Logic with Exponential Backoff

Provides retry decorators with exponential backoff and circuit breaker pattern for resilient API calls.

#### Features

- Exponential backoff with configurable parameters
- Circuit breaker pattern to prevent cascading failures
- Service-specific retry configurations
- Comprehensive logging of retry attempts

#### Usage

```python
from src.utils import retry_with_backoff, OPENAI_RETRY_CONFIG

# Basic retry with default settings
@retry_with_backoff(max_attempts=3)
async def fetch_data():
    # API call that might fail
    pass

# Retry with circuit breaker
@retry_with_backoff(
    max_attempts=3,
    exceptions=(ConnectionError, TimeoutError),
    service_name="openai",
    use_circuit_breaker=True
)
async def call_openai_api():
    # OpenAI API call
    pass

# Use predefined service configurations
@retry_with_backoff(**OPENAI_RETRY_CONFIG, exceptions=(LLMError,))
async def generate_response(prompt: str):
    # LLM generation
    pass
```

#### Circuit Breaker

The circuit breaker monitors failures and opens the circuit after a threshold is reached:

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests are rejected immediately
- **HALF_OPEN**: Testing if service has recovered

```python
from src.utils import get_circuit_breaker, CircuitState

# Get circuit breaker for a service
cb = get_circuit_breaker("tavily")

# Check circuit state
if cb.state == CircuitState.OPEN:
    print("Service is unavailable")
```

### fallback.py - Fallback Mechanisms

Provides fallback chains for graceful degradation when services are unavailable.

#### Features

- Fallback chain with multiple alternatives
- Response caching for resilience
- Service mode tracking (FULL, DEGRADED, MINIMAL)
- User-friendly degraded mode messages

#### Usage

```python
from src.utils import (
    tavily_search_with_fallback,
    vector_search_with_fallback,
    get_degraded_mode_message,
    ServiceMode
)

# Tavily search with vector store fallback
async def search_f1_data(query: str):
    results, mode = await tavily_search_with_fallback(
        search_fn=tavily_client.search,
        vector_search_fn=vector_store.search,
        query=query
    )

    # Show degraded mode message to user if needed
    if mode != ServiceMode.FULL:
        message = get_degraded_mode_message(mode, "tavily")
        print(message)

    return results

# Vector search with cache fallback
async def query_history(query: str):
    results, mode = await vector_search_with_fallback(
        vector_search_fn=vector_store.search,
        query=query
    )
    return results
```

#### Custom Fallback Chain

```python
from src.utils import FallbackChain

async def primary_function(query: str):
    # Primary implementation
    pass

async def fallback_1(query: str):
    # First fallback
    pass

async def fallback_2(query: str):
    # Second fallback
    pass

chain = FallbackChain(
    primary=primary_function,
    fallbacks=[fallback_1, fallback_2],
    cache_key_fn=lambda query: f"custom:{query}",
    use_cache=True
)

result, mode = await chain.execute("my query")
```

#### Response Cache

```python
from src.utils import get_response_cache

cache = get_response_cache()

# Manual cache operations
cache.set("key", {"data": "value"}, ttl=300)
cached_data = cache.get("key")

# Cleanup expired entries
removed_count = cache.cleanup_expired()
```

### error_tracking.py - Comprehensive Error Logging

Provides structured error logging with categorization, aggregation, and alerting.

#### Features

- Automatic error categorization
- Severity determination
- Error metrics and aggregation
- Alert threshold monitoring
- Error rate tracking

#### Usage

```python
from src.utils import log_error_with_context, get_error_metrics

# Log error with context
try:
    # Some operation
    pass
except Exception as e:
    log_error_with_context(
        error=e,
        context={
            "user_id": "123",
            "query": "race predictions",
            "function": "predict_race"
        },
        include_traceback=True
    )

# Get error metrics
metrics = get_error_metrics()
total_errors = metrics.get_error_count()
error_rate = metrics.get_error_rate(window_minutes=5)
recent_errors = metrics.get_recent_errors(limit=10)

# Get error summary for monitoring
from src.utils import create_error_summary, log_error_summary

summary = create_error_summary()
print(f"Total errors: {summary['total_errors']}")
print(f"Error rate: {summary['error_rate_5min']} errors/min")

# Log summary periodically
log_error_summary()
```

#### Error Categories

- `CONFIGURATION`: Configuration errors
- `AUTHENTICATION`: Authentication failures
- `RATE_LIMIT`: Rate limit exceeded
- `TIMEOUT`: Timeout errors
- `NETWORK`: Network connectivity issues
- `VALIDATION`: Data validation failures
- `DATA`: Data processing errors
- `AGENT`: Agent execution errors
- `LLM`: LLM API errors
- `VECTOR_STORE`: Vector store errors
- `SEARCH_API`: Search API errors
- `UNKNOWN`: Uncategorized errors

#### Error Severity

- `CRITICAL`: Requires immediate attention (configuration, authentication)
- `ERROR`: High priority (LLM, agent errors)
- `WARNING`: Medium priority (rate limits, timeouts)
- `INFO`: Lower priority (validation, data errors)
- `DEBUG`: Debug information

#### Alert Thresholds

Automatic alerts are triggered when:

- Any critical error occurs
- Error rate exceeds 10 errors/minute
- More than 5 rate limit errors in 5 minutes
- More than 3 LLM errors in 5 minutes
- More than 3 vector store errors in 5 minutes

## Complete Example

Here's a complete example combining all error handling features:

```python
from src.utils import (
    retry_with_backoff,
    TAVILY_RETRY_CONFIG,
    tavily_search_with_fallback,
    log_error_with_context,
    get_degraded_mode_message,
    ServiceMode
)
from src.exceptions import SearchAPIError

class F1SearchService:
    def __init__(self, tavily_client, vector_store):
        self.tavily_client = tavily_client
        self.vector_store = vector_store

    @retry_with_backoff(**TAVILY_RETRY_CONFIG, exceptions=(SearchAPIError,))
    async def _tavily_search(self, query: str):
        """Tavily search with retry logic."""
        return await self.tavily_client.search(query)

    async def _vector_search(self, query: str):
        """Vector store search."""
        return await self.vector_store.search(query)

    async def search(self, query: str, user_id: str = None):
        """Search with full error handling and fallbacks."""
        try:
            # Execute search with fallback chain
            results, mode = await tavily_search_with_fallback(
                search_fn=self._tavily_search,
                vector_search_fn=self._vector_search,
                query=query
            )

            # Prepare response with degraded mode message
            response = {
                "results": results,
                "mode": mode.value,
            }

            if mode != ServiceMode.FULL:
                response["message"] = get_degraded_mode_message(mode, "tavily")

            return response

        except Exception as e:
            # Log error with comprehensive context
            log_error_with_context(
                error=e,
                context={
                    "user_id": user_id,
                    "query": query,
                    "service": "search",
                    "function": "search"
                },
                include_traceback=True
            )

            # Re-raise or return error response
            raise

# Usage
service = F1SearchService(tavily_client, vector_store)
result = await service.search("latest F1 standings", user_id="user123")

if result.get("message"):
    print(f"Note: {result['message']}")

print(result["results"])
```

## Service-Specific Configurations

### OpenAI Configuration

```python
OPENAI_RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2,
    "service_name": "openai",
    "use_circuit_breaker": True,
}
```

### Pinecone Configuration

```python
PINECONE_RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay": 0.5,
    "max_delay": 30.0,
    "exponential_base": 2,
    "service_name": "pinecone",
    "use_circuit_breaker": True,
}
```

### Tavily Configuration

```python
TAVILY_RETRY_CONFIG = {
    "max_attempts": 2,
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "exponential_base": 2,
    "service_name": "tavily",
    "use_circuit_breaker": True,
}
```

## Monitoring and Observability

### Periodic Error Summary

Set up periodic error summary logging:

```python
import asyncio
from src.utils import log_error_summary

async def periodic_error_summary():
    """Log error summary every 5 minutes."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        log_error_summary()

# Start background task
asyncio.create_task(periodic_error_summary())
```

### Health Check Endpoint

Include error metrics in health check:

```python
from fastapi import FastAPI
from src.utils import create_error_summary

app = FastAPI()

@app.get("/health")
async def health_check():
    error_summary = create_error_summary()

    return {
        "status": "healthy" if error_summary["error_rate_5min"] < 5 else "degraded",
        "errors": error_summary
    }
```

## Best Practices

1. **Use service-specific configurations**: Apply appropriate retry configs for each service
2. **Enable circuit breakers**: Prevent cascading failures with circuit breaker pattern
3. **Implement fallback chains**: Always have a fallback strategy for critical operations
4. **Log with context**: Include relevant context when logging errors
5. **Monitor error rates**: Set up alerts for high error rates
6. **Cache responses**: Use response caching for resilience
7. **Show degraded mode messages**: Inform users when services are degraded
8. **Track metrics**: Monitor error metrics for system health

## Testing

Test error handling with simulated failures:

```python
import pytest
from src.utils import retry_with_backoff, get_circuit_breaker

@pytest.mark.asyncio
async def test_retry_with_backoff():
    call_count = 0

    @retry_with_backoff(max_attempts=3, initial_delay=0.1)
    async def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Simulated failure")
        return "success"

    result = await failing_function()
    assert result == "success"
    assert call_count == 3

@pytest.mark.asyncio
async def test_circuit_breaker():
    cb = get_circuit_breaker("test_service")

    async def failing_function():
        raise ConnectionError("Simulated failure")

    # Trigger circuit breaker
    for _ in range(5):
        try:
            await cb.call_async(failing_function)
        except:
            pass

    # Circuit should be open
    from src.utils import CircuitState
    assert cb.state == CircuitState.OPEN
```
