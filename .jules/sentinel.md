## 2024-05-18 - Unauthenticated Admin Endpoints
**Vulnerability:** Admin endpoints like `/api/admin/api-keys` and `/api/admin/ingest` in `src/api/routes/admin.py` were missing authentication checks.
**Learning:** The `AuthenticationMiddleware` can be bypassed for certain prefixes or if `require_auth` is false. FastAPI route-level dependencies must be used for explicit security boundaries on sensitive endpoints.
**Prevention:** Always inject explicit security dependencies like `Depends(verify_api_key)` into admin or sensitive endpoints to ensure defense in depth, rather than relying solely on global middleware.
