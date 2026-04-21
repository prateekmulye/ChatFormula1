## 2025-04-21 - [Admin Endpoints Missing Authentication]
**Vulnerability:** The admin API router (`src/api/routes/admin.py`) was entirely unauthenticated by default, allowing arbitrary users to access administrative features like `create_api_key` and ingest endpoints.
**Learning:** For defense in depth, relying solely on global authentication middleware is insufficient or easily bypassed.
**Prevention:** Always inject explicit route-level dependencies like `Security(verify_api_key)` directly into the `APIRouter` initialization to comprehensively secure all endpoints within that router.
