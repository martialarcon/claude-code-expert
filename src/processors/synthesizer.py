"""
AI Architect v2 - Synthesizer

Generates strategic synthesis from analyzed items using Claude Opus.
Supports daily, weekly, and monthly synthesis modes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .analyzer import AnalysisResult
from .claude_client import ClaudeClient, ClaudeClientError, get_synthesis_client
from ..collectors.base import CollectedItem
from ..utils.logger import get_logger

log = get_logger("processor.synthesizer")


class SynthesisMode(str, Enum):
    """Synthesis modes."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class DailySynthesis:
    """Daily synthesis result."""
    date: str
    relevance_score: int  # 1-10
    highlights: list[str]
    patterns: list[str]
    recommendations: list[str]
    key_changes: list[str]
    summary: str


@dataclass
class WeeklySynthesis:
    """Weekly synthesis result."""
    week: str  # YYYY-WNN format
    relevance_score: int
    top_stories: list[dict[str, str]]
    trends: list[str]
    competitive_moves: list[str]
    emerging_technologies: list[str]
    recommendations: list[str]
    summary: str


@dataclass
class MonthlySynthesis:
    """Monthly synthesis result."""
    month: str  # YYYY-MM format
    relevance_score: int
    major_developments: list[dict[str, str]]
    trend_analysis: str
    ecosystem_changes: list[str]
    competitive_landscape: str
    predictions: list[str]
    recommendations: list[str]
    summary: str


# Prompt templates
DAILY_SYNTHESIS_PROMPT = """Synthesize today's AI/Claude ecosystem signals into a strategic digest.

**Items analyzed today ({date}):**
{items_content}

**Total items:** {item_count}

Generate a JSON response:
{{
  "relevance_score": 1-10,  // How significant was today in the ecosystem?
  "highlights": [
    "Most important finding 1",
    "Most important finding 2",
    "Most important finding 3"
  ],
  "patterns": [
    "Pattern or trend noticed today",
    "Another pattern"
  ],
  "recommendations": [
    "Actionable recommendation 1",
    "Actionable recommendation 2"
  ],
  "key_changes": [
    "Notable change from previous days/weeks"
  ],
  "summary": "2-3 paragraph overview of the day's most important developments"
}}

Focus on:
1. What matters most for someone building with Claude/AI
2. Patterns that might not be obvious from individual items
3. Actionable intelligence

Respond with JSON only.
"""

WEEKLY_SYNTHESIS_PROMPT = """Synthesize this week's AI/Claude ecosystem signals into a strategic report.

**Week:** {week}
**Items this week:** {item_count}

{items_content}

Generate a JSON response:
{{
  "relevance_score": 1-10,
  "top_stories": [
    {{"title": "...", "significance": "..."}},
    ...
  ],
  "trends": [
    "Major trend 1 with implications",
    "Major trend 2"
  ],
  "competitive_moves": [
    "Competitive development 1",
    "Competitive development 2"
  ],
  "emerging_technologies": [
    "Emerging tech/tool to watch"
  ],
  "recommendations": [
    "Strategic recommendation"
  ],
  "summary": "Week overview with strategic insights"
}}

Focus on patterns and changes visible over the week timeframe.
"""

MONTHLY_SYNTHESIS_PROMPT = """Generate a comprehensive monthly intelligence report for the AI/Claude ecosystem.

**Month:** {month}
**Items this month:** {item_count}

{items_content}

Generate a JSON response:
{{
  "relevance_score": 1-10,
  "major_developments": [
    {{"title": "...", "impact": "...", "timeline": "..."}}
  ],
  "trend_analysis": "Analysis of major trends this month",
  "ecosystem_changes": [
    "Significant ecosystem change"
  ],
  "competitive_landscape": "How the competitive landscape has shifted",
  "predictions": [
    "Prediction for next month based on current signals"
  ],
  "recommendations": [
    "Strategic recommendation"
  ],
  "summary": "Month overview with strategic implications"
}}

Focus on strategic intelligence and predictive insights.
"""


class Synthesizer:
    """
    Generates synthesis reports using Claude Opus.

    Supports daily, weekly, and monthly synthesis modes.
    """

    def __init__(
        self,
        client: ClaudeClient | None = None,
        store_results: bool = True,
    ):
        """
        Initialize synthesizer.

        Args:
            client: Claude client (uses synthesis/Opus client if None)
            store_results: Whether to store synthesis in vector store
        """
        self.client = client or get_synthesis_client()
        self.store_results = store_results
        self._vector_store = None

    @property
    def vector_store(self):
        """Lazy load vector store."""
        if self._vector_store is None:
            from ..storage.vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    def synthesize_daily(
        self,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
        date: str | None = None,
    ) -> DailySynthesis | None:
        """
        Generate daily synthesis.

        Args:
            items: List of (item, analysis) tuples
            date: Date string (defaults to today)

        Returns:
            DailySynthesis or None if synthesis fails
        """
        date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Build items content
        items_content = self._format_items_for_prompt(items)
        item_count = len(items)

        prompt = DAILY_SYNTHESIS_PROMPT.format(
            date=date,
            items_content=items_content,
            item_count=item_count,
        )

        try:
            log.info("synthesizing_daily", date=date, items=item_count)

            response = self.client.complete(
                prompt=prompt,
                max_tokens=2048,
                expect_json=True,
            )

            if not response.json_data:
                log.warning("daily_synthesis_no_json")
                return self._fallback_daily(date, items)

            result = self._parse_daily_synthesis(date, response.json_data)

            if self.store_results:
                self._store_synthesis("daily", date, result.summary)

            log.info(
                "daily_synthesis_complete",
                date=date,
                relevance_score=result.relevance_score,
            )

            return result

        except ClaudeClientError as e:
            log.error("daily_synthesis_error", error=str(e)[:200])
            return self._fallback_daily(date, items)

    def _parse_daily_synthesis(
        self,
        date: str,
        data: dict[str, Any],
    ) -> DailySynthesis:
        """Parse daily synthesis from JSON."""
        return DailySynthesis(
            date=date,
            relevance_score=min(10, max(1, int(data.get("relevance_score", 5)))),
            highlights=data.get("highlights", []),
            patterns=data.get("patterns", []),
            recommendations=data.get("recommendations", []),
            key_changes=data.get("key_changes", []),
            summary=data.get("summary", "Synthesis unavailable."),
        )

    def _fallback_daily(
        self,
        date: str,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
    ) -> DailySynthesis:
        """Generate fallback daily synthesis."""
        highlights = [item.title for item, _ in items[:3]]
        return DailySynthesis(
            date=date,
            relevance_score=5,
            highlights=highlights,
            patterns=["Synthesis unavailable - using fallback"],
            recommendations=["Review items manually"],
            key_changes=[],
            summary=f"Processed {len(items)} items. Synthesis generation failed.",
        )

    def synthesize_weekly(
        self,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
        week: str | None = None,
    ) -> WeeklySynthesis | None:
        """Generate weekly synthesis."""
        week = week or datetime.now(timezone.utc).strftime("%Y-W%W")
        items_content = self._format_items_for_prompt(items)

        prompt = WEEKLY_SYNTHESIS_PROMPT.format(
            week=week,
            item_count=len(items),
            items_content=items_content,
        )

        try:
            log.info("synthesizing_weekly", week=week, items=len(items))

            response = self.client.complete(
                prompt=prompt,
                max_tokens=3000,
                expect_json=True,
            )

            if not response.json_data:
                return self._fallback_weekly(week, items)

            result = self._parse_weekly_synthesis(week, response.json_data)

            if self.store_results:
                self._store_synthesis("weekly", week, result.summary)

            return result

        except ClaudeClientError as e:
            log.error("weekly_synthesis_error", error=str(e)[:200])
            return self._fallback_weekly(week, items)

    def _parse_weekly_synthesis(self, week: str, data: dict[str, Any]) -> WeeklySynthesis:
        """Parse weekly synthesis from JSON."""
        return WeeklySynthesis(
            week=week,
            relevance_score=min(10, max(1, int(data.get("relevance_score", 5)))),
            top_stories=data.get("top_stories", []),
            trends=data.get("trends", []),
            competitive_moves=data.get("competitive_moves", []),
            emerging_technologies=data.get("emerging_technologies", []),
            recommendations=data.get("recommendations", []),
            summary=data.get("summary", ""),
        )

    def _fallback_weekly(
        self,
        week: str,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
    ) -> WeeklySynthesis:
        """Generate fallback weekly synthesis."""
        top_stories = [{"title": item.title, "significance": ""} for item, _ in items[:5]]
        return WeeklySynthesis(
            week=week,
            relevance_score=5,
            top_stories=top_stories,
            trends=[],
            competitive_moves=[],
            emerging_technologies=[],
            recommendations=["Review items manually"],
            summary=f"Weekly synthesis for {week}. Processed {len(items)} items.",
        )

    def synthesize_monthly(
        self,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
        month: str | None = None,
    ) -> MonthlySynthesis | None:
        """Generate monthly synthesis."""
        month = month or datetime.now(timezone.utc).strftime("%Y-%m")
        items_content = self._format_items_for_prompt(items, max_items=100)

        prompt = MONTHLY_SYNTHESIS_PROMPT.format(
            month=month,
            item_count=len(items),
            items_content=items_content,
        )

        try:
            log.info("synthesizing_monthly", month=month, items=len(items))

            response = self.client.complete(
                prompt=prompt,
                max_tokens=4096,
                expect_json=True,
            )

            if not response.json_data:
                return self._fallback_monthly(month, items)

            result = self._parse_monthly_synthesis(month, response.json_data)

            if self.store_results:
                self._store_synthesis("monthly", month, result.summary)

            return result

        except ClaudeClientError as e:
            log.error("monthly_synthesis_error", error=str(e)[:200])
            return self._fallback_monthly(month, items)

    def _parse_monthly_synthesis(self, month: str, data: dict[str, Any]) -> MonthlySynthesis:
        """Parse monthly synthesis from JSON."""
        return MonthlySynthesis(
            month=month,
            relevance_score=min(10, max(1, int(data.get("relevance_score", 5)))),
            major_developments=data.get("major_developments", []),
            trend_analysis=data.get("trend_analysis", ""),
            ecosystem_changes=data.get("ecosystem_changes", []),
            competitive_landscape=data.get("competitive_landscape", ""),
            predictions=data.get("predictions", []),
            recommendations=data.get("recommendations", []),
            summary=data.get("summary", ""),
        )

    def _fallback_monthly(
        self,
        month: str,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
    ) -> MonthlySynthesis:
        """Generate fallback monthly synthesis."""
        major = [{"title": item.title, "impact": "", "timeline": ""} for item, _ in items[:10]]
        return MonthlySynthesis(
            month=month,
            relevance_score=5,
            major_developments=major,
            trend_analysis="Monthly synthesis unavailable.",
            ecosystem_changes=[],
            competitive_landscape="",
            predictions=[],
            recommendations=["Review items manually"],
            summary=f"Monthly synthesis for {month}. Processed {len(items)} items.",
        )

    def _format_items_for_prompt(
        self,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
        max_items: int = 50,
    ) -> str:
        """Format items for inclusion in prompt."""
        formatted = []
        for item, analysis in items[:max_items]:
            entry = f"- [{item.source_type.value}] {item.title}"
            if analysis:
                entry += f"\n  Summary: {analysis.summary[:200]}"
            formatted.append(entry)

        return "\n\n".join(formatted)

    def _store_synthesis(self, mode: str, period: str, content: str) -> None:
        """Store synthesis in vector store."""
        try:
            self.vector_store.add(
                collection="synthesis",
                documents=[content],
                ids=[f"synthesis_{mode}_{period}"],
                metadatas=[{
                    "mode": mode,
                    "period": period,
                }],
            )
        except Exception as e:
            log.warning("synthesis_storage_failed", error=str(e)[:200])
