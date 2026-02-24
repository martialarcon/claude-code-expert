"""Tests for chroma_query helper module."""

import pytest
from src.utils.chroma_query import (
    ChromaQueryError,
    QueryResult,
    query_chromadb,
)


class TestQueryResult:
    """Test QueryResult dataclass."""

    def test_query_result_creation(self):
        """Should create QueryResult with all fields."""
        result = QueryResult(
            title="Test Title",
            content="Test content",
            source="items",
            score=0.85,
            metadata={"date": "2026-02-24"},
        )
        assert result.title == "Test Title"
        assert result.score == 0.85


class TestQueryChromaDB:
    """Test query_chromadb function."""

    def test_query_returns_list_of_results(self, tmp_path):
        """Should return list of QueryResult objects."""
        from src.storage.vector_store import VectorStore

        # Setup test store
        vs = VectorStore(persist_directory=str(tmp_path / "chroma"))
        vs.add(
            collection="items",
            documents=["Claude Code is an AI assistant for coding"],
            ids=["test-1"],
            metadatas=[{"title": "Test Doc", "source_type": "docs"}],
        )

        results = query_chromadb(
            query="coding assistant",
            collections=["items"],
            persist_directory=str(tmp_path / "chroma"),
            n_results=5,
        )

        assert isinstance(results, list)
        assert len(results) >= 1
        assert all(isinstance(r, QueryResult) for r in results)

    def test_query_with_days_filter(self, tmp_path):
        """Should filter results by days."""
        from datetime import datetime, timedelta
        from src.storage.vector_store import VectorStore

        vs = VectorStore(persist_directory=str(tmp_path / "chroma"))

        # Old item
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        vs.add(
            collection="items",
            documents=["Old content"],
            ids=["old-1"],
            metadatas=[{"title": "Old", "date": old_date}],
        )

        # Recent item
        recent_date = datetime.now().isoformat()
        vs.add(
            collection="items",
            documents=["Recent content"],
            ids=["recent-1"],
            metadatas=[{"title": "Recent", "date": recent_date}],
        )

        results = query_chromadb(
            query="content",
            collections=["items"],
            persist_directory=str(tmp_path / "chroma"),
            n_results=5,
            days=7,
        )

        # Should only return recent item
        assert len(results) == 1
        assert results[0].title == "Recent"

    def test_query_multiple_collections(self, tmp_path):
        """Should search across multiple collections."""
        from src.storage.vector_store import VectorStore

        vs = VectorStore(persist_directory=str(tmp_path / "chroma"))
        vs.add(
            collection="items",
            documents=["Item document"],
            ids=["item-1"],
            metadatas=[{"title": "Item"}],
        )
        vs.add(
            collection="analysis",
            documents=["Analysis document"],
            ids=["analysis-1"],
            metadatas=[{"title": "Analysis"}],
        )

        results = query_chromadb(
            query="document",
            collections=["items", "analysis"],
            persist_directory=str(tmp_path / "chroma"),
            n_results=5,
        )

        assert len(results) >= 2


class TestFormatResults:
    """Test result formatting."""

    def test_format_empty_results(self):
        """Should handle empty results gracefully."""
        from src.utils.chroma_query import format_results_markdown

        output = format_results_markdown([], "test query")
        assert "No se encontraron resultados" in output

    def test_format_with_results(self):
        """Should format results in markdown."""
        from src.utils.chroma_query import format_results_markdown

        results = [
            QueryResult(
                title="Test Title",
                content="Test content here",
                source="items",
                score=0.92,
                metadata={"date": "2026-02-24", "source_type": "blog"},
            )
        ]

        output = format_results_markdown(results, "test query")

        assert "## Resumen" in output
        assert "## Fuentes" in output
        assert "Test Title" in output
        assert "0.92" in output


class TestChromaQueryError:
    """Test ChromaQueryError exception."""

    def test_error_is_exception(self):
        """Should be an exception type."""
        assert issubclass(ChromaQueryError, Exception)

    def test_error_with_message(self):
        """Should accept message argument."""
        error = ChromaQueryError("Test error")
        assert str(error) == "Test error"
