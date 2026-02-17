"""Tests for Hacker News collector."""

from unittest.mock import patch, MagicMock

import pytest


class TestHackerNewsCollector:
    """Test HackerNewsCollector class."""

    def test_import_hackernews_collector(self):
        """Should be able to import HackerNewsCollector."""
        from src.collectors.hackernews import HackerNewsCollector
        assert HackerNewsCollector is not None

    def test_import_hn_item_dataclass(self):
        """Should be able to import HNItem dataclass."""
        from src.collectors.hackernews import HNItem
        assert HNItem is not None

    def test_initialization(self):
        """Should initialize with default values."""
        from src.collectors.hackernews import HackerNewsCollector
        from src.collectors.base import SourceType

        collector = HackerNewsCollector()
        assert collector.source_type == SourceType.HACKERNEWS
        assert collector.min_points == 30
        assert collector.min_comments == 3
        assert collector.max_items == 20

    def test_min_points_default_is_30(self):
        """Default min_points should be 30 (lowered from v1's 50)."""
        from src.collectors.hackernews import HackerNewsCollector

        collector = HackerNewsCollector()
        assert collector.min_points == 30

    def test_custom_config(self):
        """Should accept custom configuration."""
        from src.collectors.hackernews import HackerNewsCollector

        config = {
            "min_points": 100,
            "min_comments": 10,
            "max_items": 50,
        }
        collector = HackerNewsCollector(config)
        assert collector.min_points == 100
        assert collector.min_comments == 10
        assert collector.max_items == 50

    def test_collect_returns_collection_result(self):
        """collect() should return CollectionResult."""
        from src.collectors.hackernews import HackerNewsCollector
        from src.collectors.base import CollectionResult, SourceType

        collector = HackerNewsCollector()

        # Mock the _fetch method to return empty list
        with patch.object(collector, '_fetch', return_value=[]):
            result = collector.collect()

        assert isinstance(result, CollectionResult)
        assert result.source_type == SourceType.HACKERNEWS

    def test_ai_keywords_defined(self):
        """Should have AI_KEYWORDS for filtering."""
        from src.collectors.hackernews import HackerNewsCollector

        collector = HackerNewsCollector()
        assert hasattr(collector, 'AI_KEYWORDS')
        assert isinstance(collector.AI_KEYWORDS, set)
        # Should include common AI terms
        assert 'ai' in collector.AI_KEYWORDS or 'claude' in collector.AI_KEYWORDS

    def test_base_url_defined(self):
        """Should have BASE_URL for Hacker News API."""
        from src.collectors.hackernews import HackerNewsCollector

        collector = HackerNewsCollector()
        assert hasattr(collector, 'BASE_URL')
        assert 'hacker-news' in collector.BASE_URL or 'hackernews' in collector.BASE_URL.lower()

    @patch('src.collectors.hackernews.httpx')
    def test_fetch_gets_topstories(self, mock_httpx):
        """_fetch should get topstories from HN API."""
        from src.collectors.hackernews import HackerNewsCollector

        collector = HackerNewsCollector()

        # Mock the HTTP response for topstories
        mock_response = MagicMock()
        mock_response.json.return_value = [1, 2, 3]
        mock_httpx.get.return_value = mock_response

        # Mock _fetch_item to return minimal items
        with patch.object(collector, '_fetch_item') as mock_fetch_item:
            mock_fetch_item.return_value = None
            collector._fetch()

        # Verify topstories endpoint was called
        mock_httpx.get.assert_called()
        call_args = str(mock_httpx.get.call_args)
        assert 'topstories' in call_args


class TestHNItem:
    """Test HNItem dataclass."""

    def test_hn_item_has_required_fields(self):
        """HNItem should have all required fields."""
        from src.collectors.hackernews import HNItem

        item = HNItem(
            id=123,
            title="Test Story",
            url="https://example.com",
            text="Content",
            by="user",
            score=50,
            descendants=10,
            time=1700000000,
            type="story",
        )

        assert item.id == 123
        assert item.title == "Test Story"
        assert item.url == "https://example.com"
        assert item.text == "Content"
        assert item.by == "user"
        assert item.score == 50
        assert item.descendants == 10
        assert item.time == 1700000000
        assert item.type == "story"


class TestConvenienceFunction:
    """Test collect_hackernews convenience function."""

    def test_import_collect_hackernews(self):
        """Should be able to import collect_hackernews function."""
        from src.collectors.hackernews import collect_hackernews
        assert collect_hackernews is not None

    def test_collect_hackernews_returns_result(self):
        """collect_hackernews should return CollectionResult."""
        from src.collectors.hackernews import collect_hackernews
        from src.collectors.base import CollectionResult

        with patch('src.collectors.hackernews.HackerNewsCollector') as mock_collector:
            mock_instance = MagicMock()
            mock_result = MagicMock(spec=CollectionResult)
            mock_instance.collect.return_value = mock_result
            mock_collector.return_value = mock_instance

            result = collect_hackernews()

            assert result is not None
            mock_instance.collect.assert_called_once()
