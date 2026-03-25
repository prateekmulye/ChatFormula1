## 2024-05-18 - Unauthenticated Admin Endpoints
**Vulnerability:** Admin endpoints like `/ingest` and `/api-keys` were exposed without authentication.
**Learning:** Mixing public and private routes in a single router without global middleware requires applying security dependencies individually to each sensitive endpoint.
**Prevention:** Use `Security(verify_api_key)` on all sensitive operations to ensure authorized access.
