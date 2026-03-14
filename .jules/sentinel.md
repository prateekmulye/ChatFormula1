## 2025-03-14 - Prevent IP Spoofing via X-Forwarded-For Bypass
**Vulnerability:** The `RateLimiter` component trusted the first element of the `X-Forwarded-For` HTTP header by default, allowing arbitrary attackers to spoof their IP address and completely bypass API rate limits.
**Learning:** Naively trusting client-supplied headers without validating them against a trusted proxy configuration leads to easily exploitable security bypasses, especially in edge networking scenarios.
**Prevention:** Implement a `trusted_proxies` configuration array and traverse the `X-Forwarded-For` chain from right-to-left, dropping known-trusted proxy IPs until the first untrusted client IP is identified.
