## 2024-04-02 - Missing Admin Authentication
**Vulnerability:** Sensitive admin endpoints (`/stats`, `/ingest`, `/api-keys`) lacked direct authentication checks in their function signatures, relying solely on global middleware.
**Learning:** For defense in depth, relying solely on `AuthenticationMiddleware` is insufficient as it can be bypassed for certain prefixes or if `require_auth` is set to false.
**Prevention:** Always inject explicit route-level dependencies like `Security(verify_api_key)` into sensitive admin endpoint signatures.
