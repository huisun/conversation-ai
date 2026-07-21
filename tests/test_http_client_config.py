"""Tests for HTTP client configuration in BaseAPIClient."""

import httpx
import pytest

from tac.context.memory import MemoryClient


class TestHTTPClientConfig:
    """Test HTTP client configuration."""

    @pytest.mark.asyncio
    async def test_base_async_client_enables_redirects(self) -> None:
        """Test that BaseAPIClient._get_client() has follow_redirects enabled."""
        client = MemoryClient(
            store_id="test_store",
            api_key="test_key",
            api_secret="test_token",
        )

        async with client._get_client() as http_client:
            assert http_client.follow_redirects is True

    def test_base_sync_client_enables_redirects(self) -> None:
        """Test that BaseAPIClient._get_sync_client() has follow_redirects enabled."""
        client = MemoryClient(
            store_id="test_store",
            api_key="test_key",
            api_secret="test_token",
        )

        with client._get_sync_client() as http_client:
            assert http_client.follow_redirects is True

    @pytest.mark.asyncio
    async def test_async_client_handles_redirect_with_auth(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that BaseAPIClient async client follows redirects and preserves auth headers."""

        def handler(request: httpx.Request) -> httpx.Response:
            # Simulate redirect from merged profile to canonical profile
            if "merged_profile" in str(request.url):
                return httpx.Response(
                    status_code=307,
                    headers={
                        "Location": str(request.url).replace("merged_profile", "canonical_profile")
                    },
                )
            # Final response after redirect
            # Verify auth header is present
            assert request.headers.get("authorization") is not None
            return httpx.Response(
                status_code=200,
                json={"profile_id": "canonical_profile", "status": "success"},
            )

        transport = httpx.MockTransport(handler)
        original_async_client = httpx.AsyncClient

        # Monkeypatch httpx.AsyncClient to inject mock transport
        def mock_async_client(*args, **kwargs):
            # Verify follow_redirects is passed
            assert kwargs.get("follow_redirects") is True
            # Replace transport with mock
            kwargs["transport"] = transport
            return original_async_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", mock_async_client)

        client = MemoryClient(
            store_id="test_store",
            api_key="test_key",
            api_secret="test_secret",
        )

        # Use SDK's client method which now uses mocked httpx.AsyncClient
        async with client._get_client() as http_client:
            response = await http_client.get(
                "https://memory.twilio.com/v1/Stores/test_store/Profiles/merged_profile"
            )

            # Verify redirect was followed and auth was preserved
            assert response.status_code == 200
            assert response.json()["profile_id"] == "canonical_profile"
            assert "canonical_profile" in str(response.url)

    def test_sync_client_handles_redirect_with_auth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that BaseAPIClient sync client follows redirects and preserves auth headers."""

        def handler(request: httpx.Request) -> httpx.Response:
            # Simulate redirect from merged profile to canonical profile
            if "merged_profile" in str(request.url):
                return httpx.Response(
                    status_code=307,
                    headers={
                        "Location": str(request.url).replace("merged_profile", "canonical_profile")
                    },
                )
            # Final response after redirect
            # Verify auth header is present
            assert request.headers.get("authorization") is not None
            return httpx.Response(
                status_code=200,
                json={"profile_id": "canonical_profile", "status": "success"},
            )

        transport = httpx.MockTransport(handler)
        original_client = httpx.Client

        # Monkeypatch httpx.Client to inject mock transport
        def mock_client(*args, **kwargs):
            # Verify follow_redirects is passed
            assert kwargs.get("follow_redirects") is True
            # Replace transport with mock
            kwargs["transport"] = transport
            return original_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", mock_client)

        client = MemoryClient(
            store_id="test_store",
            api_key="test_key",
            api_secret="test_secret",
        )

        # Use SDK's client method which now uses mocked httpx.Client
        with client._get_sync_client() as http_client:
            response = http_client.get(
                "https://memory.twilio.com/v1/Stores/test_store/Profiles/merged_profile"
            )

            # Verify redirect was followed and auth was preserved
            assert response.status_code == 200
            assert response.json()["profile_id"] == "canonical_profile"
            assert "canonical_profile" in str(response.url)
