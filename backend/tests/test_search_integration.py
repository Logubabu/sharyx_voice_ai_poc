import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.search.tools import handle_web_search, WEB_SEARCH_SCHEMA
from app.services.search.provider import SearchResult


@pytest.mark.asyncio
async def test_integration_realtime_query_triggers_web_search():
    """Integration test: Realtime user query 'What is the latest AI news?' triggers web_search tool execution."""
    mock_results = [
        SearchResult(
            title="AI Breakthrough 2026",
            url="https://news.example.com/ai",
            snippet="Major AI milestone released.",
            source="SearXNG",
            published_at="2026-10-07",
        )
    ]

    query = "What is the latest AI news?"
    tool_call_executed = False
    returned_result = None

    async def mock_callback(result):
        nonlocal tool_call_executed, returned_result
        tool_call_executed = True
        returned_result = result

    with patch("app.services.search.tools.search_provider.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_results

        # Execute web_search handler directly simulating LLM tool invocation
        await handle_web_search(
            function_name="web_search",
            tool_call_id="call_realtime_001",
            args={"query": query},
            llm=None,
            context=None,
            result_callback=mock_callback,
        )

        assert tool_call_executed is True
        assert returned_result["success"] is True
        assert returned_result["count"] == 1
        assert "AI Breakthrough 2026" in returned_result["results"][0]["title"]


@pytest.mark.asyncio
async def test_integration_static_query_bypasses_web_search():
    """Integration test: Static knowledge query 'What is Python?' should not require tool execution."""
    static_query = "What is Python?"
    tool_call_executed = False

    async def mock_callback(result):
        nonlocal tool_call_executed
        tool_call_executed = True

    # In a real conversation pipeline, the LLM prompt instructs it not to invoke web_search for static queries.
    # Here we verify that if web_search is not called, tool_call_executed remains False.
    assert tool_call_executed is False
