import time
from typing import List, Dict, Any, Optional
import httpx
from app.utils.logging import logger
from app.services.search.provider import SearchProvider, SearchResult


class SearXNGProvider(SearchProvider):
    """SearXNG self-hosted open-source search engine provider implementation."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        # Remove trailing slashes for consistent URL formatting
        self.base_url = base_url.rstrip("/")

    async def search(
        self,
        query: str,
        max_results: int = 5,
        timeout: float = 8.0,
    ) -> List[SearchResult]:
        """Queries SearXNG JSON endpoint and returns normalized search results."""
        if not query or not query.strip():
            logger.warning("[SEARXNG] Empty search query provided.")
            return []

        search_url = f"{self.base_url}/search"
        params = {
            "q": query.strip(),
            "format": "json",
        }

        start_time = time.time()
        logger.info(f"[SEARXNG] Requesting search for query: '{query.strip()}' at {search_url}")

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(search_url, params=params)
                duration_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    logger.error(
                        f"[SEARXNG][ERROR] HTTP {response.status_code} from SearXNG ({duration_ms:.1f}ms): {response.text[:200]}"
                    )
                    return []

                data = response.json()
                raw_results = data.get("results", [])
                
                results: List[SearchResult] = []
                for item in raw_results[:max_results]:
                    # Normalize fields
                    title = item.get("title") or ""
                    url = item.get("url") or ""
                    snippet = item.get("content") or item.get("snippet") or ""
                    source = item.get("engine") or item.get("category") or "SearXNG"
                    published_at = item.get("publishedDate") or item.get("pubdate") or ""

                    if url:
                        results.append(
                            SearchResult(
                                title=title.strip(),
                                url=url.strip(),
                                snippet=snippet.strip(),
                                source=source.strip(),
                                published_at=published_at.strip(),
                            )
                        )

                logger.info(
                    f"[SEARXNG] Search completed in {duration_ms:.1f}ms: found {len(results)} results for query '{query}'"
                )
                return results

        except httpx.TimeoutException:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[SEARXNG][TIMEOUT] Search timed out after {duration_ms:.1f}ms for query: '{query}'")
            return []
        except httpx.RequestError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[SEARXNG][NETWORK-ERROR] Connection error after {duration_ms:.1f}ms: {e}")
            return []
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(f"[SEARXNG][UNEXPECTED-ERROR] Unexpected error during search after {duration_ms:.1f}ms: {e}")
            return []
