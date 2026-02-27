# Email Metadata Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix missing titles, sources, URLs and truncated text in email reports by enriching metadata stored in the analysis collection.

**Architecture:** Modify the analyzer's `_store_analysis()` method to include all fields needed by the email reporter. Minor fix in email reporter to handle string-to-int conversion for signal_score.

**Tech Stack:** Python, ChromaDB, pytest

---

## Task 1: Add Tests for Enriched Analysis Metadata

**Files:**
- Create: `tests/processors/test_analyzer_metadata.py`

**Step 1: Write the failing test**

```python
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

    @patch("src.processors.analyzer.get_vector_store")
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

    @patch("src.processors.analyzer.get_vector_store")
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

    @patch("src.processors.analyzer.get_vector_store")
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

    @patch("src.processors.analyzer.get_vector_store")
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

    @patch("src.processors.analyzer.get_vector_store")
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

    @patch("src.processors.analyzer.get_vector_store")
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/processors/test_analyzer_metadata.py -v`
Expected: FAIL - metadata doesn't include new fields

**Step 3: Commit test file**

```bash
git add tests/processors/test_analyzer_metadata.py
git commit -m "test: add tests for enriched analysis metadata"
```

---

## Task 2: Implement Enriched Metadata in Analyzer

**Files:**
- Modify: `src/processors/analyzer.py:190-252`

**Step 1: Modify `_store_analysis()` method**

Locate the analysis storage section (around lines 230-243) and replace:

```python
# OLD CODE (lines 230-243):
            self.vector_store.add(
                collection="analysis",
                documents=[analysis_text],
                ids=[f"analysis_{item.id}"],
                metadatas=[{
                    "item_id": item.id,
                    "source_type": item.source_type.value,
                    "actionability": result.actionability,
                    "confidence": result.confidence,
                }],
            )

# NEW CODE:
            # Build analysis metadata with all fields needed for email reporter
            analysis_metadata = {
                "item_id": item.id,
                "title": item.title,
                "source": item.source_type.value,
                "url": item.source_url,
                "summary": result.summary,
                "actionability": result.actionability,
                "confidence": result.confidence,
            }
            if item.signal_score is not None:
                analysis_metadata["signal_score"] = str(item.signal_score)

            self.vector_store.add(
                collection="analysis",
                documents=[analysis_text],
                ids=[f"analysis_{item.id}"],
                metadatas=[analysis_metadata],
            )
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/processors/test_analyzer_metadata.py -v`
Expected: All 6 tests PASS

**Step 3: Run full analyzer test suite**

Run: `pytest tests/processors/test_analyzer.py -v`
Expected: All existing tests still PASS

**Step 4: Commit**

```bash
git add src/processors/analyzer.py
git commit -m "feat: enrich analysis metadata with title, source, url, summary, signal_score"
```

---

## Task 3: Fix signal_score Int Conversion in Email Reporter

**Files:**
- Modify: `src/notifications/email_reporter.py:164-176`
- Create: `tests/notifications/test_email_reporter_metadata.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/notifications/test_email_reporter_metadata.py -v`
Expected: FAIL - signal_score returned as string "7" not int 7

**Step 3: Modify `_parse_analysis_item()`**

```python
# OLD CODE (line 169):
            signal_score=meta.get("signal_score", 5),

# NEW CODE:
            signal_score=int(meta.get("signal_score", 5)),
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/notifications/test_email_reporter_metadata.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add tests/notifications/test_email_reporter_metadata.py src/notifications/email_reporter.py
git commit -m "fix: convert signal_score to int in email reporter"
```

---

## Task 4: Integration Test

**Files:**
- None (manual verification)

**Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 2: Verify with preview (optional)**

If you have ChromaDB with data:

```bash
python main.py --mode daily --email --preview
```

Check the generated HTML in `output/email_preview/` for:
- [ ] Titles show correctly (not "Unknown")
- [ ] Sources show correctly (not "unknown")
- [ ] Links are present and functional
- [ ] Summary text is complete (not truncated)

**Step 3: Final commit (if any changes)**

```bash
git status
# Only commit if there are actual changes
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add tests for enriched metadata | `tests/processors/test_analyzer_metadata.py` |
| 2 | Implement enriched metadata | `src/processors/analyzer.py` |
| 3 | Fix signal_score int conversion | `src/notifications/email_reporter.py`, `tests/notifications/test_email_reporter_metadata.py` |
| 4 | Integration test | Manual verification |

**Total:** 4 tasks, ~15 minutes
