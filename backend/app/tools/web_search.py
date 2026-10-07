from typing import Dict, Any
from pipecat.adapters.schemas.function_schema import FunctionSchema

from app.tools.base import BaseTool
from app.services.search.tools import search_provider, sanitize_web_content
from app.utils.logging import logger


class WebSearchTool(BaseTool):
    """Tool implementation for real-time web search."""

    def __init__(self):
        super().__init__(
            name="web_search",
            description=(
                "Search the live internet for current events, news, recent updates, real-time data, pricing, or specific facts beyond static knowledge. "
                "Use this tool whenever the user asks about current events, recent developments, real-time prices, or latest model/news releases. "
                "Do NOT call this tool for general static knowledge or standard conversational requests."
            ),
            timeout=8.0,
        )

    def get_schema(self, handler: Any = None) -> FunctionSchema:
        return FunctionSchema(
            name=self.name,
            description=self.description,
            properties={
                "query": {
                    "type": "string",
                    "description": "The search query string to search on the live internet.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Optional maximum number of search results to return (default 5).",
                },
            },
            required=["query"],
            handler=handler,
        )

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "").strip()
        max_results = args.get("max_results", 5)

        if not query:
            return {"success": False, "error": "Search query cannot be empty."}

        logger.info(f"[TOOL-EXEC][WEB_SEARCH] Searching for: '{query}'")
        try:
            results = await search_provider.search(query=query, max_results=max_results, timeout=self.timeout)
            if not results:
                return {
                    "success": True,
                    "query": query,
                    "count": 0,
                    "results": [],
                    "message": f"No web search results were found for '{query}'.",
                }

            normalized = []
            for r in results:
                res_dict = r.to_dict()
                res_dict["snippet"] = sanitize_web_content(res_dict["snippet"])
                normalized.append(res_dict)

            return {
                "success": True,
                "query": query,
                "count": len(normalized),
                "results": normalized,
            }

        except Exception as e:
            logger.exception(f"[TOOL-EXEC][WEB_SEARCH][ERROR] Search failed for '{query}': {e}")
            return {
                "success": False,
                "error": "Web search is temporarily unavailable.",
            }
