"""
AI Architect v2 - Reddit Collector

Collects posts from relevant subreddits with focus on high discussion ratio.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


@dataclass
class RedditPost:
    """Parsed Reddit post."""
    id: str
    title: str
    url: str
    selftext: str
    subreddit: str
    author: str
    score: int
    num_comments: int
    created_utc: float
    permalink: str


class RedditCollector(BaseCollector[RedditPost]):
    """
    Collector for Reddit posts from AI-related subreddits.

    Focuses on posts with high engagement (comments/score ratio) to find
    discussions that generate meaningful conversation.

    Supports:
    - Multiple subreddit sources
    - Comment/score ratio filtering
    - AI keyword relevance filtering
    - Configurable thresholds
    """

    DEFAULT_SUBREDDITS = ["LocalLLaMA", "ClaudeAI"]

    # AI keywords for filtering relevant content
    AI_KEYWORDS = {
        "claude", "anthropic", "llm", "gpt", "ai", "machine learning",
        "neural", "transformer", "prompt", "agent", "rag", "embedding",
        "openai", "deepmind", "huggingface", "langchain", "code llama",
        "mistral", "llama", "gemini", "copilot", "cursor",
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize Reddit collector.

        Config options:
            subreddits: List of subreddit names (without r/)
            min_comments: Minimum comments threshold
            min_score: Minimum score threshold
            max_items: Maximum items to collect
            timeout: HTTP timeout in seconds
        """
        super().__init__(SourceType.REDDIT, config)

        self.subreddits = self.config.get("subreddits", self.DEFAULT_SUBREDDITS)
        self.min_comments = self.config.get("min_comments", 5)
        self.min_score = self.config.get("min_score", 10)
        self.max_items = self.config.get("max_items", 20)
        self.timeout = self.config.get("timeout", 30)

    def _fetch(self) -> list[RedditPost]:
        """
        Fetch posts from all configured subreddits.

        Returns:
            List of RedditPost objects
        """
        items = []
        headers = {
            "User-Agent": "AI-Architect-Collector/1.0 (knowledge gathering bot)"
        }

        for subreddit in self.subreddits:
            try:
                subreddit_items = self._fetch_subreddit(subreddit, headers)
                items.extend(subreddit_items)
            except Exception as e:
                self._log.warning(
                    "subreddit_fetch_failed",
                    subreddit=subreddit,
                    error=str(e)[:200],
                )

        return items[:self.max_items]

    def _fetch_subreddit(
        self, subreddit: str, headers: dict[str, str]
    ) -> list[RedditPost]:
        """
        Fetch posts from a single subreddit.

        Args:
            subreddit: Subreddit name (without r/)
            headers: HTTP headers including User-Agent

        Returns:
            List of RedditPosts
        """
        items = []
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"

        self._log.info("fetching_subreddit", subreddit=subreddit)

        response = httpx.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        children = data.get("data", {}).get("children", [])

        for child in children:
            if child.get("kind") != "t3":
                continue

            post_data = child.get("data", {})

            # Apply filters
            score = post_data.get("score", 0)
            num_comments = post_data.get("num_comments", 0)

            if score < self.min_score:
                continue
            if num_comments < self.min_comments:
                continue

            # Check relevance
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")
            if not self._is_relevant(title, selftext):
                continue

            post = RedditPost(
                id=post_data.get("id", ""),
                title=title,
                url=post_data.get("url", f"https://reddit.com{post_data.get('permalink', '')}"),
                selftext=selftext,
                subreddit=post_data.get("subreddit", subreddit),
                author=post_data.get("author", "[deleted]"),
                score=score,
                num_comments=num_comments,
                created_utc=post_data.get("created_utc", 0.0),
                permalink=post_data.get("permalink", ""),
            )
            items.append(post)

        return items

    def _is_relevant(self, title: str, selftext: str) -> bool:
        """
        Check if post is AI-related based on keywords.

        Args:
            title: Post title
            selftext: Post body text

        Returns:
            True if post contains AI keywords
        """
        text = f"{title} {selftext}".lower()
        return any(keyword in text for keyword in self.AI_KEYWORDS)

    def _parse(self, raw_item: RedditPost) -> CollectedItem | None:
        """
        Convert a RedditPost to a CollectedItem.

        Args:
            raw_item: RedditPost to convert

        Returns:
            CollectedItem with Reddit metadata
        """
        post = raw_item

        # Calculate comment/score ratio (higher = more discussion)
        comment_score_ratio = 0.0
        if post.score > 0:
            comment_score_ratio = round(post.num_comments / post.score, 3)

        # Build full Reddit URL if permalink is relative
        source_url = post.url
        if post.permalink and not post.url.startswith("https://reddit.com"):
            source_url = f"https://reddit.com{post.permalink}"

        # Parse timestamp
        published_at = None
        if post.created_utc:
            try:
                published_at = datetime.fromtimestamp(
                    post.created_utc, tz=timezone.utc
                )
            except (TypeError, ValueError):
                pass

        # Build content
        content = f"**r/{post.subreddit}** | Score: {post.score} | Comments: {post.num_comments}\n\n"
        content += f"{post.selftext}" if post.selftext else post.title

        return CollectedItem(
            id=self._compute_id(post.id),
            source_type=SourceType.REDDIT,
            source_url=source_url,
            title=post.title,
            content=content,
            summary=post.selftext[:500] if post.selftext and len(post.selftext) > 500 else post.selftext,
            author=post.author,
            published_at=published_at,
            metadata={
                "subreddit": post.subreddit,
                "score": post.score,
                "num_comments": post.num_comments,
                "comment_score_ratio": comment_score_ratio,
                "reddit_id": post.id,
                "permalink": post.permalink,
            },
        )

    def _compute_id(self, reddit_id: str) -> str:
        """Compute unique ID from Reddit ID."""
        import hashlib
        return f"reddit_{hashlib.sha256(reddit_id.encode()).hexdigest()[:16]}"


def collect_reddit(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect Reddit posts.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = RedditCollector(config)
    return collector.collect()
