"""
AI Architect v2 - Item Analyzer

Performs deep analysis of individual items using Claude Sonnet.
"""

import time
from dataclasses import dataclass
from typing import Any

from .client_factory import get_analysis_client
from .claude_client import ClaudeClientError
from ..collectors.base import CollectedItem
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("processor.analyzer")

# Default delay between API calls to avoid rate limits (seconds)
DEFAULT_REQUEST_DELAY = 5.0


@dataclass
class AnalysisResult:
    """Result of item analysis."""
    item_id: str
    summary: str
    key_insights: list[str]
    technical_details: str | None
    relevance_to_claude: str
    actionability: str  # high, medium, low
    related_topics: list[str]
    confidence: float  # 0-1


# Analysis prompt template
ANALYSIS_PROMPT = """Analyze this item from the AI/Claude ecosystem and provide a structured analysis.

**Item:**
Title: {title}
Source: {source_type}
URL: {source_url}
Content:
{content}

Provide a JSON response with this structure:
{{
  "summary": "One paragraph summary (2-3 sentences)",
  "key_insights": [
    "Insight 1",
    "Insight 2",
    "Insight 3"
  ],
  "technical_details": "Any technical specifics worth noting (or null if none)",
  "relevance_to_claude": "How this relates to Claude/Anthropic specifically",
  "actionability": "high|medium|low - how actionable is this information",
  "related_topics": ["topic1", "topic2"],
  "confidence": 0.0-1.0
}}

Focus on:
1. What's actually new or changed
2. Practical implications for developers using Claude
3. Connection to broader AI ecosystem trends

Respond with JSON only, no markdown.
"""


class Analyzer:
    """
    Deep analyzer for individual items.

    Uses Claude Sonnet for detailed analysis.
    """

    def __init__(
        self,
        client: None = None,
        store_results: bool = True,
        request_delay: float | None = None,
    ):
        """
        Initialize analyzer.

        Args:
            client: Claude client (uses default analysis client if None)
            store_results: Whether to store analysis in vector store
            request_delay: Delay between API calls in seconds (to avoid rate limits).
                          Defaults to config.thresholds.request_delay
        """
        self.client = client or get_analysis_client()
        self.store_results = store_results
        config = get_config()
        self.request_delay = request_delay if request_delay is not None else config.thresholds.request_delay
        self._vector_store = None

    @property
    def vector_store(self):
        """Lazy load vector store."""
        if self._vector_store is None:
            from ..storage.vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    def analyze(self, item: CollectedItem) -> AnalysisResult | None:
        """
        Analyze a single item.

        Args:
            item: Item to analyze

        Returns:
            AnalysisResult or None if analysis fails
        """
        prompt = ANALYSIS_PROMPT.format(
            title=item.title,
            source_type=item.source_type.value,
            source_url=item.source_url,
            content=item.content[:4000],  # Limit content length
        )

        try:
            log.debug("analyzing_item", item_id=item.id, title=item.title[:50])

            response = self.client.complete(
                prompt=prompt,
                max_tokens=1024,
                expect_json=True,
            )

            if not response.json_data:
                log.warning("analysis_no_json", item_id=item.id)
                return self._fallback_analysis(item)

            result = self._parse_result(item.id, response.json_data)

            # Store in vector store if enabled
            if self.store_results:
                self._store_analysis(item, result)

            log.info(
                "analysis_complete",
                item_id=item.id,
                actionability=result.actionability,
                confidence=result.confidence,
            )

            return result

        except ClaudeClientError as e:
            log.error("analysis_error", item_id=item.id, error=str(e)[:200])
            return self._fallback_analysis(item)

        except Exception as e:
            # Catch-all for any unexpected errors (timeouts, network issues, etc.)
            # Always return fallback instead of crashing the batch
            log.error("analysis_unexpected_error", item_id=item.id, error=str(e)[:200], error_type=type(e).__name__)
            return self._fallback_analysis(item)

    def _parse_result(self, item_id: str, data: dict[str, Any]) -> AnalysisResult:
        """Parse analysis result from JSON."""
        return AnalysisResult(
            item_id=item_id,
            summary=data.get("summary", "Unable to generate summary."),
            key_insights=data.get("key_insights", []),
            technical_details=data.get("technical_details"),
            relevance_to_claude=data.get("relevance_to_claude", ""),
            actionability=data.get("actionability", "medium"),
            related_topics=data.get("related_topics", []),
            confidence=min(1.0, max(0.0, float(data.get("confidence", 0.7)))),
        )

    def _fallback_analysis(self, item: CollectedItem) -> AnalysisResult:
        """Generate fallback analysis when Claude fails."""
        # Extract first sentence as summary
        summary = item.content.split(".")[0] + "." if item.content else item.title

        return AnalysisResult(
            item_id=item.id,
            summary=summary[:500],
            key_insights=["Analysis unavailable - using fallback"],
            technical_details=None,
            relevance_to_claude="Unable to assess",
            actionability="medium",
            related_topics=[item.source_type.value],
            confidence=0.3,
        )

    def _store_analysis(self, item: CollectedItem, result: AnalysisResult) -> None:
        """Store analysis result in vector store."""
        try:
            # Create searchable text from analysis
            analysis_text = f"{result.summary}\n" + "\n".join(result.key_insights)

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
        except Exception as e:
            log.warning("analysis_storage_failed", error=str(e)[:200])

    def analyze_batch(
        self,
        items: list[CollectedItem],
    ) -> list[tuple[CollectedItem, AnalysisResult | None]]:
        """
        Analyze multiple items.

        Args:
            items: Items to analyze

        Returns:
            List of (item, result) tuples
        """
        results = []

        log.info("analyzing_batch", total_items=len(items))

        for i, item in enumerate(items):
            log.debug("batch_progress", current=i + 1, total=len(items))
            result = self.analyze(item)
            results.append((item, result))

            # Add delay between requests to avoid rate limiting
            # Skip delay after last item
            if self.request_delay > 0 and i < len(items) - 1:
                time.sleep(self.request_delay)

        successful = sum(1 for _, r in results if r is not None)
        log.info(
            "batch_analysis_complete",
            total=len(items),
            successful=successful,
        )

        return results


def analyze_item(item: CollectedItem) -> AnalysisResult | None:
    """
    Convenience function to analyze a single item.

    Args:
        item: Item to analyze

    Returns:
        AnalysisResult or None
    """
    analyzer = Analyzer()
    return analyzer.analyze(item)


def analyze_items(
    items: list[CollectedItem],
) -> list[tuple[CollectedItem, AnalysisResult | None]]:
    """
    Convenience function to analyze multiple items.

    Args:
        items: Items to analyze

    Returns:
        List of (item, result) tuples
    """
    analyzer = Analyzer()
    return analyzer.analyze_batch(items)
