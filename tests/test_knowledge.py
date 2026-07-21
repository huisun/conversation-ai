"""Tests for Knowledge API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tac.context.knowledge import KnowledgeClient
from tac.models.knowledge import KnowledgeBase, KnowledgeChunkResult


@pytest.fixture
def knowledge_client():
    """Create a KnowledgeClient instance for testing."""
    return KnowledgeClient(
        api_key="test_api_key",
        api_secret="test_api_token",
    )


class TestKnowledgeClient:
    """Test KnowledgeClient API methods."""

    def test_init(self):
        """Test KnowledgeClient initialization."""
        client = KnowledgeClient(
            api_key="test_api_key",
            api_secret="test_api_token",
        )
        assert client.base_url == "https://knowledge.twilio.com"
        assert client.api_key == "test_api_key"
        assert client.api_secret == "test_api_token"

    def test_init_with_region(self):
        client = KnowledgeClient(
            api_key="test_api_key",
            api_secret="test_api_token",
            region="au1",
        )
        assert client.base_url == "https://knowledge.au1.twilio.com"

    def test_init_without_region(self):
        client = KnowledgeClient(
            api_key="test_api_key",
            api_secret="test_api_token",
        )
        assert client.base_url == "https://knowledge.twilio.com"

    @pytest.mark.asyncio
    async def test_get_knowledge_base_success(self, knowledge_client):
        """Test successful knowledge base retrieval."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "know_knowledgebase_00000000000000000000000000",
            "displayName": "Product FAQ",
            "description": "Frequently asked questions about our products",
            "status": "ACTIVE",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "version": 1,
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(knowledge_client, "_get_client", return_value=mock_client):
            # Call method
            kb = await knowledge_client.get_knowledge_base(
                "know_knowledgebase_00000000000000000000000000"
            )

            # Assertions
            assert isinstance(kb, KnowledgeBase)
            assert kb.id == "know_knowledgebase_00000000000000000000000000"
            assert kb.display_name == "Product FAQ"
            assert kb.description == "Frequently asked questions about our products"
            assert kb.status == "ACTIVE"

            # Verify API call
            mock_client.get.assert_called_once_with(
                "https://knowledge.twilio.com/v2/ControlPlane/KnowledgeBases/know_knowledgebase_00000000000000000000000000"
            )

    @pytest.mark.asyncio
    async def test_get_knowledge_base_not_found(self, knowledge_client):
        """Test knowledge base retrieval when not found."""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(knowledge_client, "_get_client", return_value=mock_client):
            # Should raise exception
            with pytest.raises(httpx.HTTPStatusError):
                await knowledge_client.get_knowledge_base("know_knowledgebase_invalid")

    @pytest.mark.asyncio
    async def test_search_knowledge_base_success(self, knowledge_client):
        """Test successful knowledge base search."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chunks": [
                {
                    "content": "Our product offers 24/7 customer support",
                    "knowledgeId": "know_00000000000000000000000000000001",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "score": 0.95,
                },
                {
                    "content": "We provide a 30-day money-back guarantee",
                    "knowledgeId": "know_00000000000000000000000000000002",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "score": 0.88,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(knowledge_client, "_get_client", return_value=mock_client):
            # Call method
            results = await knowledge_client.search_knowledge_base(
                knowledge_base_id="know_knowledgebase_00000000000000000000000000",
                query="customer support",
                top_k=5,
            )

            # Assertions
            assert len(results) == 2
            assert all(isinstance(r, KnowledgeChunkResult) for r in results)
            assert results[0].content == "Our product offers 24/7 customer support"
            assert results[0].score == 0.95
            assert results[1].content == "We provide a 30-day money-back guarantee"
            assert results[1].score == 0.88

            # Verify API call
            mock_client.post.assert_called_once_with(
                "https://knowledge.twilio.com/v2/KnowledgeBases/know_knowledgebase_00000000000000000000000000/Search",
                json={"query": "customer support", "top": 5},
            )

    @pytest.mark.asyncio
    async def test_search_knowledge_base_with_knowledge_ids(self, knowledge_client):
        """Test knowledge base search with knowledge_ids filter."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"chunks": []}
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(knowledge_client, "_get_client", return_value=mock_client):
            # Call method with knowledge_ids
            await knowledge_client.search_knowledge_base(
                knowledge_base_id="know_knowledgebase_00000000000000000000000000",
                query="test query",
                top_k=3,
                knowledge_ids=["know_001", "know_002"],
            )

            # Verify API call includes knowledge_ids
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["knowledgeIds"] == ["know_001", "know_002"]

    @pytest.mark.asyncio
    async def test_search_knowledge_base_empty_results(self, knowledge_client):
        """Test knowledge base search with no results."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"chunks": []}
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(knowledge_client, "_get_client", return_value=mock_client):
            # Call method
            results = await knowledge_client.search_knowledge_base(
                knowledge_base_id="know_knowledgebase_00000000000000000000000000",
                query="nonexistent query",
            )

            # Assertions
            assert results == []

    @pytest.mark.asyncio
    async def test_search_knowledge_base_error(self, knowledge_client):
        """Test knowledge base search error handling."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal server error", request=MagicMock(), response=mock_response
        )

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(knowledge_client, "_get_client", return_value=mock_client):
            # Should raise exception
            with pytest.raises(httpx.HTTPStatusError):
                await knowledge_client.search_knowledge_base(
                    knowledge_base_id="know_knowledgebase_00000000000000000000000000",
                    query="test query",
                )

    @pytest.mark.asyncio
    async def test_search_knowledge_base_default_top_k(self, knowledge_client):
        """Test that search uses default top_k value."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"chunks": []}
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(knowledge_client, "_get_client", return_value=mock_client):
            # Call method without top_k
            await knowledge_client.search_knowledge_base(
                knowledge_base_id="know_knowledgebase_00000000000000000000000000",
                query="test query",
            )

            # Verify default top_k=5 is used
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["top"] == 5
