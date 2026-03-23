## 2025-03-23 - [Missing Authentication on Admin Endpoints]
**Vulnerability:** Found that several sensitive administrative endpoints under `/api/admin` (e.g. `ingest`, `stats`, `metrics`, etc.) lacked authentication, meaning any user could execute destructive or sensitive actions without an API key.
**Learning:** This existed because while `verify_api_key` was implemented in `src/security/authentication.py`, the `Depends(verify_api_key)` or `Security(verify_api_key)` was never explicitly added to these endpoints in `src/api/routes/admin.py`.
**Prevention:** To avoid this next time, always ensure sensitive endpoints have the necessary FastAPI `Depends` or `Security` authentication declarations applied at the route level.
