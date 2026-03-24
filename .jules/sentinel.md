## 2024-05-24 - Unauthenticated Admin Endpoints in FastAPI

**Vulnerability:** Multiple sensitive administrative endpoints in `src/api/routes/admin.py` (e.g., `/api/admin/ingest`, `/api/admin/api-keys`, `/api/admin/stats`) were exposed publicly without authentication.
**Learning:** The FastAPI `APIRouter` was defined without global dependencies, and individual admin route functions omitted the `Security(verify_api_key)` injection, leaving them accessible to any user who discovered the paths.
**Prevention:** Always verify that sensitive route definitions include explicit dependency injection for authentication (e.g., `api_key: APIKey = Security(verify_api_key)`), or apply the dependency globally at the `APIRouter` level if the entire module is strictly private.
