## 2026-03-19 - Missing Authentication on Admin Endpoints
**Vulnerability:** Admin endpoints for stats, configuration, metrics, and API keys lacked authentication (no `Depends(verify_api_key)`).
**Learning:** Even if a file is named `admin.py`, FastAPI routes do not automatically inherit authentication middleware or dependencies.
**Prevention:** Apply `Depends(verify_api_key)` directly to the function signatures of all sensitive routes, especially in mixed-use router files.
