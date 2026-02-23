"""
AI Architect v2 - Signal Ranker

Ranks collected items by signal strength using Claude.
Processes items in batches with unified Impact + Maturity classification.
"""

import json
import time
from dataclasses import dataclass
from typing import Any

from .client_factory import get_analysis_client
from .claude_client import ClaudeClientError
from ..collectors.base import CollectedItem
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("processor.signal_ranker")

# Default delay between batch API calls to avoid rate limits (seconds)
DEFAULT_BATCH_DELAY = 3.0


# Impact dimensions from the plan
IMPACT_DIMENSIONS = [
    "tooling",           # Development tools and workflows
    "architecture",      # System design patterns
    "research",          # Academic/industry research
    "production",        # Production deployment concerns
    "ecosystem",         # Library/framework ecosystem
]

# Maturity levels from the plan
MATURITY_LEVELS = [
    "experimental",      # Proof of concept, research
    "early",             # Early adopters, limited production use
    "growing",           # Growing adoption, best practices emerging
    "stable",            # Widely adopted, stable APIs
    "legacy",            # Declining, being replaced
]


@dataclass
class RankedItem:
    """Item with ranking scores."""
    item: CollectedItem
    signal_score: int          # 1-10
    impact: str                # Impact dimension
    maturity: str              # Maturity level
    reasoning: str | None = None


# Prompt template for batch ranking
BATCH_RANKING_PROMPT = """Analyze these {count} items and rank them by signal strength.

For each item, provide:
1. **signal_score** (1-10): How important is this for someone building with Claude/AI?
   - 1-3: Low signal, routine updates or minor changes
   - 4-6: Moderate signal, useful but not urgent
   - 7-8: High signal, significant development
   - 9-10: Critical signal, breakthrough or major shift

2. **impact**: Primary impact dimension (choose one):
   - tooling: Development tools and workflows
   - architecture: System design patterns
   - research: Academic/industry research findings
   - production: Production deployment concerns
   - ecosystem: Library/framework ecosystem changes

3. **maturity**: Technology maturity level (choose one):
   - experimental: Proof of concept, research stage
   - early: Early adopters, limited production use
   - growing: Growing adoption, best practices emerging
   - stable: Widely adopted, stable APIs
   - legacy: Declining, being replaced

4. **reasoning**: One sentence explaining the score

Items to analyze:
{items}

Respond with a JSON array (no markdown):
[
  {{"index": 0, "signal_score": N, "impact": "...", "maturity": "...", "reasoning": "..."}},
  ...
]
"""


class SignalRanker:
    """
    Ranks items by signal strength using Claude.

    Processes items in batches for efficiency.
    Items below signal_threshold are discarded.
    """

    def __init__(
        self,
        batch_size: int = 10,
        signal_threshold: int = 4,
        client: None = None,
        batch_delay: float | None = None,
    ):
        """
        Initialize signal ranker.

        Args:
            batch_size: Items per Claude call
            signal_threshold: Minimum score to keep (1-10)
            client: Claude client (uses default if None)
            batch_delay: Delay between batch API calls in seconds (to avoid rate limits).
                        Defaults to config.thresholds.batch_delay
        """
        config = get_config()
        self.batch_size = batch_size or config.thresholds.batch_size
        self.signal_threshold = signal_threshold or config.thresholds.signal_score_min
        self.client = client or get_analysis_client()
        self.batch_delay = batch_delay if batch_delay is not None else config.thresholds.batch_delay

    def rank_batch(self, items: list[CollectedItem]) -> list[RankedItem]:
        """
        Rank a batch of items.

        Args:
            items: Items to rank (should be <= batch_size)

        Returns:
            List of RankedItem objects
        """
        if not items:
            return []

        # Format items for prompt
        items_text = "\n\n".join([
            f"[{i}] **{item.title}**\nSource: {item.source_type.value}\n{item.content[:1000]}"
            for i, item in enumerate(items)
        ])

        prompt = BATCH_RANKING_PROMPT.format(
            count=len(items),
            items=items_text,
        )

        try:
            response = self.client.complete(prompt, max_tokens=4096, expect_json=True)

            if not response.json_data:
                log.warning("batch_ranking_no_json", items=len(items))
                return self._fallback_rank(items)

            return self._parse_rankings(items, response.json_data)

        except ClaudeClientError as e:
            log.error("batch_ranking_error", error=str(e)[:200])
            return self._fallback_rank(items)

    def _parse_rankings(
        self,
        items: list[CollectedItem],
        rankings_data: list[dict[str, Any]] | dict[str, Any],
    ) -> list[RankedItem]:
        """Parse Claude's ranking response."""
        ranked = []

        # Handle if it's wrapped in a dict
        if isinstance(rankings_data, dict):
            rankings_data = rankings_data.get("rankings", rankings_data.get("items", [rankings_data]))

        rankings_by_index = {r.get("index", i): r for i, r in enumerate(rankings_data)}

        for i, item in enumerate(items):
            ranking = rankings_by_index.get(i, {})

            signal_score = ranking.get("signal_score", 5)
            impact = ranking.get("impact", "ecosystem")
            maturity = ranking.get("maturity", "growing")
            reasoning = ranking.get("reasoning")

            # Validate values
            signal_score = max(1, min(10, int(signal_score)))
            if impact not in IMPACT_DIMENSIONS:
                impact = "ecosystem"
            if maturity not in MATURITY_LEVELS:
                maturity = "growing"

            ranked.append(RankedItem(
                item=item,
                signal_score=signal_score,
                impact=impact,
                maturity=maturity,
                reasoning=reasoning,
            ))

        return ranked

    def _fallback_rank(self, items: list[CollectedItem]) -> list[RankedItem]:
        """Fallback ranking when Claude fails."""
        ranked = []
        for item in items:
            # Simple heuristic based on source type
            score = 5
            if item.source_type.value in ["github_signals", "docs"]:
                score = 6
            elif item.source_type.value == "github_emerging":
                score = 7
            elif item.metadata.get("has_priority_label"):
                score = 7

            ranked.append(RankedItem(
                item=item,
                signal_score=score,
                impact="ecosystem",
                maturity="growing",
                reasoning="Fallback ranking (Claude unavailable)",
            ))

        return ranked

    def rank_all(self, items: list[CollectedItem]) -> list[RankedItem]:
        """
        Rank all items, processing in batches.

        Args:
            items: All items to rank

        Returns:
            List of RankedItem objects (filtered by threshold)
        """
        all_ranked = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size

        log.info(
            "ranking_items",
            total_items=len(items),
            batch_size=self.batch_size,
            total_batches=total_batches,
        )

        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1

            log.info("ranking_batch", batch=batch_num, items=len(batch))

            ranked = self.rank_batch(batch)
            all_ranked.extend(ranked)

            # Add delay between batch requests to avoid rate limiting
            # Skip delay after last batch
            if self.batch_delay > 0 and i + self.batch_size < len(items):
                time.sleep(self.batch_delay)

        # Filter by threshold
        filtered = [r for r in all_ranked if r.signal_score >= self.signal_threshold]

        log.info(
            "ranking_complete",
            total_ranked=len(all_ranked),
            passed_threshold=len(filtered),
            threshold=self.signal_threshold,
        )

        return filtered

    def apply_scores(self, ranked_items: list[RankedItem]) -> list[CollectedItem]:
        """
        Apply ranking scores back to CollectedItems.

        Args:
            ranked_items: Ranked items

        Returns:
            CollectedItems with scores applied
        """
        for ranked in ranked_items:
            ranked.item.signal_score = ranked.signal_score
            ranked.item.impact = ranked.impact
            ranked.item.maturity = ranked.maturity

        return [r.item for r in ranked_items]


def rank_items(items: list[CollectedItem]) -> list[CollectedItem]:
    """
    Convenience function to rank and filter items.

    Args:
        items: Items to rank

    Returns:
        Filtered items with scores applied
    """
    ranker = SignalRanker()
    ranked = ranker.rank_all(items)
    return ranker.apply_scores(ranked)
