## 2024-05-23 - Added Authentication to Sensitive Admin Endpoints
**Vulnerability:** Missing authentication on critical admin API endpoints (`/api/admin/ingest`, `/api/admin/api-keys`, `/api/admin/stats`, etc.) potentially allowed unauthenticated users to trigger data ingestion, access telemetry/metrics, and manage API keys.
**Learning:** Although `verify_api_key` dependency existed in `src/security/authentication.py`, it was not applied to the sensitive endpoints in `src/api/routes/admin.py`, leaving these endpoints publicly accessible without an API key.
**Prevention:** When creating new sensitive endpoints, always secure them by adding `Depends(verify_api_key)` directly to the target function signatures instead of relying on global settings.
