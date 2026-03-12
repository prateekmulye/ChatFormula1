## 2026-03-12 - Fix Rate Limiter IP Spoofing Vulnerability
**Vulnerability:** The application blindly trusted the `X-Forwarded-For` header by taking the first IP address, allowing attackers to bypass IP-based rate limiting via header spoofing.
**Learning:** Even when behind a reverse proxy, parsing `X-Forwarded-For` requires explicit trust. Attackers can inject a spoofed IP at the start of the chain (e.g. `X-Forwarded-For: <spoofed_ip>, <real_ip>`), making the application rate limit the fake IP instead of their real IP.
**Prevention:** Introduce a `trusted_proxies` configuration. When processing `X-Forwarded-For`, parse the chain from right to left, skipping known trusted proxies until encountering the first untrusted IP, which represents the true origin.
