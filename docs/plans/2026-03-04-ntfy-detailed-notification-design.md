# Design: ntfy Detailed Notification

**Date:** 2026-03-04
**Status:** Approved
**Scope:** Add complete item details to ntfy notifications

## Problem

The ntfy notification after daily analysis only shows:
- Item counts (analyzed/discarded)
- Relevance score
- One truncated highlight

Missing: item titles, sources, URLs, and summaries.

## Solution

### 1. Modify `notify_daily_complete()` in `src/utils/notifier.py`

Add optional `items` parameter and build detailed message:

```python
def notify_daily_complete(
    self,
    date: str,
    items_analyzed: int,
    items_discarded: int,
    relevance_score: int,
    highlight: str | None = None,
    items: list[dict] | None = None,  # NEW
) -> bool:
    """
    Send daily cycle completion notification.

    Args:
        items: Optional list of dicts with keys:
            - title: str
            - source: str
            - url: str (optional)
            - summary: str (optional)
            - signal_score: int
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

### 2. Update `_notify_complete()` in `main.py`

Build items list and pass to notifier:

```python
def _notify_complete(self, synthesis: Any, analyzed: list) -> None:
    """Send completion notification."""
    if not synthesis:
        return

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if self.mode == "daily":
        highlight = synthesis.highlights[0] if synthesis.highlights else None

        # Build items list for detailed notification
        items_for_ntfy = []
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
            items=items_for_ntfy,  # NEW
        )
```

## Files to Modify

| File | Change |
|------|--------|
| `src/utils/notifier.py` | Add `items` param to `notify_daily_complete()` |
| `main.py` | Build items list and pass to notifier |

## Testing

1. Run daily cycle with `--mode daily`
2. Verify ntfy notification includes:
   - Item titles
   - Sources
   - URLs
   - Summaries (truncated)
   - Signal scores

## Constraints

- Limit items to 5 (ntfy has message length limits)
- Truncate titles to 60 chars, URLs to 60 chars, summaries to 100 chars
- Keep backward compatibility (items param is optional)
