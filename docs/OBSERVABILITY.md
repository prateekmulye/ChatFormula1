# Observability & Monitoring

This document describes the observability and monitoring features implemented in Chat P1.

## Overview

Chat P1 includes comprehensive observability features:

- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Performance Timing**: Track operation latency with detailed checkpoints
- **Metrics Collection**: Track latency, token usage, API calls, and user satisfaction
- **Monitoring Dashboards**: Visualize metrics and system health
- **Prometheus Export**: Export metrics for external monitoring systems

## Structured Logging

### Features

- JSON-formatted logs for production
- Pretty console output for development
- Request ID correlation across all logs
- Session ID tracking for conversation context
- Automatic timestamp and log level inclusion

### Usage

```python
from src.config.logging import get_logger, set_request_id, set_session_id

logger = get_logger(__name__)

# Set correlation IDs
set_request_id("req-12345")
set_session_id("session-abc")

# Log with structured data
logger.info(
    "user_query_received",
    query="Who won the championship?",
    user_id="user-123",
)
```

### Log Output

Development (pretty console):
```
2024-01-15 10:30:45 [info     ] user_query_received    app=chatp1 query=Who won the championship? request_id=req-12345 session_id=session-abc user_id=user-123
```

Production (JSON):
```json
{
  "event": "user_query_received",
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "info",
  "logger": "src.api.routes.chat",
  "app": "chatp1",
  "request_id": "req-12345",
  "session_id": "session-abc",
  "query": "Who won the championship?",
  "user_id": "user-123"
}
```

## Performance Timing

### Simple Timing with Context Manager

```python
from src.utils.timing import log_performance

async def search_vector_store(query: str):
    with log_performance("vector_search", query=query):
        results = await vector_store.search(query)
    return results
```

### Detailed Timing with Checkpoints

```python
from src.utils.timing import PerformanceTimer

async def rag_pipeline(query: str):
    timer = PerformanceTimer("rag_pipeline", query=query)
    
    # Analyze query
    timer.checkpoint("query_analysis")
    intent = await analyze_query(query)
    
    # Search vector store
    timer.checkpoint("vector_search", docs_retrieved=5)
    docs = await vector_store.search(query)
    
    # Search Tavily
    timer.checkpoint("tavily_search", results_found=3)
    search_results = await tavily.search(query)
    
    # Generate response
    timer.checkpoint("llm_generation", tokens=150)
    response = await llm.generate(query, docs, search_results)
    
    # Finish timing
    total_time = timer.finish(success=True)
    
    return response
```

## Metrics Collection

### Recording Metrics

```python
from src.utils.metrics import get_metrics_collector

metrics = get_metrics_collector()

# Record latency
metrics.record_latency(
    operation="vector_search",
    duration_ms=150.5,
    success=True,
    docs_retrieved=5,
)

# Record token usage
metrics.record_token_usage(
    model="gpt-4-turbo",
    prompt_tokens=100,
    completion_tokens=50,
    operation="chat_response",
)

# Record API call
metrics.record_api_call(
    service="openai",
    success=True,
)

# Record user feedback
metrics.record_user_feedback(
    session_id="session-abc",
    message_id="msg-1",
    rating=5,  # 1 or 5
    feedback_text="Great answer!",
)
```

### Retrieving Metrics

```python
# Get latency statistics
latency_stats = metrics.get_latency_stats()
# Returns: {count, min_ms, max_ms, mean_ms, p50_ms, p95_ms, p99_ms, success_rate}

# Get latency for specific operation
vector_stats = metrics.get_latency_stats(operation="vector_search")

# Get token usage statistics
token_stats = metrics.get_token_usage_stats()
# Returns: {total_requests, total_tokens, total_cost_usd, by_model}

# Get API success rates
api_stats = metrics.get_api_success_rates()
# Returns: {service: {total_calls, successful, failed, success_rate}}

# Get user satisfaction
satisfaction = metrics.get_user_satisfaction_stats()
# Returns: {total_feedback, positive, negative, satisfaction_rate}

# Get all metrics
all_metrics = metrics.get_all_metrics()
```

## Monitoring Dashboards

### Dashboard Endpoints

The following dashboard endpoints are available:

- `GET /api/admin/dashboard/summary` - High-level overview
- `GET /api/admin/dashboard/latency` - Latency metrics with charts
- `GET /api/admin/dashboard/cost` - Cost tracking with projections
- `GET /api/admin/dashboard/api-health` - API health and success rates
- `GET /api/admin/dashboard/satisfaction` - User satisfaction with insights
- `GET /api/admin/dashboard/errors` - Error rate visualization

### Using Dashboards

```python
from src.utils.dashboard import get_monitoring_dashboard

dashboard = get_monitoring_dashboard()

# Get summary
summary = dashboard.get_dashboard_summary()
print(f"Health status: {summary['health_status']}")
print(f"Total operations: {summary['overview']['total_operations']}")
print(f"Avg latency: {summary['overview']['avg_latency_ms']}ms")

# Get latency dashboard
latency_dashboard = dashboard.get_latency_dashboard()
# Includes overall stats, by-operation breakdown, and chart data

# Get cost dashboard
cost_dashboard = dashboard.get_cost_dashboard()
# Includes cost summary, by-model breakdown, and projections
```

### Dashboard Data Format

```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "overview": {
    "total_operations": 1234,
    "avg_latency_ms": 250.5,
    "p95_latency_ms": 450.0,
    "api_success_rate": 0.9850,
    "total_cost_usd": 2.45,
    "user_satisfaction_rate": 0.85
  },
  "health_status": "healthy"
}
```

## Prometheus Metrics Export

### Accessing Prometheus Metrics

```bash
curl http://localhost:8000/api/admin/metrics/prometheus
```

### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'chatp1'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/admin/metrics/prometheus'
```

### Available Metrics

- `f1_slipstream_info` - Application information (gauge)
- `f1_slipstream_latency_seconds` - Operation latency (summary)
- `f1_slipstream_api_calls_total` - API calls by service and status (counter)
- `f1_slipstream_api_success_rate` - API success rate by service (gauge)
- `f1_slipstream_tokens_total` - Total tokens used (counter)
- `f1_slipstream_cost_usd_total` - Total estimated cost (counter)
- `f1_slipstream_user_feedback_total` - User feedback by rating (counter)
- `f1_slipstream_satisfaction_rate` - User satisfaction rate (gauge)
- `f1_slipstream_operations_total` - Operations by type (counter)

### Grafana Dashboard

Import the metrics into Grafana for visualization:

1. Add Prometheus as a data source
2. Create dashboards with panels for:
   - Latency percentiles (P50, P95, P99)
   - API success rates by service
   - Token usage and cost over time
   - User satisfaction trends
   - Error rates by category

## API Endpoints

### Metrics Endpoints

- `GET /api/admin/metrics` - Get all metrics in JSON format
- `GET /api/admin/metrics/prometheus` - Get metrics in Prometheus format
- `POST /api/admin/metrics/reset` - Reset all metrics (use with caution)

### Feedback Endpoint

- `POST /api/admin/feedback` - Submit user feedback
  ```json
  {
    "session_id": "session-abc",
    "message_id": "msg-1",
    "rating": 5,
    "feedback_text": "Great answer!"
  }
  ```

### Health Check

- `GET /api/admin/health` - Detailed health check with dependency status

## Best Practices

### 1. Use Correlation IDs

Always set request and session IDs for request tracing:

```python
from src.config.logging import set_request_id, set_session_id

set_request_id(request_id)
set_session_id(session_id)
```

### 2. Record Metrics Consistently

Record metrics for all important operations:

```python
metrics = get_metrics_collector()

# Before operation
start_time = time.time()

try:
    result = await operation()
    success = True
except Exception as e:
    success = False
    raise
finally:
    duration_ms = (time.time() - start_time) * 1000
    metrics.record_latency("operation_name", duration_ms, success)
```

### 3. Use Performance Timers

Use `PerformanceTimer` for complex operations with multiple steps:

```python
timer = PerformanceTimer("operation_name")
timer.checkpoint("step1")
# ... do work ...
timer.checkpoint("step2")
# ... do work ...
timer.finish(success=True)
```

### 4. Monitor Health Status

Regularly check the dashboard summary for health status:

```python
summary = dashboard.get_dashboard_summary()
if summary['health_status'] != 'healthy':
    logger.warning("system_health_degraded", status=summary['health_status'])
```

### 5. Set Up Alerts

Configure alerts based on metrics:

- Latency P95 > 3000ms
- API success rate < 95%
- User satisfaction rate < 70%
- Error rate > 5%

## Troubleshooting

### High Latency

1. Check latency dashboard: `/api/admin/dashboard/latency`
2. Identify slow operations in by-operation breakdown
3. Review logs for specific request IDs
4. Check external API health

### Low API Success Rate

1. Check API health dashboard: `/api/admin/dashboard/api-health`
2. Identify failing services
3. Review error logs for specific failures
4. Check API key validity and rate limits

### High Costs

1. Check cost dashboard: `/api/admin/dashboard/cost`
2. Review token usage by model
3. Optimize prompts to reduce token usage
4. Consider using cheaper models for simple queries

### Low User Satisfaction

1. Check satisfaction dashboard: `/api/admin/dashboard/satisfaction`
2. Review negative feedback text
3. Analyze common patterns in low-rated responses
4. Improve prompts and retrieval quality

## Example

See `examples/observability_example.py` for a complete example demonstrating all observability features.

Run the example:

```bash
cd apps/chatp1-agent
poetry run python examples/observability_example.py
```

## Integration with External Systems

### Datadog

```python
# Send metrics to Datadog
from datadog import statsd

metrics = get_metrics_collector()
stats = metrics.get_latency_stats()

statsd.gauge('f1_slipstream.latency.p95', stats['p95_ms'])
statsd.gauge('f1_slipstream.latency.mean', stats['mean_ms'])
```

### CloudWatch

```python
# Send metrics to CloudWatch
import boto3

cloudwatch = boto3.client('cloudwatch')
metrics = get_metrics_collector()
stats = metrics.get_latency_stats()

cloudwatch.put_metric_data(
    Namespace='F1Slipstream',
    MetricData=[
        {
            'MetricName': 'Latency',
            'Value': stats['mean_ms'],
            'Unit': 'Milliseconds',
        },
    ]
)
```

## Future Enhancements

- Real-time metrics streaming via WebSocket
- Custom metric aggregation windows
- Anomaly detection and alerting
- Distributed tracing with OpenTelemetry
- Log aggregation with ELK stack
- Custom dashboard builder UI
