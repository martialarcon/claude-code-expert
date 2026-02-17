"""
AI Architect v2 - Documentation Collector

Collects official documentation and detects changes via diff.
"""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, CollectedItem, CollectionError, CollectionResult, SourceType

# BeautifulSoup type hints
from bs4.element import Tag


class DocsCollector(BaseCollector[str]):
    """
    Collector for official documentation.

    Fetches documentation pages, detects changes by comparing with
    previous snapshots, and creates items for changed/new content.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize docs collector.

        Config options:
            sources: List of documentation URLs to monitor
            snapshot_dir: Directory to store snapshots
            max_items: Maximum items per run
            timeout: HTTP timeout in seconds
        """
        super().__init__(SourceType.DOCS, config)

        self.sources = self.config.get("sources", [
            "https://docs.anthropic.com",
            "https://docs.claude.ai",
        ])
        self.snapshot_dir = Path(self.config.get("snapshot_dir", "data/snapshots/docs"))
        self.max_items = self.config.get("max_items", 50)
        self.timeout = self.config.get("timeout", 30)

        # Ensure snapshot directory exists
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Common documentation paths to check
        self.doc_paths = [
            "/en/docs/about-claude",
            "/en/docs/build-with-claude",
            "/en/docs/reference",
            "/en/api",
            "/en/docs",
            "/docs/introduction",
            "/docs/quickstart",
            "/docs/api",
        ]

    def _fetch(self) -> list[str]:
        """
        Fetch documentation pages from all configured sources.

        Returns:
            List of page URLs that have content
        """
        pages = []

        for source_url in self.sources:
            try:
                discovered = self._discover_pages(source_url)
                pages.extend(discovered)
            except Exception as e:
                self._log.warning(
                    "source_fetch_failed",
                    source=source_url,
                    error=str(e)[:200],
                )

        return pages[:self.max_items]

    def _discover_pages(self, base_url: str) -> list[str]:
        """
        Discover documentation pages from a base URL.

        Args:
            base_url: Base documentation URL

        Returns:
            List of discovered page URLs
        """
        discovered = []

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            # Try to fetch the sitemap first
            sitemap_url = f"{base_url}/sitemap.xml"
            try:
                response = client.get(sitemap_url)
                if response.status_code == 200:
                    sitemap_pages = self._parse_sitemap(response.text, base_url)
                    discovered.extend(sitemap_pages)
            except httpx.HTTPError:
                pass

            # If no sitemap or not enough pages, try common paths
            if len(discovered) < 5:
                for path in self.doc_paths:
                    url = f"{base_url}{path}"
                    try:
                        response = client.head(url)
                        if response.status_code == 200:
                            discovered.append(url)
                    except httpx.HTTPError:
                        continue

        return discovered

    def _parse_sitemap(self, sitemap_xml: str, base_url: str) -> list[str]:
        """
        Parse XML sitemap and extract URLs.

        Args:
            sitemap_xml: Sitemap XML content
            base_url: Base URL to filter by

        Returns:
            List of URLs from sitemap
        """
        urls = []
        soup = BeautifulSoup(sitemap_xml, "xml")

        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if url.startswith(base_url):
                urls.append(url)

        return urls

    def _parse(self, raw_item: str) -> CollectedItem | None:
        """
        Parse a documentation page URL into a CollectedItem.

        Args:
            raw_item: Page URL

        Returns:
            CollectedItem if page has new/changed content
        """
        url = raw_item

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    return None

                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract title
                title = self._extract_title(soup)
                if not title:
                    title = url.split("/")[-1] or "Documentation"

                # Extract main content
                content = self._extract_content(soup)
                if not content:
                    return None

                # Compute content hash
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                # Check for changes against snapshot
                snapshot_path = self._get_snapshot_path(url)
                if snapshot_path.exists():
                    stored_hash = snapshot_path.read_text().strip()
                    if stored_hash == content_hash:
                        # No changes
                        return None

                # Save new snapshot
                snapshot_path.write_text(content_hash)

                # Create item for changed/new content
                return CollectedItem(
                    id=self._compute_id(url, content_hash),
                    source_type=SourceType.DOCS,
                    source_url=url,
                    title=title,
                    content=content,
                    author=None,
                    published_at=datetime.now(timezone.utc),
                    metadata={
                        "content_hash": content_hash[:16],
                        "is_change": snapshot_path.exists(),
                    },
                )

        except httpx.HTTPError as e:
            self._log.warning(
                "page_fetch_failed",
                url=url,
                error=str(e)[:200],
            )
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract page title from HTML."""
        # Try h1 first
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Try title tag
        title = soup.find("title")
        if title:
            return title.get_text(strip=True)

        return None

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from HTML page.

        Tries to find the main content area and extract clean text.
        """
        # Remove script, style, nav, footer elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Try to find main content area
        main_content = (
            soup.find("main") or
            soup.find("article") or
            soup.find(class_=re.compile(r"content|docs|documentation")) or
            soup.find(id=re.compile(r"content|docs|main"))
        )

        if main_content:
            # Get text content
            text = main_content.get_text(separator="\n", strip=True)
            # Clean up whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text

        # Fallback to body
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text

        return ""

    def _get_snapshot_path(self, url: str) -> Path:
        """Get the snapshot file path for a URL."""
        # Create safe filename from URL
        safe_name = re.sub(r"[^\w\-]", "_", url)
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")[:100]
        return self.snapshot_dir / f"{safe_name}.hash"

    def _compute_id(self, url: str, content_hash: str) -> str:
        """Compute unique ID for a documentation page."""
        hash_input = f"docs:{url}:{content_hash[:8]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def collect_docs(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect documentation.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = DocsCollector(config)
    return collector.collect()
