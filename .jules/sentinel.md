## 2026-04-22 - Missing Authentication on Sensitive Router Endpoints
**Vulnerability:** The admin endpoints router (`src/api/routes/admin.py`) was initialized as `APIRouter()` without explicitly adding `verify_api_key` to its dependencies. This exposed sensitive internal operations like `/ingest` and `/api-keys`.
**Learning:** Initializing an API router without route-level security dependencies bypasses protection mechanisms unless handled exclusively by a global middleware, which isn't sufficient for a defense-in-depth strategy.
**Prevention:** Always inject explicit route-level security dependencies directly during router initialization (e.g., `router = APIRouter(dependencies=[Security(verify_api_key)])`) to ensure all registered endpoints are protected by default.
