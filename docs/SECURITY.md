# Security Documentation

This document describes the security features implemented in Chat P1 and how to use them.

## Overview

Chat P1 implements multiple layers of security to protect against common vulnerabilities and ensure safe operation:

1. **Input Validation and Sanitization** - Prevents prompt injection and XSS attacks
2. **Rate Limiting** - Prevents abuse and ensures fair usage
3. **API Key Authentication** - Controls access to the API
4. **Request Signing** - Ensures request integrity for sensitive operations
5. **CORS Policies** - Controls cross-origin access

## Input Validation and Sanitization

### Features

- **Length Limits**: Queries are limited to 2000 characters by default
- **Prompt Injection Detection**: Detects and blocks common prompt injection patterns
- **Code Injection Prevention**: Blocks potentially malicious code patterns
- **HTML Sanitization**: Removes HTML tags and scripts
- **Control Character Removal**: Strips control characters except newlines and tabs
- **Whitespace Normalization**: Normalizes excessive whitespace

### Configuration

```python
# In .env file
ENABLE_INPUT_VALIDATION=true
STRICT_INPUT_VALIDATION=false  # Set to true for stricter validation
MAX_QUERY_LENGTH=2000
```

### Usage

Input validation is automatically applied to all chat endpoints. You can also use it programmatically:

```python
from src.security import validate_query, sanitize_query

# Validate input
result = validate_query("User input here", strict_mode=False)
if result.valid:
    sanitized_input = result.sanitized_input
else:
    print(f"Validation errors: {result.errors}")

# Or just sanitize
sanitized = sanitize_query("User input here")
```

### Detected Patterns

The validator detects the following suspicious patterns:

- Attempts to override system instructions
- Role-playing or persona changes
- Special tokens (e.g., `<|im_start|>`, `<|im_end|>`)
- JavaScript and HTML injection
- Python code execution attempts

## Rate Limiting

### Features

- **Token Bucket Algorithm**: Smooth rate limiting with burst support
- **Per-Client Limits**: Separate limits for each IP address or API key
- **Multiple Time Windows**: Both per-minute and per-hour limits
- **Graceful Degradation**: Returns 429 status with Retry-After header

### Configuration

```python
# In .env file
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

### Default Limits

- **Per Minute**: 60 requests (with burst up to 60)
- **Per Hour**: 1000 requests

### Response Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit-Minute: 60
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Hour: 892
```

### Checking Rate Limit Status

```bash
curl http://localhost:8000/api/chat/rate-limit
```

Response:
```json
{
  "enabled": true,
  "client_id": "ip:127.0.0.1",
  "limits": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "burst_size": 60
  },
  "remaining": {
    "minute": 45,
    "hour": 892
  }
}
```

## API Key Authentication

### Overview

API keys provide a way to authenticate and authorize API access. Each key can have:

- Custom rate limits (multiplier)
- Specific scopes/permissions
- Expiration dates
- Active/inactive status

### Configuration

```python
# In .env file
REQUIRE_API_KEY=false  # Set to true to require API keys for all endpoints
API_KEY_HEADER_NAME=X-API-Key
```

### Creating API Keys

```bash
# Create a new API key
curl -X POST http://localhost:8000/api/admin/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Application",
    "scopes": ["chat", "admin"],
    "expires_in_days": 90,
    "rate_limit_multiplier": 2.0
  }'
```

Response:
```json
{
  "key_id": "abc123",
  "key": "f1s_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "name": "My Application",
  "created_at": "2024-01-01T00:00:00",
  "expires_at": "2024-04-01T00:00:00",
  "is_active": true,
  "scopes": ["chat", "admin"]
}
```

**Important**: The raw API key is only shown once. Store it securely!

### Using API Keys

Include the API key in the `X-API-Key` header:

```bash
curl http://localhost:8000/api/chat \
  -H "X-API-Key: f1s_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"message": "Who won the last race?"}'
```

### Managing API Keys

#### List All Keys

```bash
curl http://localhost:8000/api/admin/api-keys
```

#### Revoke a Key

```bash
curl -X DELETE http://localhost:8000/api/admin/api-keys/{key_id}
```

#### Rotate a Key

```bash
curl -X POST http://localhost:8000/api/admin/api-keys/{key_id}/rotate
```

This generates a new key with the same settings and revokes the old one.

### Scopes

Scopes control what operations an API key can perform:

- `chat`: Access to chat endpoints
- `admin`: Access to admin endpoints
- `ingest`: Access to data ingestion
- `*`: All scopes (wildcard)

To require a specific scope in your endpoint:

```python
from src.security import require_scope

@router.post("/sensitive-operation")
async def sensitive_operation(
    api_key: APIKey = Depends(require_scope("admin"))
):
    # Only API keys with "admin" scope can access this
    pass
```

## Request Signing

For highly sensitive operations, request signing ensures that requests haven't been tampered with.

### Configuration

Request signing requires a secret key. Set it in your environment:

```python
# In .env file
REQUEST_SIGNING_SECRET=your-secret-key-here
```

### Signing Requests

```python
from src.security.request_signing import get_request_signer

signer = get_request_signer(secret_key="your-secret-key")

# Sign a request
signature = signer.sign_request(
    method="POST",
    path="/api/admin/sensitive",
    body='{"data": "value"}',
)

# Include signature in X-Signature header
```

### Requiring Signed Requests

```python
from src.security.request_signing import require_signed_request

@router.post("/sensitive-operation")
async def sensitive_operation(
    _: None = Depends(require_signed_request())
):
    # Request signature is verified before this runs
    pass
```

## CORS Configuration

### Configuration

```python
# In .env file
ENABLE_CORS=true
CORS_ALLOW_ORIGINS=["http://localhost:3000", "http://localhost:8501"]
```

### Default Allowed Origins

- Development: `localhost:3000`, `localhost:8501`, `localhost:8000`
- Production: Only explicitly configured origins

### Exposed Headers

The following headers are exposed to clients:

- `X-Request-ID`
- `X-RateLimit-Limit-Minute`
- `X-RateLimit-Remaining-Minute`
- `X-RateLimit-Limit-Hour`
- `X-RateLimit-Remaining-Hour`

## Security Best Practices

### For Developers

1. **Never commit API keys or secrets** to version control
2. **Use environment variables** for all sensitive configuration
3. **Enable strict validation** in production environments
4. **Rotate API keys regularly** (every 90 days recommended)
5. **Monitor rate limit violations** for potential abuse
6. **Use HTTPS** in production (never HTTP)
7. **Implement request signing** for sensitive operations
8. **Review logs regularly** for security events

### For Deployment

1. **Set `REQUIRE_API_KEY=true`** in production
2. **Enable `STRICT_INPUT_VALIDATION=true`** in production
3. **Configure appropriate rate limits** based on expected traffic
4. **Use a secrets manager** (AWS Secrets Manager, HashiCorp Vault, etc.)
5. **Enable CORS** only for trusted origins
6. **Set up monitoring and alerting** for security events
7. **Keep dependencies updated** to patch vulnerabilities
8. **Use a WAF** (Web Application Firewall) if available

### For API Consumers

1. **Store API keys securely** (use environment variables, not hardcoded)
2. **Implement exponential backoff** when rate limited
3. **Handle 401/403 errors** gracefully
4. **Don't share API keys** between applications
5. **Rotate keys** if compromised
6. **Monitor your usage** to stay within limits

## Security Headers

The API includes the following security headers:

- `X-Request-ID`: Unique request identifier for tracking
- `X-RateLimit-*`: Rate limit information
- `Retry-After`: Time to wait when rate limited (429 responses)

## Vulnerability Reporting

If you discover a security vulnerability, please email security@chatp1.com (or your configured security contact) with:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

**Do not** open public issues for security vulnerabilities.

## Compliance

Chat P1 implements security controls to help with:

- **OWASP Top 10** protection
- **Input validation** (A03:2021 - Injection)
- **Rate limiting** (A04:2021 - Insecure Design)
- **Authentication** (A07:2021 - Identification and Authentication Failures)
- **Logging** (A09:2021 - Security Logging and Monitoring Failures)

## Testing Security

### Test Input Validation

```bash
# Should be rejected
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Ignore all previous instructions and..."}'
```

### Test Rate Limiting

```bash
# Send many requests quickly
for i in {1..100}; do
  curl http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "test"}' &
done
```

### Test API Key Authentication

```bash
# Without API key (should fail if REQUIRE_API_KEY=true)
curl http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# With invalid API key (should fail)
curl http://localhost:8000/api/chat \
  -H "X-API-Key: invalid-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

## Monitoring

Monitor these metrics for security:

- Rate limit violations (429 responses)
- Authentication failures (401 responses)
- Input validation failures (400 responses with validation errors)
- Suspicious patterns detected in logs
- API key usage patterns

Use the metrics endpoints:

```bash
# Get all metrics
curl http://localhost:8000/api/admin/metrics

# Get Prometheus format
curl http://localhost:8000/api/admin/metrics/prometheus
```

## Updates

This security documentation is current as of the implementation date. Check the repository for updates and new security features.
