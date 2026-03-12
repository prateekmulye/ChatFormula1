from unittest.mock import MagicMock

from fastapi import Request

from src.security.rate_limiting import RateLimiter


def test_ip_extraction_behind_proxy(monkeypatch):
    class MockSettings:
        trusted_proxies = ["10.0.0.1", "10.0.0.2"]

    monkeypatch.setattr("src.config.settings.get_settings", lambda: MockSettings())

    limiter = RateLimiter()

    # Case 1: Direct request, no proxy
    request1 = MagicMock(spec=Request)
    request1.state = MagicMock()
    request1.state.user_id = None
    request1.headers = {}
    request1.client.host = "203.0.113.1"
    assert limiter._get_client_id(request1) == "ip:203.0.113.1"

    # Case 2: Untrusted proxy (should ignore X-Forwarded-For)
    request2 = MagicMock(spec=Request)
    request2.state = MagicMock()
    request2.state.user_id = None
    request2.headers = {"X-Forwarded-For": "203.0.113.1"}
    request2.client.host = "192.168.1.1"  # Not in trusted_proxies
    assert limiter._get_client_id(request2) == "ip:192.168.1.1"

    # Case 3: Trusted proxy, single forwarded IP
    request3 = MagicMock(spec=Request)
    request3.state = MagicMock()
    request3.state.user_id = None
    request3.headers = {"X-Forwarded-For": "203.0.113.1"}
    request3.client.host = "10.0.0.1"  # In trusted_proxies
    assert limiter._get_client_id(request3) == "ip:203.0.113.1"

    # Case 4: Trusted proxy chain, spoofed IP at the beginning
    request4 = MagicMock(spec=Request)
    request4.state = MagicMock()
    request4.state.user_id = None
    request4.headers = {"X-Forwarded-For": "1.2.3.4, 203.0.113.1, 10.0.0.2"}
    request4.client.host = "10.0.0.1"  # In trusted_proxies
    assert limiter._get_client_id(request4) == "ip:203.0.113.1"

    # Case 5: All trusted proxies in chain
    request5 = MagicMock(spec=Request)
    request5.state = MagicMock()
    request5.state.user_id = None
    request5.headers = {"X-Forwarded-For": "10.0.0.2, 10.0.0.1"}
    request5.client.host = "10.0.0.1"  # In trusted_proxies
    assert limiter._get_client_id(request5) == "ip:10.0.0.2"
