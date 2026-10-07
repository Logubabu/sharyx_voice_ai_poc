import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.search.provider import SearchResult
from app.services.search.searxng import SearXNGProvider


@pytest.mark.asyncio
async def test_searxng_provider_success():
    provider = SearXNGProvider(base_url="http://localhost:8080")
    
    mock_response_json = {
        "results": [
            {
                "title": "Latest AI News 2026",
                "url": "https://example.com/ai-news",
                "content": "Breakthroughs in multimodal voice AI models.",
                "engine": "google",
                "publishedDate": "2026-10-01",
            },
            {
                "title": "OpenAI Model Release",
                "url": "https://example.com/openai",
                "snippet": "New flagship model released today.",
                "category": "news",
            },
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_response_json
        mock_get.return_value = mock_res

        results = await provider.search("latest AI news", max_results=5, timeout=5.0)

        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].title == "Latest AI News 2026"
        assert results[0].url == "https://example.com/ai-news"
        assert results[0].snippet == "Breakthroughs in multimodal voice AI models."
        assert results[0].source == "google"
        assert results[0].published_at == "2026-10-01"


@pytest.mark.asyncio
async def test_searxng_provider_empty_query():
    provider = SearXNGProvider(base_url="http://localhost:8080")
    results = await provider.search("   ")
    assert results == []


@pytest.mark.asyncio
async def test_searxng_provider_http_error():
    provider = SearXNGProvider(base_url="http://localhost:8080")
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 500
        mock_res.text = "Internal Server Error"
        mock_get.return_value = mock_res

        results = await provider.search("latest news")
        assert results == []


@pytest.mark.asyncio
async def test_searxng_provider_timeout():
    provider = SearXNGProvider(base_url="http://localhost:8080")

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        results = await provider.search("latest news", timeout=1.0)
        assert results == []


@pytest.mark.asyncio
async def test_searxng_provider_network_error():
    provider = SearXNGProvider(base_url="http://localhost:8080")

    with patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Connection refused")):
        results = await provider.search("latest news")
        assert results == []
