## 2026-04-16 - Missing authentication on admin endpoints
**Vulnerability:** Admin routes in `src/api/routes/admin.py` lack direct API key authentication, relying instead on a global `AuthenticationMiddleware` which can be bypassed if `require_auth` is false or for specific prefixes.
**Learning:** Relying solely on global middleware for securing sensitive administrative endpoints provides insufficient defense in depth, especially when the middleware is configurable.
**Prevention:** Always inject explicit route-level dependencies like `Security(verify_api_key)` when initializing the `APIRouter` for sensitive endpoint groups to ensure they remain secured regardless of global middleware configuration.
