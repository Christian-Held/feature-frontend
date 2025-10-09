"""Web crawler service for extracting content from websites."""

import hashlib
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class WebsiteCrawler:
    """Crawls a website and extracts content from pages."""

    def __init__(
        self,
        base_url: str,
        max_pages: int = 100,
        timeout: int = 30,
        user_agent: str = "Mozilla/5.0 (compatible; RAG-Chatbot/1.0)",
    ):
        """Initialize the crawler.

        Args:
            base_url: The starting URL for the crawl
            max_pages: Maximum number of pages to crawl
            timeout: HTTP request timeout in seconds
            user_agent: User agent string for requests
        """
        self.base_url = base_url
        self.max_pages = max_pages
        self.timeout = timeout
        self.user_agent = user_agent

        # Parse base domain
        parsed = urlparse(base_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
        self.domain = parsed.netloc

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling.

        Args:
            url: URL to validate

        Returns:
            True if URL should be crawled
        """
        parsed = urlparse(url)

        # Must be same domain
        if parsed.netloc != self.domain:
            return False

        # Skip common file extensions
        skip_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
            '.css', '.js', '.zip', '.tar', '.gz', '.mp4', '.mp3',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        }
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False

        # Skip anchor links
        if '#' in url and url.split('#')[0] in [self.base_url]:
            return False

        return True

    def _clean_url(self, url: str) -> str:
        """Clean and normalize URL.

        Args:
            url: URL to clean

        Returns:
            Cleaned URL without fragment
        """
        # Remove fragment
        url = url.split('#')[0]
        # Remove trailing slash
        url = url.rstrip('/')
        return url

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from HTML.

        Args:
            soup: BeautifulSoup object

        Returns:
            Cleaned text content
        """
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract metadata from page.

        Args:
            soup: BeautifulSoup object
            url: Page URL

        Returns:
            Dict with metadata (title, description, headings, etc.)
        """
        metadata = {
            "url": url,
            "title": None,
            "description": None,
            "headings": [],
            "links": [],
        }

        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()

        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and desc_tag.get('content'):
            metadata["description"] = desc_tag.get('content').strip()

        # Headings
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text().strip()
                if text:
                    metadata["headings"].append({
                        "level": i,
                        "text": text
                    })

        # Internal links
        for link in soup.find_all('a', href=True):
            href = urljoin(url, link['href'])
            if self._is_valid_url(href):
                metadata["links"].append(self._clean_url(href))

        return metadata

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hex digest of hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def crawl_page(self, url: str) -> Optional[Dict]:
        """Crawl a single page.

        Args:
            url: URL to crawl

        Returns:
            Dict with page data or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True,
                )
                response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')

            # Extract content
            text = self._extract_text(soup)
            metadata = self._extract_metadata(soup, url)

            return {
                "url": url,
                "title": metadata["title"],
                "content": text,
                "metadata": metadata,
                "content_hash": self._compute_hash(text),
            }

        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return None

    async def crawl(self, start_url: Optional[str] = None) -> List[Dict]:
        """Crawl website starting from base URL.

        Args:
            start_url: Optional starting URL (uses base_url if not provided)

        Returns:
            List of crawled page data dicts
        """
        if start_url is None:
            start_url = self.base_url

        visited: Set[str] = set()
        to_visit: List[str] = [self._clean_url(start_url)]
        results: List[Dict] = []

        while to_visit and len(results) < self.max_pages:
            url = to_visit.pop(0)

            # Skip if already visited
            if url in visited:
                continue

            visited.add(url)

            # Crawl page
            page_data = await self.crawl_page(url)

            if page_data:
                results.append(page_data)

                # Add new links to queue
                if page_data.get("metadata", {}).get("links"):
                    for link in page_data["metadata"]["links"]:
                        clean_link = self._clean_url(link)
                        if clean_link not in visited and clean_link not in to_visit:
                            to_visit.append(clean_link)

        return results
