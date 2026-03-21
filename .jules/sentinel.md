## 2024-03-17 - Missing Authentication on Admin Endpoints
**Vulnerability:** Several sensitive administrative endpoints (ingestion, metric reset, and API key management) in `src/api/routes/admin.py` lacked authentication entirely.
**Learning:** Admin endpoints placed alongside public endpoints (like `/health`) can be easily missed if router-level dependencies aren't applied. In this case, no authentication mechanism (like `verify_api_key`) was applied to the sensitive endpoints.
**Prevention:** Apply function-level authentication dependencies to sensitive endpoints, or segregate public and private routes into separate routers so router-level security constraints can be strictly enforced.
