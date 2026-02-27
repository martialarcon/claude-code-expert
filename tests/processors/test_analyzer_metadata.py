"""Tests for analyzer metadata enrichment."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, call

from src.collectors.base import CollectedItem, SourceType
from src.processors.analyzer import Analyzer, AnalysisResult


class TestAnalysisMetadataEnrichment:
    """Test that analysis stores enriched metadata for email reporter."""

    @pytest.fixture
    def sample_item(self):
        """Create a sample collected item."""
        return CollectedItem(
            id="test-item-123",
            title="Claude 4.6 Released with New Features",
            source_type=SourceType.REDDIT,
            source_url="https://reddit.com/r/ClaudeAI/comments/abc123",
            content="Claude 4.6 introduces significant improvements...",
            summary="Claude 4.6 released with improvements",
            published_at=datetime(2026, 2, 27, 10, 0, 0),
            author="test_user",
            signal_score=8,
        )

    @pytest.fixture
    def sample_result(self):
        """Create a sample analysis result."""
        return AnalysisResult(
            item_id="test-item-123",
            summary="Claude 4.6 brings major improvements to coding capabilities.",
            key_insights=["Improved code generation", "Better context handling"],
            technical_details="FP16 inference support",
            relevance_to_claude="Direct product update",
            actionability="high",
            related_topics=["Claude", "coding"],
            confidence=0.9,
        )

    @patch("src.storage.vector_store.get_vector_store")
    def test_analysis_stores_title_in_metadata(self, mock_get_store, sample_item, sample_result):
        """Analysis metadata should include title for email reporter."""
        mock_store = Mock()
        mock_get_store.return_value = mock_store

        analyzer = Analyzer(store_results=True)
        analyzer._vector_store = mock_store
        analyzer._store_analysis(sample_item, sample_result)

        # Find the call to add analysis (second call)
        calls = mock_store.add.call_args_list
        analysis_call = [c for c in calls if c.kwargs.get("collection") == "analysis"][0]

        metadata = analysis_call.kwargs["metadatas"][0]
        assert metadata["title"] == "Claude 4.6 Released with New Features"

    @patch("src.storage.vector_store.get_vector_store")
    def test_analysis_stores_source_in_metadata(self, mock_get_store, sample_item, sample_result):
        """Analysis metadata should include source (not source_type) for email reporter."""
        mock_store = Mock()
        mock_get_store.return_value = mock_store

        analyzer = Analyzer(store_results=True)
        analyzer._vector_store = mock_store
        analyzer._store_analysis(sample_item, sample_result)

        calls = mock_store.add.call_args_list
        analysis_call = [c for c in calls if c.kwargs.get("collection") == "analysis"][0]

        metadata = analysis_call.kwargs["metadatas"][0]
        assert metadata["source"] == "reddit"

    @patch("src.storage.vector_store.get_vector_store")
    def test_analysis_stores_url_in_metadata(self, mock_get_store, sample_item, sample_result):
        """Analysis metadata should include URL for email reporter links."""
        mock_store = Mock()
        mock_get_store.return_value = mock_store

        analyzer = Analyzer(store_results=True)
        analyzer._vector_store = mock_store
        analyzer._store_analysis(sample_item, sample_result)

        calls = mock_store.add.call_args_list
        analysis_call = [c for c in calls if c.kwargs.get("collection") == "analysis"][0]

        metadata = analysis_call.kwargs["metadatas"][0]
        assert metadata["url"] == "https://reddit.com/r/ClaudeAI/comments/abc123"

    @patch("src.storage.vector_store.get_vector_store")
    def test_analysis_stores_summary_in_metadata(self, mock_get_store, sample_item, sample_result):
        """Analysis metadata should include full summary (not truncated)."""
        mock_store = Mock()
        mock_get_store.return_value = mock_store

        analyzer = Analyzer(store_results=True)
        analyzer._vector_store = mock_store
        analyzer._store_analysis(sample_item, sample_result)

        calls = mock_store.add.call_args_list
        analysis_call = [c for c in calls if c.kwargs.get("collection") == "analysis"][0]

        metadata = analysis_call.kwargs["metadatas"][0]
        assert metadata["summary"] == "Claude 4.6 brings major improvements to coding capabilities."

    @patch("src.storage.vector_store.get_vector_store")
    def test_analysis_stores_signal_score_in_metadata(self, mock_get_store, sample_item, sample_result):
        """Analysis metadata should include signal_score as string."""
        mock_store = Mock()
        mock_get_store.return_value = mock_store

        analyzer = Analyzer(store_results=True)
        analyzer._vector_store = mock_store
        analyzer._store_analysis(sample_item, sample_result)

        calls = mock_store.add.call_args_list
        analysis_call = [c for c in calls if c.kwargs.get("collection") == "analysis"][0]

        metadata = analysis_call.kwargs["metadatas"][0]
        assert metadata["signal_score"] == "8"

    @patch("src.storage.vector_store.get_vector_store")
    def test_analysis_without_signal_score(self, mock_get_store, sample_item, sample_result):
        """Analysis metadata should work when signal_score is None."""
        mock_store = Mock()
        mock_get_store.return_value = mock_store
        sample_item.signal_score = None

        analyzer = Analyzer(store_results=True)
        analyzer._vector_store = mock_store
        analyzer._store_analysis(sample_item, sample_result)

        calls = mock_store.add.call_args_list
        analysis_call = [c for c in calls if c.kwargs.get("collection") == "analysis"][0]

        metadata = analysis_call.kwargs["metadatas"][0]
        assert "signal_score" not in metadata
