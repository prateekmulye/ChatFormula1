## 2025-02-18 - Missing Authentication on Admin Endpoints
**Vulnerability:** Admin endpoints in `src/api/routes/admin.py` (like `/stats`, `/ingest`, `/api-keys`) were missing explicit authentication checks.
**Learning:** Relying solely on global middleware or assuming certain prefixes are protected is insufficient.
**Prevention:** Always inject explicit route-level dependencies like `Security(verify_api_key)` for sensitive endpoints for defense-in-depth.
