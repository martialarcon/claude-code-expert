"""
AI Architect v2 - Markdown Generator

Generates structured Markdown outputs for daily, weekly, and monthly digests.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..collectors.base import CollectedItem
from ..processors.analyzer import AnalysisResult
from ..processors.synthesizer import DailySynthesis, MonthlySynthesis, WeeklySynthesis
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("storage.markdown_gen")


class MarkdownGenerator:
    """
    Generates Markdown files for AI Architect outputs.

    Creates:
    - Daily digests: output/daily/YYYY-MM-DD.md
    - Weekly reports: output/weekly/YYYY-WNN.md
    - Monthly reports: output/monthly/YYYY-MM.md
    - Topic indexes: output/topics/{topic}.md
    - Master file: output/master.md
    - Index file: output/index.md
    """

    def __init__(
        self,
        output_dir: str | Path | None = None,
    ):
        """
        Initialize markdown generator.

        Args:
            output_dir: Base output directory
        """
        config = get_config()
        self.output_dir = Path(output_dir or "output")

        # Ensure directories exist
        for subdir in ["daily", "weekly", "monthly", "topics", "competitive"]:
            (self.output_dir / subdir).mkdir(parents=True, exist_ok=True)

    def generate_daily(
        self,
        synthesis: DailySynthesis,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
    ) -> Path:
        """
        Generate daily digest markdown.

        Args:
            synthesis: Daily synthesis result
            items: Analyzed items

        Returns:
            Path to generated file
        """
        date = synthesis.date
        filepath = self.output_dir / "daily" / f"{date}.md"

        content = self._build_daily_markdown(synthesis, items)
        filepath.write_text(content, encoding="utf-8")

        log.info("daily_digest_generated", path=str(filepath))
        return filepath

    def _build_daily_markdown(
        self,
        synthesis: DailySynthesis,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
    ) -> str:
        """Build daily digest markdown content."""
        lines = [
            f"# AI Architect Daily Digest",
            f"",
            f"**Date:** {synthesis.date}",
            f"**Relevance Score:** {synthesis.relevance_score}/10",
            f"",
            "---",
            f"",
            "## Summary",
            f"",
            synthesis.summary,
            f"",
            "## Highlights",
            f"",
        ]

        for highlight in synthesis.highlights:
            lines.append(f"- {highlight}")

        lines.extend([
            "",
            "## Patterns Detected",
            "",
        ])

        for pattern in synthesis.patterns:
            lines.append(f"- {pattern}")

        if synthesis.key_changes:
            lines.extend([
                "",
                "## Key Changes",
                "",
            ])
            for change in synthesis.key_changes:
                lines.append(f"- {change}")

        lines.extend([
            "",
            "## Recommendations",
            "",
        ])

        for rec in synthesis.recommendations:
            lines.append(f"- {rec}")

        # Add items section
        lines.extend([
            "",
            "---",
            "",
            "## Items Analyzed",
            "",
        ])

        # Group items by source type
        by_source: dict[str, list[tuple[CollectedItem, AnalysisResult | None]]] = {}
        for item, analysis in items:
            source = item.source_type.value
            if source not in by_source:
                by_source[source] = []
            by_source[source].append((item, analysis))

        for source, source_items in sorted(by_source.items()):
            lines.append(f"### {source.replace('_', ' ').title()}")
            lines.append("")

            for item, analysis in source_items:
                lines.append(f"#### [{item.title}]({item.source_url})")
                lines.append("")

                if analysis:
                    lines.append(analysis.summary)
                    lines.append("")

                    if analysis.key_insights:
                        lines.append("**Key Insights:**")
                        for insight in analysis.key_insights[:3]:
                            lines.append(f"- {insight}")
                        lines.append("")

                lines.append(f"*Signal: {item.signal_score}/10 | Novelty: {item.novelty_score:.2f}*")
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def generate_weekly(self, synthesis: WeeklySynthesis) -> Path:
        """Generate weekly report markdown."""
        week = synthesis.week
        filepath = self.output_dir / "weekly" / f"{week}.md"

        lines = [
            f"# AI Architect Weekly Report",
            "",
            f"**Week:** {week}",
            f"**Relevance Score:** {synthesis.relevance_score}/10",
            "",
            "---",
            "",
            "## Summary",
            "",
            synthesis.summary,
            "",
            "## Top Stories",
            "",
        ]

        for story in synthesis.top_stories:
            lines.append(f"### {story.get('title', 'Untitled')}")
            if story.get("significance"):
                lines.append("")
                lines.append(story["significance"])
            lines.append("")

        if synthesis.trends:
            lines.extend([
                "## Trends",
                "",
            ])
            for trend in synthesis.trends:
                lines.append(f"- {trend}")
            lines.append("")

        if synthesis.competitive_moves:
            lines.extend([
                "## Competitive Moves",
                "",
            ])
            for move in synthesis.competitive_moves:
                lines.append(f"- {move}")
            lines.append("")

        if synthesis.emerging_technologies:
            lines.extend([
                "## Emerging Technologies",
                "",
            ])
            for tech in synthesis.emerging_technologies:
                lines.append(f"- {tech}")
            lines.append("")

        lines.extend([
            "## Recommendations",
            "",
        ])
        for rec in synthesis.recommendations:
            lines.append(f"- {rec}")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        log.info("weekly_report_generated", path=str(filepath))
        return filepath

    def generate_monthly(self, synthesis: MonthlySynthesis) -> Path:
        """Generate monthly report markdown."""
        month = synthesis.month
        filepath = self.output_dir / "monthly" / f"{month}.md"

        lines = [
            f"# AI Architect Monthly Report",
            "",
            f"**Month:** {month}",
            f"**Relevance Score:** {synthesis.relevance_score}/10",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            synthesis.summary,
            "",
            "## Major Developments",
            "",
        ]

        for dev in synthesis.major_developments:
            lines.append(f"### {dev.get('title', 'Untitled')}")
            if dev.get("impact"):
                lines.append(f"**Impact:** {dev['impact']}")
            if dev.get("timeline"):
                lines.append(f"**Timeline:** {dev['timeline']}")
            lines.append("")

        lines.extend([
            "## Trend Analysis",
            "",
            synthesis.trend_analysis,
            "",
        ])

        if synthesis.ecosystem_changes:
            lines.extend([
                "## Ecosystem Changes",
                "",
            ])
            for change in synthesis.ecosystem_changes:
                lines.append(f"- {change}")
            lines.append("")

        lines.extend([
            "## Competitive Landscape",
            "",
            synthesis.competitive_landscape,
            "",
        ])

        if synthesis.predictions:
            lines.extend([
                "## Predictions",
                "",
            ])
            for pred in synthesis.predictions:
                lines.append(f"- {pred}")
            lines.append("")

        lines.extend([
            "## Recommendations",
            "",
        ])
        for rec in synthesis.recommendations:
            lines.append(f"- {rec}")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        log.info("monthly_report_generated", path=str(filepath))
        return filepath

    def update_index(self, daily_files: list[Path] | None = None) -> Path:
        """Update the main index file."""
        filepath = self.output_dir / "index.md"

        lines = [
            "# AI Architect - Knowledge Index",
            "",
            f"*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
            "",
            "---",
            "",
            "## Recent Digests",
            "",
        ]

        # List recent daily files
        daily_dir = self.output_dir / "daily"
        if daily_dir.exists():
            daily_files = sorted(daily_dir.glob("*.md"), reverse=True)[:10]
            for f in daily_files:
                date = f.stem
                lines.append(f"- [{date}](daily/{f.name})")

        lines.extend([
            "",
            "## Weekly Reports",
            "",
        ])

        weekly_dir = self.output_dir / "weekly"
        if weekly_dir.exists():
            weekly_files = sorted(weekly_dir.glob("*.md"), reverse=True)[:5]
            for f in weekly_files:
                lines.append(f"- [{f.stem}](weekly/{f.name})")

        lines.extend([
            "",
            "## Monthly Reports",
            "",
        ])

        monthly_dir = self.output_dir / "monthly"
        if monthly_dir.exists():
            monthly_files = sorted(monthly_dir.glob("*.md"), reverse=True)[:6]
            for f in monthly_files:
                lines.append(f"- [{f.stem}](monthly/{f.name})")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        log.info("index_updated", path=str(filepath))
        return filepath


def generate_daily_digest(
    synthesis: DailySynthesis,
    items: list[tuple[CollectedItem, AnalysisResult | None]],
) -> Path:
    """Convenience function to generate daily digest."""
    gen = MarkdownGenerator()
    return gen.generate_daily(synthesis, items)
