## 2026-03-15 - IP Spoofing in Rate Limiting
**Vulnerability:** The rate limiter blindly trusted the first IP in the `X-Forwarded-For` chain.
**Learning:** This allows malicious users to spoof their IP by setting their own `X-Forwarded-For` header, bypassing rate limits.
**Prevention:** Parse the `X-Forwarded-For` chain from right to left, skipping trusted proxy IPs until the true untrusted client IP is found.
