import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.search.duckduckgo import DuckDuckGoProvider
from app.services.search.fallback import FallbackSearchProvider
from app.services.search.provider import SearchResult


@pytest.mark.asyncio
async def test_duckduckgo_provider_success():
    provider = DuckDuckGoProvider()

    sample_html = """
    <div class="result">
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fnews&rut=123">Realtime AI News</a>
        <a class="result__snippet">Latest breakthroughs in multimodal AI models.</a>
    </div>
    """

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.text = sample_html
        mock_post.return_value = mock_res

        results = await provider.search("latest AI news", max_results=5)

        assert len(results) == 1
        assert results[0].title == "Realtime AI News"
        assert results[0].url == "https://example.com/news"
        assert "Latest breakthroughs" in results[0].snippet


@pytest.mark.asyncio
async def test_fallback_search_provider():
    primary = AsyncMock()
    primary.search.return_value = []  # Primary fails / returns empty

    fallback = AsyncMock()
    fallback.search.return_value = [
        SearchResult(title="Fallback News", url="https://fallback.com", snippet="Content", source="DuckDuckGo")
    ]

    composite = FallbackSearchProvider(primary_provider=primary, fallback_provider=fallback)
    results = await composite.search("query")

    assert len(results) == 1
    assert results[0].title == "Fallback News"
    assert primary.search.called
    assert fallback.search.called
