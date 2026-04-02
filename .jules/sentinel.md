## 2024-05-18 - Missing Authentication on Admin Endpoints
**Vulnerability:** Several sensitive administrative endpoints in `src/api/routes/admin.py` (like `/stats`, `/ingest`, `/metrics/reset`, and API key management routes) were missing authentication checks, allowing unauthenticated access.
**Learning:** Relying solely on global middleware is insufficient if the middleware skips paths or if defense-in-depth is required. Route-level dependencies ensure explicit protection.
**Prevention:** Always inject explicit route-level dependencies like `Security(verify_api_key)` into the function signatures of sensitive admin endpoints.
