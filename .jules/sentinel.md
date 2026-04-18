## 2026-04-18 - Missing Authentication on Admin Endpoints
**Vulnerability:** Admin endpoints like API key generation, revocation, and dashboard access were missing authentication and could be accessed publicly.
**Learning:** FastAPI routers (`APIRouter`) need explicit dependency injection for authentication. If a router groups sensitive endpoints, applying security directly at the router level ensures all endpoints within that file are inherently protected.
**Prevention:** Always use `router = APIRouter(dependencies=[Security(verify_api_key)])` or similar global protection mechanisms for administrative and internal routers to ensure defense in depth and avoid unauthenticated access.
