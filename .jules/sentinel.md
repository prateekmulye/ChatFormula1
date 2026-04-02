## 2024-04-02 - Explicit Route-Level Authentication
**Vulnerability:** Admin API endpoints lacked explicit route-level dependency checks, relying on global authentication middleware that is not applied by default.
**Learning:** FastAPI dependency injection using `Security(verify_api_key)` is required on sensitive routes for defense-in-depth, even if global middleware exists, to ensure authentication cannot be bypassed.
**Prevention:** Always inject explicit authentication dependencies into admin or sensitive endpoints rather than relying solely on global router/middleware config.
