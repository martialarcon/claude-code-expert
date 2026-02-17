"""
AI Architect v2 - Blogs/RSS Collector

Collects posts from RSS feeds including Simon Willison's blog and AI newsletters.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


@dataclass
class FeedItem:
    """Parsed feed item."""
    title: str
    url: str
    content: str
    author: str | None
    published_at: datetime | None
    feed_name: str


class BlogsCollector(BaseCollector[FeedItem]):
    """
    Collector for RSS/Atom feeds from blogs and newsletters.

    Supports:
    - RSS 2.0 and Atom feeds
    - Content extraction from full posts
    - Simon Willison's blog as primary source
    - AI newsletters (Import AI, The Batch, etc.)
    """

    DEFAULT_FEEDS = [
        {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/"},
        {"name": "Anthropic Blog", "url": "https://www.anthropic.com/news/rss"},
    ]

    # AI keywords for filtering relevant content
    AI_KEYWORDS = {
        "claude", "anthropic", "llm", "gpt", "ai", "machine learning",
        "neural", "transformer", "prompt", "agent", "rag", "embedding",
        "openai", "deepmind", "huggingface", "langchain",
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize blogs collector.

        Config options:
            feeds: List of {name, url} feed configs
            max_items: Maximum items per feed
            filter_ai_only: Only collect AI-related posts
            fetch_full_content: Fetch full article content
            timeout: HTTP timeout in seconds
        """
        super().__init__(SourceType.BLOGS, config)

        self.feeds = self.config.get("feeds", self.DEFAULT_FEEDS)
        self.max_items = self.config.get("max_items", 20)
        self.filter_ai_only = self.config.get("filter_ai_only", True)
        self.fetch_full_content = self.config.get("fetch_full_content", False)
        self.timeout = self.config.get("timeout", 30)

    def _fetch(self) -> list[FeedItem]:
        """
        Fetch posts from all configured feeds.

        Returns:
            List of FeedItem objects
        """
        items = []

        for feed_config in self.feeds:
            try:
                feed_items = self._fetch_feed(feed_config)
                items.extend(feed_items)
            except Exception as e:
                self._log.warning(
                    "feed_fetch_failed",
                    feed=feed_config.get("name", "unknown"),
                    error=str(e)[:200],
                )

        return items[:self.max_items]

    def _fetch_feed(self, feed_config: dict[str, str]) -> list[FeedItem]:
        """
        Fetch items from a single feed.

        Args:
            feed_config: {name, url} configuration

        Returns:
            List of FeedItems
        """
        items = []
        feed_name = feed_config.get("name", "Unknown")
        feed_url = feed_config.get("url")

        if not feed_url:
            return items

        self._log.info("fetching_feed", feed=feed_name)

        # Parse the feed
        feed = feedparser.parse(feed_url)

        if feed.bozo and feed.bozo_exception:
            self._log.warning(
                "feed_parse_warning",
                feed=feed_name,
                error=str(feed.bozo_exception)[:200],
            )

        for entry in feed.entries[:self.max_items]:
            try:
                item = self._parse_entry(entry, feed_name)
                if item and self._is_relevant(item):
                    items.append(item)
            except Exception as e:
                self._log.warning(
                    "entry_parse_error",
                    feed=feed_name,
                    error=str(e)[:100],
                )

        return items

    def _parse_entry(self, entry: Any, feed_name: str) -> FeedItem | None:
        """
        Parse a feed entry into a FeedItem.

        Args:
            entry: feedparser entry
            feed_name: Name of the feed

        Returns:
            FeedItem or None
        """
        # Get title
        title = getattr(entry, "title", None)
        if not title:
            return None

        # Get URL
        url = None
        if hasattr(entry, "link"):
            url = entry.link
        elif hasattr(entry, "links") and entry.links:
            url = entry.links[0].get("href")

        if not url:
            return None

        # Get content
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description

        # Clean HTML
        content = self._clean_html(content)

        # Get author
        author = None
        if hasattr(entry, "author"):
            author = entry.author
        elif hasattr(entry, "dc_creator"):
            author = entry.dc_creator

        # Get published date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                published_at = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

        return FeedItem(
            title=title,
            url=url,
            content=content,
            author=author,
            published_at=published_at,
            feed_name=feed_name,
        )

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags and clean up content."""
        # Remove script and style tags with content
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove all other tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _is_relevant(self, item: FeedItem) -> bool:
        """Check if item is AI-related (if filtering is enabled)."""
        if not self.filter_ai_only:
            return True

        text = f"{item.title} {item.content}".lower()
        return any(keyword in text for keyword in self.AI_KEYWORDS)

    def _parse(self, raw_item: FeedItem) -> CollectedItem | None:
        """
        Convert a FeedItem to a CollectedItem.

        Args:
            raw_item: FeedItem

        Returns:
            CollectedItem
        """
        item = raw_item

        return CollectedItem(
            id=self._compute_id(item.url),
            source_type=SourceType.BLOGS,
            source_url=item.url,
            title=item.title,
            content=f"**{item.feed_name}**\n\n{item.content}",
            summary=item.content[:500] if len(item.content) > 500 else item.content,
            author=item.author,
            published_at=item.published_at,
            metadata={
                "feed_name": item.feed_name,
                "domain": urlparse(item.url).netloc,
            },
        )

    def _compute_id(self, url: str) -> str:
        """Compute unique ID from URL."""
        import hashlib
        return f"blog_{hashlib.sha256(url.encode()).hexdigest()[:16]}"


def collect_blogs(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect blog posts.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = BlogsCollector(config)
    return collector.collect()
