import re
import html
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from app.utils.logging import logger


class SearchResult:
    """Encapsulates a single search engine result item."""

    def __init__(self, title: str, url: str, snippet: str):
        self.title = title.strip()
        self.url = url.strip()
        self.snippet = snippet.strip()

    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }


def sanitize_web_content(content: str, max_chars: int = 1000) -> str:
    """Sanitizes web text content by stripping HTML tags, script/style blocks, and redundant whitespace."""
    if not content:
        return ""

    # Unescape HTML entities
    text = html.unescape(content)

    # Use BeautifulSoup if tags are present
    if "<" in text and ">" in text:
        try:
            soup = BeautifulSoup(text, "html.parser")
            for element in soup(["script", "style", "head", "title", "meta", "[document]"]):
                element.decompose()
            text = soup.get_text(separator=" ")
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)

    # Remove extra whitespace and newlines
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate if exceeds character limit
    if len(text) > max_chars:
        text = text[:max_chars] + "..."

    return text


class RealtimeSearchProvider:
    """Async Real-Time Web Search Provider supporting DuckDuckGo, SearXNG, and HTML scraping fallback."""

    def __init__(self, searxng_url: Optional[str] = None):
        self.searxng_url = searxng_url or "https://searx.be/search"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def search(self, query: str, max_results: int = 5, timeout: float = 8.0) -> List[SearchResult]:
        """Executes a real-time web search across available online providers with robust fallback."""
        query = query.strip()
        if not query:
            return []

        logger.info(f"[SEARCH-PROVIDER] Executing real-time web search for query: '{query}'")

        # 1. Try DuckDuckGo Lite / HTML API search
        results = await self._search_duckduckgo(query, max_results, timeout)
        if results:
            return results

        # 2. Try SearXNG fallback if DDG returned no results
        results = await self._search_searxng(query, max_results, timeout)
        if results:
            return results

        logger.warning(f"[SEARCH-PROVIDER] All web search providers returned empty results for '{query}'")
        return []

    async def _search_duckduckgo(self, query: str, max_results: int, timeout: float) -> List[SearchResult]:
        """Fetches and parses DuckDuckGo HTML search results."""
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": self.user_agent}
        data = {"q": query, "b": ""}

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.post(url, data=data, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"[SEARCH-PROVIDER] DuckDuckGo HTTP {response.status_code}")
                    return []

                soup = BeautifulSoup(response.text, "html.parser")
                results: List[SearchResult] = []

                for result in soup.select(".result"):
                    title_elem = result.select_one(".result__title a")
                    snippet_elem = result.select_one(".result__snippet")
                    url_elem = result.select_one(".result__url")

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if href and title:
                        results.append(SearchResult(title=title, url=href, snippet=snippet))
                        if len(results) >= max_results:
                            break

                logger.info(f"[SEARCH-PROVIDER] DuckDuckGo returned {len(results)} search results for '{query}'")
                return results

        except Exception as e:
            logger.warning(f"[SEARCH-PROVIDER] DuckDuckGo search failed: {e}")
            return []

    async def _search_searxng(self, query: str, max_results: int, timeout: float) -> List[SearchResult]:
        """Queries SearXNG JSON API instance."""
        headers = {"User-Agent": self.user_agent}
        params = {"q": query, "format": "json"}

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(self.searxng_url, params=params, headers=headers)
                if response.status_code != 200:
                    return []

                data = response.json()
                raw_results = data.get("results", [])
                results: List[SearchResult] = []

                for item in raw_results[:max_results]:
                    title = item.get("title", "")
                    url = item.get("url", "")
                    snippet = item.get("content", "")
                    if title and url:
                        results.append(SearchResult(title=title, url=url, snippet=snippet))

                logger.info(f"[SEARCH-PROVIDER] SearXNG returned {len(results)} results for '{query}'")
                return results

        except Exception as e:
            logger.warning(f"[SEARCH-PROVIDER] SearXNG search failed: {e}")
            return []


search_provider = RealtimeSearchProvider()
