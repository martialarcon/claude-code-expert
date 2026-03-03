# ntfy Detailed Notification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add complete item details (titles, sources, URLs, summaries) to ntfy notifications after daily analysis.

**Architecture:** Modify `notify_daily_complete()` to accept optional `items` parameter with item details. Update `main.py` to build items list from analyzed results and pass to notifier. TDD approach with unit tests.

**Tech Stack:** Python 3.12, pytest, httpx (for mocking), ntfy.sh

---

## Task 1: Write test for `notify_daily_complete` with items

**Files:**
- Create: `tests/utils/test_notifier.py`

**Step 1: Create test file with failing test**

```python
"""Tests for Notifier."""
import pytest
from unittest.mock import patch, MagicMock

from src.utils.notifier import Notifier, Priority


class TestNotifyDailyComplete:
    """Tests for notify_daily_complete method."""

    @pytest.fixture
    def notifier(self):
        """Create notifier instance for testing."""
        return Notifier(topic="test-topic", enabled=True)

    def test_notify_daily_complete_without_items(self, notifier):
        """Test notification without items parameter (backward compatibility)."""
        with patch.object(notifier, 'send') as mock_send:
            mock_send.return_value = True

            result = notifier.notify_daily_complete(
                date="2026-03-04",
                items_analyzed=5,
                items_discarded=10,
                relevance_score=7,
                highlight="Test highlight",
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            message = call_args.kwargs['message']

            assert "2026-03-04" in call_args.kwargs['title']
            assert "5 analyzed" in message
            assert "10 discarded" in message
            assert "7/10" in message
            assert "Test highlight" in message

    def test_notify_daily_complete_with_items(self, notifier):
        """Test notification with detailed items."""
        with patch.object(notifier, 'send') as mock_send:
            mock_send.return_value = True

            items = [
                {
                    "title": "Claude 4.6 Released with New Features",
                    "source": "hackernews",
                    "url": "https://news.ycombinator.com/item?id=123",
                    "summary": "Anthropic releases Claude 4.6 with improved reasoning capabilities",
                    "signal_score": 9,
                },
                {
                    "title": "New MCP Server for Database Integration",
                    "source": "github",
                    "url": "https://github.com/example/mcp-db",
                    "summary": "A new MCP server for database connectivity",
                    "signal_score": 7,
                },
            ]

            result = notifier.notify_daily_complete(
                date="2026-03-04",
                items_analyzed=2,
                items_discarded=5,
                relevance_score=8,
                highlight="Great day for AI news",
                items=items,
            )

            assert result is True
            mock_send.assert_called_once()
            message = mock_send.call_args.kwargs['message']

            # Check that item details are included
            assert "Claude 4.6 Released with New Features" in message
            assert "hackernews" in message
            assert "9/10" in message
            assert "https://news.ycombinator.com/item?id=123" in message
            assert "Anthropic releases Claude 4.6" in message

    def test_notify_daily_complete_limits_items_to_five(self, notifier):
        """Test that only first 5 items are included."""
        with patch.object(notifier, 'send') as mock_send:
            mock_send.return_value = True

            # Create 10 items
            items = [
                {"title": f"Item {i}", "source": "test", "signal_score": 5}
                for i in range(10)
            ]

            notifier.notify_daily_complete(
                date="2026-03-04",
                items_analyzed=10,
                items_discarded=0,
                relevance_score=5,
                items=items,
            )

            message = mock_send.call_args.kwargs['message']

            # Should include first 5 items
            assert "Item 0" in message
            assert "Item 4" in message
            # Should NOT include items 5-9
            assert "Item 5" not in message
            assert "Item 9" not in message

    def test_notify_daily_complete_truncates_long_text(self, notifier):
        """Test that long text is truncated properly."""
        with patch.object(notifier, 'send') as mock_send:
            mock_send.return_value = True

            long_title = "A" * 100
            long_url = "https://example.com/" + "b" * 100
            long_summary = "C" * 200

            items = [
                {
                    "title": long_title,
                    "source": "test",
                    "url": long_url,
                    "summary": long_summary,
                    "signal_score": 5,
                }
            ]

            notifier.notify_daily_complete(
                date="2026-03-04",
                items_analyzed=1,
                items_discarded=0,
                relevance_score=5,
                items=items,
            )

            message = mock_send.call_args.kwargs['message']

            # Title should be truncated to 60 chars
            assert "A" * 60 in message
            assert "A" * 61 not in message

            # Summary should be truncated to 100 chars
            assert "C" * 100 in message
            assert "C" * 101 not in message

    def test_notify_daily_complete_handles_missing_fields(self, notifier):
        """Test that missing optional fields don't cause errors."""
        with patch.object(notifier, 'send') as mock_send:
            mock_send.return_value = True

            items = [
                {
                    "title": "Minimal Item",
                    "source": "test",
                    "signal_score": 5,
                    # No url, no summary
                }
            ]

            result = notifier.notify_daily_complete(
                date="2026-03-04",
                items_analyzed=1,
                items_discarded=0,
                relevance_score=5,
                items=items,
            )

            assert result is True
            message = mock_send.call_args.kwargs['message']
            assert "Minimal Item" in message
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_notifier.py -v`
Expected: FAIL - `test_notify_daily_complete_with_items` fails because `items` parameter doesn't exist yet

**Step 3: Commit test file**

```bash
git add tests/utils/test_notifier.py
git commit -m "test: add tests for ntfy detailed notification"
```

---

## Task 2: Implement `items` parameter in `notify_daily_complete`

**Files:**
- Modify: `src/utils/notifier.py:118-157`

**Step 1: Update method signature and implementation**

Replace the `notify_daily_complete` method (lines 118-157) with:

```python
    def notify_daily_complete(
        self,
        date: str,
        items_analyzed: int,
        items_discarded: int,
        relevance_score: int,
        highlight: str | None = None,
        items: list[dict] | None = None,
    ) -> bool:
        """
        Send daily cycle completion notification.

        Args:
            date: Date string
            items_analyzed: Number of items analyzed
            items_discarded: Number of items discarded
            relevance_score: Day's relevance score (1-10)
            highlight: Optional highlight text
            items: Optional list of dicts with keys:
                - title: str
                - source: str
                - url: str (optional)
                - summary: str (optional)
                - signal_score: int

        Returns:
            True if sent successfully
        """
        title = f"AI Architect - {date}"

        lines = [
            "Daily cycle complete",
            f"Items: {items_analyzed} analyzed, {items_discarded} discarded",
            f"Relevance: {relevance_score}/10",
        ]

        if highlight:
            lines.append(f"Highlight: {highlight[:100]}")

        # Add detailed items section
        if items:
            lines.append("")
            lines.append("Items analizados:")
            for item in items[:5]:  # Limit to 5 for readability
                title_text = item.get('title', 'Unknown')[:60]
                source = item.get('source', 'unknown')
                score = item.get('signal_score', 5)
                lines.append(f"- {title_text}")
                lines.append(f"  Fuente: {source} | Score: {score}/10")
                if item.get('url'):
                    lines.append(f"  URL: {item['url'][:60]}")
                if item.get('summary'):
                    lines.append(f"  {item['summary'][:100]}...")

        message = "\n".join(lines)

        return self.send(
            message=message,
            title=title,
            priority=Priority.DEFAULT,
            tags=["white_check_mark", "robot"],
        )
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/utils/test_notifier.py -v`
Expected: All 5 tests PASS

**Step 3: Commit implementation**

```bash
git add src/utils/notifier.py
git commit -m "feat: add items parameter to notify_daily_complete for detailed notifications"
```

---

## Task 3: Update `main.py` to pass items to notifier

**Files:**
- Modify: `main.py:144` (call site)
- Modify: `main.py:314-349` (method definition)

**Step 1: Update `_notify_complete` method signature and implementation**

Replace the `_notify_complete` method (lines 314-349) with:

```python
    def _notify_complete(self, synthesis: Any, analyzed: list | None = None) -> None:
        """Send completion notification.

        Args:
            synthesis: Synthesis result object
            analyzed: List of (item, result) tuples from analysis phase
        """
        if not synthesis:
            return

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if self.mode == "daily":
            highlight = synthesis.highlights[0] if synthesis.highlights else None

            # Build items list for detailed notification
            items_for_ntfy = []
            if analyzed:
                for item, result in analyzed:
                    if result:
                        items_for_ntfy.append({
                            "title": item.title,
                            "source": item.source_type.value,
                            "url": item.source_url,
                            "summary": result.summary[:150] if result.summary else None,
                            "signal_score": item.signal_score or 5,
                        })

            self.notifier.notify_daily_complete(
                date=date,
                items_analyzed=self.metrics.items_analyzed,
                items_discarded=self.metrics.items_discarded,
                relevance_score=synthesis.relevance_score,
                highlight=highlight,
                items=items_for_ntfy if items_for_ntfy else None,
            )

            if self.metrics.collectors_failed:
                self.notifier.notify_daily_errors(
                    date=date,
                    items_analyzed=self.metrics.items_analyzed,
                    failed_collectors=self.metrics.collectors_failed,
                )

        elif self.mode == "weekly":
            self.notifier.notify_weekly_complete(
                week=synthesis.week,
                relevance_score=synthesis.relevance_score,
                patterns=synthesis.trends[:3] if synthesis.trends else [],
            )

        elif self.mode == "monthly":
            self.notifier.notify_monthly_complete(
                month=synthesis.month,
                relevance_score=synthesis.relevance_score,
            )
```

**Step 2: Update call site in `run` method**

Change line 144 from:
```python
            self._notify_complete(synthesis)
```

To:
```python
            self._notify_complete(synthesis, analyzed)
```

**Step 3: Run existing tests to verify no regressions**

Run: `pytest tests/ -v --tb=short`
Expected: All existing tests PASS

**Step 4: Commit implementation**

```bash
git add main.py
git commit -m "feat: pass analyzed items to ntfy notification for detailed reports"
```

---

## Task 4: Integration verification

**Step 1: Run linting and type checks**

Run: `ruff check src/utils/notifier.py main.py`
Expected: No errors

Run: `mypy src/utils/notifier.py --ignore-missing-imports`
Expected: No errors

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 3: Manual verification (optional)**

If you want to test manually:
```bash
# Dry run with email preview to see the notification would work
docker compose exec app python main.py --mode daily --verbose
```

Check ntfy notification on your device for item details.

---

## Summary

| Task | Files | Description |
|------|-------|-------------|
| 1 | `tests/utils/test_notifier.py` | Add TDD tests for items parameter |
| 2 | `src/utils/notifier.py` | Implement items parameter in notify_daily_complete |
| 3 | `main.py` | Pass analyzed items to notifier |
| 4 | - | Integration verification |

## Constraints Maintained

- Backward compatible: `items` parameter is optional
- Message length: Limited to 5 items, truncated text
- No breaking changes to existing notification flow
