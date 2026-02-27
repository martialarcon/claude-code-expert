"""Tests for email reporter metadata parsing."""
import pytest

from src.notifications.email_reporter import EmailReporter


class TestParseAnalysisItem:
    """Test _parse_analysis_item handles metadata correctly."""

    @pytest.fixture
    def reporter(self, tmp_path):
        """Create email reporter with temp directories."""
        from pathlib import Path
        return EmailReporter(
            template_dir=Path(__file__).parent.parent.parent / "src" / "notifications" / "templates",
            persist_directory=tmp_path / "chroma",
        )

    def test_signal_score_converted_to_int(self, reporter):
        """signal_score from ChromaDB (string) should be converted to int."""
        meta = {
            "title": "Test Title",
            "source": "reddit",
            "signal_score": "7",  # ChromaDB stores as string
            "summary": "Test summary",
        }
        doc = "Document content"

        item = reporter._parse_analysis_item(doc, meta)

        assert item.signal_score == 7
        assert isinstance(item.signal_score, int)

    def test_signal_score_default_when_missing(self, reporter):
        """signal_score should default to 5 when not in metadata."""
        meta = {
            "title": "Test Title",
            "source": "reddit",
            "summary": "Test summary",
        }
        doc = "Document content"

        item = reporter._parse_analysis_item(doc, meta)

        assert item.signal_score == 5

    def test_full_metadata_parsed_correctly(self, reporter):
        """All enriched metadata fields should be parsed correctly."""
        meta = {
            "title": "Claude 4.6 Released",
            "source": "hackernews",
            "url": "https://news.ycombinator.com/item?id=123",
            "summary": "Full summary text that is not truncated",
            "signal_score": "9",
            "actionability": "high",
            "key_insights": ["Insight 1", "Insight 2"],
        }
        doc = "Document content"

        item = reporter._parse_analysis_item(doc, meta)

        assert item.title == "Claude 4.6 Released"
        assert item.source == "hackernews"
        assert item.url == "https://news.ycombinator.com/item?id=123"
        assert item.summary == "Full summary text that is not truncated"
        assert item.signal_score == 9
        assert item.actionability == "high"
