## 2025-02-18 - Fix Rate Limiter IP Spoofing
**Vulnerability:** Rate limiter used `X-Forwarded-For` header to determine client IP without verifying if the request actually came from a trusted proxy.
**Learning:** This allowed any client to spoof their IP address and bypass rate limits entirely by sending random `X-Forwarded-For` values.
**Prevention:** Always validate that the immediate upstream connection (client.host) is a known trusted proxy before trusting the `X-Forwarded-For` header. Introduce a `trusted_proxies` configuration to manage this list securely, defaulting to empty.