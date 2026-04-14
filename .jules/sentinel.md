## 2024-05-14 - Missing Route-Level Authentication on Admin Endpoints
**Vulnerability:** The admin router in `src/api/routes/admin.py` was not protected by a security dependency, allowing unauthenticated access to sensitive administrative endpoints (like `/stats` and `/ingest`).
**Learning:** Relying solely on global middleware (like `AuthenticationMiddleware`) can be insufficient for defense in depth if it doesn't strictly enforce requirements on critical paths, or if the `require_auth` flag is disabled globally.
**Prevention:** Always inject explicit route-level dependencies like `Security(verify_api_key)` when instantiating the `APIRouter` for sensitive areas, ensuring comprehensive and localized protection.
