import asyncio
import ipaddress
import re
import socket
import time
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from app.utils.logging import logger
from app.utils.audit import audit_logger


class WebFetcher:
    """Safe webpage fetcher with SSRF protection, size limits, timeouts, and HTML text extraction."""


    def __init__(
        self,
        timeout: float = 10.0,
        max_bytes: int = 2_000_000,
        max_text_length: int = 4000,
    ):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_text_length = max_text_length

    @staticmethod
    def is_ip_blocked(ip_str: str) -> bool:
        """Check if an IP address is private, loopback, link-local, or reserved (SSRF protection)."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            )
        except ValueError:
            return True

    async def validate_url_ssrf(self, url: str) -> Tuple[bool, str]:
        """Validates that a URL uses http/https and does not resolve to private/local IP addresses."""
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ("http", "https"):
                return False, f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed."

            hostname = parsed.hostname
            if not hostname:
                return False, "Invalid URL: missing hostname."

            # Check if host is direct IP
            try:
                ip_obj = ipaddress.ip_address(hostname)
                if self.is_ip_blocked(str(ip_obj)):
                    return False, f"Access to private/local IP address '{hostname}' is blocked."
                return True, ""
            except ValueError:
                # Hostname is domain name, resolve DNS
                pass

            loop = asyncio.get_running_loop()
            port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
            addr_info = await loop.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
            
            if not addr_info:
                return False, f"Could not resolve hostname '{hostname}'."

            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_str = sockaddr[0]
                if self.is_ip_blocked(ip_str):
                    return False, f"URL resolves to private/local IP address '{ip_str}' which is blocked."

            return True, ""

        except Exception as e:
            return False, f"URL validation error: {str(e)}"

    def extract_text_from_html(self, html_content: str) -> Tuple[str, str]:
        """Parses HTML, strips unwanted tags, extracts clean text and page title."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Remove scripts, styles, forms, headers, footers, etc.
        for tag in soup(
            ["script", "style", "nav", "header", "footer", "svg", "noscript", "iframe", "form", "button", "aside", "head"]
        ):
            tag.decompose()

        # Extract body or main content
        main_content = soup.find("main") or soup.find("article") or soup.body or soup
        raw_text = main_content.get_text(separator=" ", strip=True)

        # Normalize whitespace
        clean_text = re.sub(r"\s+", " ", raw_text).strip()
        return title, clean_text

    async def fetch(self, url: str) -> Dict[str, Any]:
        """Safely fetches webpage content with SSRF validation, size limiting, and timeout."""
        start_time = time.time()
        logger.info(f"[WEB-FETCH] Fetching webpage: {url}")

        # SSRF Check
        is_safe, error_msg = await self.validate_url_ssrf(url)
        if not is_safe:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(f"[WEB-FETCH][SSRF-BLOCKED] {error_msg} ({duration_ms:.1f}ms)")
            audit_logger.log_event(
                event="SSRF_BLOCKED",
                category="security",
                actor="system",
                action="url_validation",
                details={"url": url, "reason": error_msg},
                status="BLOCKED",
                duration_ms=duration_ms,
            )
            return {
                "url": url,
                "success": False,
                "error": f"Security restriction: {error_msg}",
            }


        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        current_url = url
        max_redirects = 3

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                for redirect_count in range(max_redirects + 1):
                    # Fetch headers / stream
                    response = await client.get(current_url, headers=headers)

                    # Handle Redirects manually to enforce SSRF validation on target URL
                    if response.status_code in (301, 302, 303, 307, 308):
                        redirect_target = response.headers.get("location")
                        if not redirect_target:
                            break
                        # Handle relative redirect URLs
                        parsed_target = urlparse(redirect_target)
                        if not parsed_target.netloc:
                            base_parsed = urlparse(current_url)
                            redirect_target = f"{base_parsed.scheme}://{base_parsed.netloc}{redirect_target}"

                        # Validate target URL against SSRF
                        is_safe_target, target_error = await self.validate_url_ssrf(redirect_target)
                        if not is_safe_target:
                            logger.warning(f"[WEB-FETCH][SSRF-BLOCKED-REDIRECT] {target_error}")
                            return {
                                "url": url,
                                "success": False,
                                "error": f"Redirect blocked: {target_error}",
                            }
                        current_url = redirect_target
                        continue

                    duration_ms = (time.time() - start_time) * 1000

                    if response.status_code != 200:
                        logger.warning(f"[WEB-FETCH] HTTP {response.status_code} for {url} ({duration_ms:.1f}ms)")
                        return {
                            "url": url,
                            "success": False,
                            "error": f"Webpage returned HTTP status {response.status_code}.",
                        }

                    # Check Content-Type header if text/html
                    content_type = response.headers.get("content-type", "").lower()
                    if content_type and "text/html" not in content_type and "text/plain" not in content_type and "application/xhtml+xml" not in content_type:
                        logger.warning(f"[WEB-FETCH] Unsupported Content-Type '{content_type}' for {url}")
                        return {
                            "url": url,
                            "success": False,
                            "error": f"Unsupported page format: {content_type}",
                        }

                    # Size checking
                    raw_content = response.content
                    if len(raw_content) > self.max_bytes:
                        logger.warning(f"[WEB-FETCH] Content size ({len(raw_content)} bytes) exceeded limit ({self.max_bytes} bytes). Truncating.")
                        raw_content = raw_content[: self.max_bytes]

                    html_text = raw_content.decode("utf-8", errors="replace")
                    title, text_content = self.extract_text_from_html(html_text)

                    is_truncated = False
                    if len(text_content) > self.max_text_length:
                        text_content = text_content[: self.max_text_length] + " [Content truncated...]"
                        is_truncated = True

                    logger.info(
                        f"[WEB-FETCH] Successfully fetched {url} ({duration_ms:.1f}ms, extracted {len(text_content)} chars)"
                    )
                    return {
                        "url": url,
                        "title": title,
                        "text": text_content,
                        "success": True,
                        "truncated": is_truncated,
                    }

                return {
                    "url": url,
                    "success": False,
                    "error": "Too many redirects.",
                }

        except httpx.TimeoutException:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[WEB-FETCH][TIMEOUT] Webpage fetch timed out for {url} after {duration_ms:.1f}ms")
            return {
                "url": url,
                "success": False,
                "error": "Webpage request timed out.",
            }
        except httpx.RequestError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[WEB-FETCH][NETWORK-ERROR] Network error for {url}: {e}")
            return {
                "url": url,
                "success": False,
                "error": f"Network error fetching webpage: {str(e)}",
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(f"[WEB-FETCH][UNEXPECTED-ERROR] Error fetching {url}: {e}")
            return {
                "url": url,
                "success": False,
                "error": f"Error parsing webpage: {str(e)}",
            }
