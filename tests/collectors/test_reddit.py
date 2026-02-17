"""Tests for Reddit Collector."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest

from src.collectors.base import CollectionResult, SourceType


class TestRedditPost:
    """Test RedditPost dataclass."""

    def test_reddit_post_creation(self):
        """Should create RedditPost with all fields."""
        from src.collectors.reddit import RedditPost

        post = RedditPost(
            id="abc123",
            title="Test Post",
            url="https://reddit.com/r/test/abc123",
            selftext="Post content",
            subreddit="test",
            author="testuser",
            score=100,
            num_comments=50,
            created_utc=1700000000.0,
            permalink="/r/test/comments/abc123",
        )

        assert post.id == "abc123"
        assert post.title == "Test Post"
        assert post.url == "https://reddit.com/r/test/abc123"
        assert post.selftext == "Post content"
        assert post.subreddit == "test"
        assert post.author == "testuser"
        assert post.score == 100
        assert post.num_comments == 50
        assert post.created_utc == 1700000000.0
        assert post.permalink == "/r/test/comments/abc123"


class TestRedditCollectorInit:
    """Test RedditCollector initialization."""

    def test_init_with_defaults(self):
        """Should initialize with default subreddits."""
        from src.collectors.reddit import RedditCollector

        collector = RedditCollector()

        assert collector.source_type == SourceType.REDDIT
        assert "LocalLLaMA" in collector.subreddits
        assert "ClaudeAI" in collector.subreddits
        assert collector.min_comments == 5
        assert collector.min_score == 10
        assert collector.max_items == 20

    def test_init_with_custom_config(self):
        """Should accept custom configuration."""
        from src.collectors.reddit import RedditCollector

        config = {
            "subreddits": ["CustomSub"],
            "min_comments": 10,
            "min_score": 50,
            "max_items": 50,
        }

        collector = RedditCollector(config=config)

        assert collector.subreddits == ["CustomSub"]
        assert collector.min_comments == 10
        assert collector.min_score == 50
        assert collector.max_items == 50

    def test_default_subreddits_constant(self):
        """Should have default subreddits as class constant."""
        from src.collectors.reddit import RedditCollector

        assert "LocalLLaMA" in RedditCollector.DEFAULT_SUBREDDITS
        assert "ClaudeAI" in RedditCollector.DEFAULT_SUBREDDITS


class TestRedditCollectorMinComments:
    """Test min_comments filter."""

    def test_min_comments_filters_low_comment_posts(self):
        """Should filter posts with fewer comments than min_comments."""
        from src.collectors.reddit import RedditCollector, RedditPost

        # Use single subreddit to avoid mock being called multiple times
        collector = RedditCollector(config={
            "min_comments": 5,
            "subreddits": ["test"],  # Single subreddit
        })

        # Mock response with low comment post
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "low_comments",
                            "title": "Low Comment Post",
                            "url": "https://reddit.com/r/test/low",
                            "selftext": "Content",
                            "subreddit": "test",
                            "author": "user",
                            "score": 100,
                            "num_comments": 2,  # Below threshold
                            "created_utc": 1700000000.0,
                            "permalink": "/r/test/comments/low",
                        }
                    },
                    {
                        "kind": "t3",
                        "data": {
                            "id": "high_comments",
                            "title": "High Comment Post with Claude AI keywords",
                            "url": "https://reddit.com/r/test/high",
                            "selftext": "Claude LLM discussion",
                            "subreddit": "test",
                            "author": "user",
                            "score": 100,
                            "num_comments": 20,  # Above threshold
                            "created_utc": 1700000000.0,
                            "permalink": "/r/test/comments/high",
                        }
                    }
                ]
            }
        }

        with patch("httpx.get", return_value=mock_response):
            items = collector._fetch()

            # Only the high comment post should pass
            assert len(items) == 1
            assert items[0].id == "high_comments"


class TestRedditCollectorCollect:
    """Test RedditCollector collect method."""

    def test_collect_returns_collection_result(self):
        """Should return CollectionResult with items."""
        from src.collectors.reddit import RedditCollector

        collector = RedditCollector()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "test123",
                            "title": "Claude AI Discussion",
                            "url": "https://reddit.com/r/ClaudeAI/test123",
                            "selftext": "Discussion about Claude LLM",
                            "subreddit": "ClaudeAI",
                            "author": "testuser",
                            "score": 50,
                            "num_comments": 10,
                            "created_utc": 1700000000.0,
                            "permalink": "/r/ClaudeAI/comments/test123",
                        }
                    }
                ]
            }
        }

        with patch("httpx.get", return_value=mock_response):
            result = collector.collect()

        assert isinstance(result, CollectionResult)
        assert result.source_type == SourceType.REDDIT

    def test_collect_with_empty_response(self):
        """Should handle empty response gracefully."""
        from src.collectors.reddit import RedditCollector

        collector = RedditCollector()

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"children": []}}

        with patch("httpx.get", return_value=mock_response):
            result = collector.collect()

        assert isinstance(result, CollectionResult)
        assert result.total_count == 0


class TestRedditCollectorParse:
    """Test _parse method."""

    def test_parse_creates_collected_item_with_metadata(self):
        """Should create CollectedItem with Reddit-specific metadata."""
        from src.collectors.reddit import RedditCollector, RedditPost

        collector = RedditCollector()

        post = RedditPost(
            id="test123",
            title="Test Post",
            url="https://reddit.com/r/test/test123",
            selftext="Test content",
            subreddit="test",
            author="testuser",
            score=100,
            num_comments=50,
            created_utc=1700000000.0,
            permalink="/r/test/comments/test123",
        )

        item = collector._parse(post)

        assert item is not None
        assert item.title == "Test Post"
        assert item.source_url == "https://reddit.com/r/test/test123"
        assert item.author == "testuser"
        assert item.metadata["subreddit"] == "test"
        assert item.metadata["score"] == 100
        assert item.metadata["num_comments"] == 50
        assert "comment_score_ratio" in item.metadata

    def test_parse_calculates_comment_score_ratio(self):
        """Should calculate comment/score ratio in metadata."""
        from src.collectors.reddit import RedditCollector, RedditPost

        collector = RedditCollector()

        # Post with 100 score and 50 comments = 0.5 ratio
        post = RedditPost(
            id="ratio_test",
            title="Ratio Test",
            url="https://reddit.com/r/test/ratio",
            selftext="Content",
            subreddit="test",
            author="user",
            score=100,
            num_comments=50,
            created_utc=1700000000.0,
            permalink="/r/test/comments/ratio",
        )

        item = collector._parse(post)

        assert item.metadata["comment_score_ratio"] == 0.5


class TestRedditCollectorKeywords:
    """Test AI keyword filtering."""

    def test_ai_keywords_constant_exists(self):
        """Should have AI_KEYWORDS class constant."""
        from src.collectors.reddit import RedditCollector

        assert hasattr(RedditCollector, "AI_KEYWORDS")
        assert "claude" in RedditCollector.AI_KEYWORDS
        assert "llm" in RedditCollector.AI_KEYWORDS


class TestConvenienceFunction:
    """Test collect_reddit convenience function."""

    def test_collect_reddit_function_exists(self):
        """Should have collect_reddit convenience function."""
        from src.collectors.reddit import collect_reddit

        assert callable(collect_reddit)

    def test_collect_reddit_returns_result(self):
        """Should return CollectionResult."""
        from src.collectors.reddit import collect_reddit

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"children": []}}

        with patch("httpx.get", return_value=mock_response):
            result = collect_reddit()

        assert isinstance(result, CollectionResult)
        assert result.source_type == SourceType.REDDIT


class TestRedditCollectorUserAgent:
    """Test User-Agent header requirement."""

    def test_fetch_uses_user_agent_header(self):
        """Should include User-Agent header in requests."""
        from src.collectors.reddit import RedditCollector

        collector = RedditCollector()

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"children": []}}

        with patch("httpx.get", return_value=mock_response) as mock_get:
            collector._fetch()

            # Verify User-Agent was passed
            call_kwargs = mock_get.call_args[1]
            assert "headers" in call_kwargs
            assert "User-Agent" in call_kwargs["headers"]
