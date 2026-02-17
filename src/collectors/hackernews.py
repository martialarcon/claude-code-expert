"""
AI Architect v2 - Hacker News Collector

Collects posts from Hacker News with revised filtering strategy:
- Lower threshold for stories (min_points: 30, down from v1's 50)
- Special handling for Ask HN and Show HN posts
- AI keyword filtering for relevance
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


@dataclass
class HNItem:
    """Parsed Hacker News item."""
    id: int
    title: str
    url: str | None
    text: str | None
    by: str
    score: int
    descendants: int  # Number of comments
    time: int  # Unix timestamp
    type: str  # story, ask, show, job, etc.


class HackerNewsCollector(BaseCollector[HNItem]):
    """
    Collector for Hacker News posts.

    Features:
    - Fetches from official HN Firebase API
    - Lower score threshold (30 points, down from v1's 50)
    - Special handling for Ask HN (no score filter if relevant)
    - Special handling for Show HN (check min_comments)
    - AI keyword filtering for relevance
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    # AI keywords for filtering relevant content
    AI_KEYWORDS = {
        "claude", "anthropic", "llm", "gpt", "ai", "machine learning",
        "neural", "transformer", "prompt", "agent", "rag", "embedding",
        "openai", "deepmind", "huggingface", "langchain", "artificial intelligence",
        "nlp", "computer vision", "deep learning", "tensorflow", "pytorch",
        "chatgpt", "copilot", "code generation", "llama", "mistral",
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize Hacker News collector.

        Config options:
            min_points: Minimum points for stories (default: 30)
            min_comments: Minimum comments for Ask/Show HN (default: 3)
            max_items: Maximum items to collect (default: 20)
            timeout: HTTP timeout in seconds
        """
        super().__init__(SourceType.HACKERNEWS, config)

        self.min_points = self.config.get("min_points", 30)
        self.min_comments = self.config.get("min_comments", 3)
        self.max_items = self.config.get("max_items", 20)
        self.timeout = self.config.get("timeout", 30)

    def _fetch(self) -> list[HNItem]:
        """
        Fetch posts from Hacker News.

        Returns:
            List of HNItem objects
        """
        items = []

        try:
            # Get top story IDs
            self._log.info("fetching_topstories")
            response = httpx.get(
                f"{self.BASE_URL}/topstories.json",
                timeout=self.timeout,
            )
            response.raise_for_status()
            story_ids = response.json()

            self._log.info("topstories_fetched", count=len(story_ids))

            # Fetch each item individually
            for story_id in story_ids[:self.max_items * 3]:  # Fetch more to allow for filtering
                if len(items) >= self.max_items:
                    break

                try:
                    item = self._fetch_item(story_id)
                    if item and self._should_include(item):
                        items.append(item)
                except Exception as e:
                    self._log.warning(
                        "item_fetch_error",
                        story_id=story_id,
                        error=str(e)[:100],
                    )

        except Exception as e:
            self._log.error("fetch_failed", error=str(e)[:500])
            raise

        self._log.info("items_fetched", count=len(items))
        return items

    def _fetch_item(self, item_id: int) -> HNItem | None:
        """
        Fetch a single item from HN API.

        Args:
            item_id: Hacker News item ID

        Returns:
            HNItem or None if fetch fails
        """
        try:
            response = httpx.get(
                f"{self.BASE_URL}/item/{item_id}.json",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            # Determine type from title for Ask/Show HN
            title = data.get("title", "")
            item_type = data.get("type", "story")

            if title.lower().startswith("ask hn:"):
                item_type = "ask"
            elif title.lower().startswith("show hn:"):
                item_type = "show"

            return HNItem(
                id=data.get("id", 0),
                title=title,
                url=data.get("url"),
                text=data.get("text"),
                by=data.get("by", ""),
                score=data.get("score", 0),
                descendants=data.get("descendants", 0),
                time=data.get("time", 0),
                type=item_type,
            )

        except Exception as e:
            self._log.warning("item_parse_error", item_id=item_id, error=str(e)[:100])
            return None

    def _should_include(self, item: HNItem) -> bool:
        """
        Determine if an item should be included based on type and filters.

        Args:
            item: HNItem to check

        Returns:
            True if item should be included
        """
        # Check AI relevance first
        is_relevant = self._is_ai_relevant(item)

        # Apply type-specific filtering
        if item.type == "ask":
            # Ask HN: Include if AI-relevant (no score filter)
            return is_relevant

        elif item.type == "show":
            # Show HN: Check min_comments if AI-relevant, otherwise check score too
            if is_relevant:
                return item.descendants >= self.min_comments
            else:
                return item.score >= self.min_points and item.descendants >= self.min_comments

        else:
            # Regular stories: Check min_points
            if is_relevant:
                # Lower threshold for AI-relevant content
                return item.score >= self.min_points // 2
            else:
                return item.score >= self.min_points

    def _is_ai_relevant(self, item: HNItem) -> bool:
        """
        Check if item is AI-related.

        Args:
            item: HNItem to check

        Returns:
            True if item contains AI keywords
        """
        text = f"{item.title} {item.text or ''}".lower()
        return any(keyword in text for keyword in self.AI_KEYWORDS)

    def _parse(self, raw_item: HNItem) -> CollectedItem | None:
        """
        Convert an HNItem to a CollectedItem.

        Args:
            raw_item: HNItem from fetch

        Returns:
            CollectedItem
        """
        item = raw_item

        # Use HN permalink if no external URL
        url = item.url or f"https://news.ycombinator.com/item?id={item.id}"

        # Build content
        content = f"**{item.title}**\n\n"
        if item.text:
            content += f"{item.text}\n\n"
        content += f"Posted by {item.by} | {item.score} points | {item.descendants} comments"

        # Build summary
        summary = item.title
        if item.text:
            summary += f" - {item.text[:200]}"

        # Parse timestamp
        published_at = None
        if item.time:
            try:
                published_at = datetime.fromtimestamp(item.time, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        return CollectedItem(
            id=self._compute_id(item.id),
            source_type=SourceType.HACKERNEWS,
            source_url=url,
            title=item.title,
            content=content,
            summary=summary[:500] if len(summary) > 500 else summary,
            author=item.by,
            published_at=published_at,
            metadata={
                "hn_id": item.id,
                "type": item.type,
                "score": item.score,
                "num_comments": item.descendants,
                "hn_permalink": f"https://news.ycombinator.com/item?id={item.id}",
            },
        )

    def _compute_id(self, hn_id: int) -> str:
        """Compute unique ID from HN ID."""
        return f"hn_{hn_id}"


def collect_hackernews(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect Hacker News posts.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = HackerNewsCollector(config)
    return collector.collect()
