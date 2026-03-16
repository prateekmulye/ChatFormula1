## 2025-03-16 - Prevent Rate Limit Bypass via IP Spoofing
**Vulnerability:** The rate limiter parsed `X-Forwarded-For` by taking the first IP (leftmost), which can be spoofed by a malicious client.
**Learning:** `X-Forwarded-For` chains are built by appending IPs. Untrusted clients can send a spoofed header, causing the real client IP to appear later in the chain, bypassing rate limits.
**Prevention:** Parse `X-Forwarded-For` from right to left, skipping trusted proxy IPs until the first untrusted IP is found, ensuring the real client IP is used.
