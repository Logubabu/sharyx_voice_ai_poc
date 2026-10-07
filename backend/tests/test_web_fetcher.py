import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.search.fetcher import WebFetcher


@pytest.mark.asyncio
async def test_ssrf_ip_blocking():
    fetcher = WebFetcher()

    blocked_urls = [
        "http://127.0.0.1/admin",
        "http://localhost/secret",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file.txt",
        "file:///etc/passwd",
    ]

    for url in blocked_urls:
        result = await fetcher.fetch(url)
        assert result["success"] is False
        assert "Security restriction" in result["error"] or "Invalid URL scheme" in result["error"]


@pytest.mark.asyncio
async def test_html_parsing_text_extraction():
    fetcher = WebFetcher(max_text_length=500)

    sample_html = """
    <html>
        <head>
            <title>Sample Webpage Title</title>
            <style>body { color: red; }</style>
            <script>alert('xss');</script>
        </head>
        <body>
            <header><nav>Home | About</nav></header>
            <main>
                <h1>Welcome to AI Portal</h1>
                <p>This is the main article text containing clean information.</p>
            </main>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """

    title, text = fetcher.extract_text_from_html(sample_html)

    assert title == "Sample Webpage Title"
    assert "Welcome to AI Portal" in text
    assert "This is the main article text" in text
    assert "alert('xss')" not in text
    assert "body { color: red; }" not in text
    assert "Copyright 2026" not in text  # Footer tag was decomposed


@pytest.mark.asyncio
async def test_web_fetch_success():
    fetcher = WebFetcher()

    sample_html = "<html><head><title>Test</title></head><body><p>Hello World</p></body></html>"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.headers = {"content-type": "text/html; charset=utf-8"}
        mock_res.content = sample_html.encode("utf-8")
        mock_get.return_value = mock_res

        # Patch DNS resolution to return public IP
        with patch.object(fetcher, "validate_url_ssrf", return_value=(True, "")):
            res = await fetcher.fetch("https://example.com/news")

            assert res["success"] is True
            assert res["title"] == "Test"
            assert "Hello World" in res["text"]


@pytest.mark.asyncio
async def test_web_fetch_timeout():
    fetcher = WebFetcher(timeout=1.0)

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        with patch.object(fetcher, "validate_url_ssrf", return_value=(True, "")):
            res = await fetcher.fetch("https://example.com/slow")
            assert res["success"] is False
            assert "timed out" in res["error"].lower()
