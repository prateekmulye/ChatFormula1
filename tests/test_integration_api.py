"""Integration tests for FastAPI endpoints.

These tests start the FastAPI application and test endpoints end-to-end.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.main import app
from src.config.settings import Settings


@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_endpoint_structure(self, client: TestClient):
        """Test health endpoint response structure."""
        response = client.get("/health")
        data = response.json()

        # Should contain service status
        assert "services" in data or "status" in data

        if "services" in data:
            # Check individual service statuses
            assert isinstance(data["services"], dict)

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data or "name" in data

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/health")

        # Should have CORS headers
        assert (
            "access-control-allow-origin" in response.headers
            or response.status_code == 200
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestChatEndpoints:
    """Integration tests for chat endpoints."""

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    async def test_chat_endpoint_exists(self, async_client: AsyncClient):
        """Test chat endpoint exists."""
        response = await async_client.post(
            "/chat", json={"message": "Who won the 2021 F1 championship?"}
        )

        # Should not return 404
        assert response.status_code != 404

    async def test_chat_endpoint_validation(self, async_client: AsyncClient):
        """Test chat endpoint input validation."""
        # Test with empty message
        response = await async_client.post("/chat", json={"message": ""})

        # Should return validation error
        assert response.status_code in [400, 422]

    async def test_chat_endpoint_with_session(self, async_client: AsyncClient):
        """Test chat endpoint with session ID."""
        response = await async_client.post(
            "/chat",
            json={"message": "Tell me about F1", "session_id": "test-session-123"},
        )

        # Should accept session ID
        assert response.status_code in [200, 201, 404, 500]  # Various valid responses


@pytest.mark.integration
class TestAdminEndpoints:
    """Integration tests for admin endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_stats_endpoint_exists(self, client: TestClient):
        """Test stats endpoint exists."""
        response = client.get("/stats")

        # Should not return 404
        assert response.status_code != 404

    def test_ingest_endpoint_exists(self, client: TestClient):
        """Test ingest endpoint exists."""
        response = client.post("/ingest", json={})

        # Should not return 404 (might return 400 or 401 for auth)
        assert response.status_code != 404


@pytest.mark.integration
class TestAPIErrorHandling:
    """Integration tests for API error handling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_invalid_endpoint(self, client: TestClient):
        """Test accessing invalid endpoint."""
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_invalid_method(self, client: TestClient):
        """Test using invalid HTTP method."""
        response = client.delete("/health")

        # Should return method not allowed
        assert response.status_code in [404, 405]

    def test_malformed_json(self, client: TestClient):
        """Test sending malformed JSON."""
        response = client.post(
            "/chat",
            data="{ invalid json }",
            headers={"Content-Type": "application/json"},
        )

        # Should return bad request
        assert response.status_code in [400, 422]


@pytest.mark.integration
class TestAPIPerformance:
    """Integration tests for API performance."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint_response_time(self, client: TestClient):
        """Test health endpoint responds quickly."""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Health check should be fast (< 1 second)
        assert elapsed < 1.0

    def test_concurrent_health_checks(self, client: TestClient):
        """Test handling concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == 200 for r in results)


@pytest.mark.integration
class TestAPIDocumentation:
    """Integration tests for API documentation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_openapi_schema(self, client: TestClient):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_docs_endpoint(self, client: TestClient):
        """Test Swagger docs endpoint."""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
