# Sentinel Journal

## 2024-10-27 - Missing Route-Level Authentication on Admin Endpoints
**Vulnerability:** Admin endpoints including API key generation, metrics reset, and configuration validation were accessible without authentication because they relied on a global middleware that was either absent or toggled off.
**Learning:** Relying solely on global `AuthenticationMiddleware` to protect sensitive endpoints is fragile and can easily be bypassed if `require_auth` is false or the prefix configuration is wrong.
**Prevention:** Always inject explicit route-level dependencies like `Security(verify_api_key)` directly onto the `APIRouter` initialization to comprehensively secure all endpoints within it for defense in depth.