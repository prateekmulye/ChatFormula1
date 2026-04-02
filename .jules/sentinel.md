## 2025-04-02 - Missing Authentication on Sensitive Admin Endpoints
**Vulnerability:** Sensitive admin endpoints such as `/api/admin/ingest` and `/api/admin/api-keys` lacked explicit route-level dependency security.
**Learning:** Depending entirely on global authentication middleware is insufficient if `require_auth` is false or the middleware allows bypasses.
**Prevention:** Always inject `Security(verify_api_key)` into function signatures for endpoints handling sensitive data.
