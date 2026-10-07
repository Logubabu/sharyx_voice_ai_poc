import time
from typing import List
from urllib.parse import parse_qs, urlparse, unquote
import httpx
from bs4 import BeautifulSoup

from app.utils.logging import logger
from app.services.search.provider import SearchProvider, SearchResult


class DuckDuckGoProvider(SearchProvider):
    """Online web search provider powered by DuckDuckGo (no API key required)."""

    def __init__(self, endpoint_url: str = "https://html.duckduckgo.com/html/"):
        self.endpoint_url = endpoint_url

    async def search(
        self,
        query: str,
        max_results: int = 5,
        timeout: float = 8.0,
    ) -> List[SearchResult]:
        """Queries online DuckDuckGo search and returns normalized SearchResult objects."""
        if not query or not query.strip():
            logger.warning("[DUCKDUCKGO] Empty search query provided.")
            return []

        start_time = time.time()
        clean_query = query.strip()
        logger.info(f"[DUCKDUCKGO] Querying real-time online web search for: '{clean_query}'")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        data = {"q": clean_query}

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.post(self.endpoint_url, data=data, headers=headers)
                duration_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    logger.error(
                        f"[DUCKDUCKGO][ERROR] HTTP {response.status_code} from DuckDuckGo ({duration_ms:.1f}ms)"
                    )
                    return []

                soup = BeautifulSoup(response.text, "html.parser")
                results: List[SearchResult] = []

                for result in soup.find_all("div", class_="result"):
                    if len(results) >= max_results:
                        break

                    title_tag = result.find("a", class_="result__a")
                    snippet_tag = result.find("a", class_="result__snippet")

                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    raw_href = title_tag.get("href", "")

                    # Extract actual target URL from DDG redirect link
                    clean_url = raw_href
                    if "uddg=" in raw_href:
                        parsed = urlparse(raw_href)
                        qs = parse_qs(parsed.query)
                        if "uddg" in qs:
                            clean_url = qs["uddg"][0]
                    elif raw_href.startswith("//"):
                        clean_url = "https:" + raw_href

                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                    if clean_url and (clean_url.startswith("http://") or clean_url.startswith("https://")):
                        results.append(
                            SearchResult(
                                title=title,
                                url=clean_url,
                                snippet=snippet,
                                source="DuckDuckGo (Online)",
                                published_at="",
                            )
                        )

                logger.info(
                    f"[DUCKDUCKGO] Online search completed in {duration_ms:.1f}ms: found {len(results)} results for query '{clean_query}'"
                )
                return results

        except httpx.TimeoutException:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[DUCKDUCKGO][TIMEOUT] Online search timed out after {duration_ms:.1f}ms for query: '{clean_query}'")
            return []
        except httpx.RequestError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[DUCKDUCKGO][NETWORK-ERROR] Connection error after {duration_ms:.1f}ms: {e}")
            return []
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(f"[DUCKDUCKGO][UNEXPECTED-ERROR] Unexpected error during online search after {duration_ms:.1f}ms: {e}")
            return []
