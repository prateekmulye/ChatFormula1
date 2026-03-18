## 2024-05-18 - Rate Limiter IP Spoofing via X-Forwarded-For

**Vulnerability:** The RateLimiter blindly trusted the first IP address in the `X-Forwarded-For` chain.
**Learning:** This allowed trivial rate limit bypass via IP Spoofing. Because it lacked a trusted proxies list, an attacker could supply a fake IP address in the `X-Forwarded-For` header.
**Prevention:** We added a `trusted_proxies` setting in `src/config/settings.py` (parsed as string lists) and modified the parser to iterate the `X-Forwarded-For` chain from right to left, skipping IPs present in the trusted proxies configuration until it found the true untrusted client IP.
