#!/usr/bin/env python3
"""
AI Architect v2 - Main Orchestrator

Coordinates the entire pipeline:
Collectors → Signal Ranker → Novelty Detector → Analyzer → Synthesizer → Output

Usage:
    python main.py --mode daily
    python main.py --mode weekly
    python main.py --mode monthly
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from typing import Any

from src.collectors.base import CollectedItem, CollectionResult
from src.collectors.blogs import collect_blogs
from src.collectors.docs import collect_docs
from src.collectors.github_emerging import collect_github_emerging
from src.collectors.github_repos import collect_github_repos
from src.collectors.github_signals import collect_github_signals
from src.collectors.stackoverflow import collect_stackoverflow
from src.collectors.hackernews import collect_hackernews
from src.collectors.reddit import collect_reddit
from src.processors.analyzer import Analyzer
from src.processors.novelty_detector import NoveltyDetector
from src.processors.signal_ranker import SignalRanker
from src.processors.synthesizer import Synthesizer, SynthesisMode
from src.storage.markdown_gen import MarkdownGenerator
from src.storage.vector_store import get_vector_store
from src.utils.config import get_config, get_settings
from src.utils.logger import configure_logging, get_logger
from src.utils.notifier import get_notifier
from src.notifications.email_reporter import EmailReporter


log = get_logger("main")


class CycleMetrics:
    """Collects metrics for the cycle."""

    def __init__(self):
        self.start_time = time.time()
        self.phase_durations: dict[str, float] = {}
        self.items_collected = 0
        self.items_by_source: dict[str, int] = {}
        self.items_processed = 0
        self.items_discarded = 0
        self.collectors_failed: list[str] = []
        self.items_analyzed = 0
        self.analysis_errors = 0

    def record_phase(self, name: str, duration: float) -> None:
        """Record a phase duration."""
        self.phase_durations[name] = duration

    @property
    def total_duration(self) -> float:
        """Total cycle duration in seconds."""
        return time.time() - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "duration_seconds": int(self.total_duration),
            "phase_durations": {k: int(v) for k, v in self.phase_durations.items()},
            "items_collected": self.items_collected,
            "items_by_source": self.items_by_source,
            "items_processed": self.items_processed,
            "items_discarded": self.items_discarded,
            "collectors_failed": self.collectors_failed,
            "items_analyzed": self.items_analyzed,
            "analysis_errors": self.analysis_errors,
        }


class AIArchitect:
    """
    Main orchestrator for AI Architect v2.

    Coordinates all pipeline phases.
    """

    def __init__(self, mode: str = "daily"):
        """
        Initialize orchestrator.

        Args:
            mode: Processing mode (daily, weekly, monthly)
        """
        self.mode = mode
        self.config = get_config()
        self.settings = get_settings()
        self.metrics = CycleMetrics()

        # Initialize components
        self.ranker = SignalRanker()
        self.novelty_detector = NoveltyDetector()
        self.analyzer = Analyzer()
        self.synthesizer = Synthesizer()
        self.markdown_gen = MarkdownGenerator()
        self.notifier = get_notifier()

        log.info("orchestrator_initialized", mode=mode)

    def run(self) -> bool:
        """
        Run the complete pipeline.

        Returns:
            True if successful
        """
        log.info("cycle_starting", mode=self.mode)

        try:
            # Phase 1: Collection
            items = self._collect()
            if not items:
                log.warning("no_items_collected")
                self._notify_empty()
                return True

            # Phase 2: Processing
            processed_items = self._process(items)
            if not processed_items:
                log.warning("no_items_after_processing")
                return True

            # Phase 3: Analysis
            analyzed = self._analyze(processed_items)

            # Phase 4: Synthesis
            synthesis = self._synthesize(analyzed)

            # Phase 5: Output
            self._generate_output(synthesis, analyzed)

            # Phase 6: Notification
            self._notify_complete(synthesis)

            # Phase 7: Email Report (if enabled)
            self._send_email_report()

            log.info(
                "cycle_complete",
                mode=self.mode,
                duration_seconds=int(self.metrics.total_duration),
            )

            return True

        except Exception as e:
            log.error("cycle_failed", error=str(e)[:500])
            self._notify_failed(str(e))
            return False

    def _collect(self) -> list[CollectedItem]:
        """Run all collectors."""
        phase_start = time.time()
        all_items = []

        collectors = [
            ("docs", collect_docs),
            ("github_signals", collect_github_signals),
            ("github_emerging", collect_github_emerging),
            ("github_repos", collect_github_repos),
            ("blogs", collect_blogs),
            ("stackoverflow", collect_stackoverflow),
            ("reddit", collect_reddit),
            ("hackernews", collect_hackernews),
        ]

        for name, collector_func in collectors:
            # Check if collector is enabled
            collector_config = getattr(self.config.collectors, name, None)
            if collector_config and not getattr(collector_config, "enabled", True):
                log.info("collector_disabled", source=name)
                continue

            try:
                log.info("collecting", source=name)
                result = collector_func(self.config.collectors.model_dump())

                self.metrics.items_by_source[name] = len(result.items)
                self.metrics.items_collected += len(result.items)

                if result.errors:
                    self.metrics.collectors_failed.append(name)
                    log.warning(
                        "collector_errors",
                        source=name,
                        errors=result.errors[:3],
                    )

                all_items.extend(result.items)

            except Exception as e:
                log.error("collector_failed", source=name, error=str(e)[:200])
                self.metrics.collectors_failed.append(name)

        self.metrics.record_phase("collection", time.time() - phase_start)
        log.info("collection_complete", total_items=len(all_items))

        return all_items

    def _process(self, items: list[CollectedItem]) -> list[CollectedItem]:
        """Process items: rank + filter by signal + detect novelty."""
        phase_start = time.time()

        # Step 1: Rank and filter by signal
        log.info("ranking_items", count=len(items))
        ranked = self.ranker.rank_all(items)
        # Apply scores to items before filtering
        filtered_by_signal = self.ranker.apply_scores(ranked)

        self.metrics.items_discarded += len(items) - len(filtered_by_signal)
        log.info(
            "signal_filter_complete",
            passed=len(filtered_by_signal),
            discarded=len(items) - len(filtered_by_signal),
        )

        # Step 2: Filter by novelty
        log.info("checking_novelty", count=len(filtered_by_signal))
        novel_items = self.novelty_detector.filter_novel(filtered_by_signal)

        self.metrics.items_discarded += len(filtered_by_signal) - len(novel_items)
        self.metrics.items_processed = len(novel_items)

        self.metrics.record_phase("processing", time.time() - phase_start)
        log.info(
            "processing_complete",
            total=len(novel_items),
            discarded_total=self.metrics.items_discarded,
        )

        return novel_items

    def _analyze(
        self,
        items: list[CollectedItem],
    ) -> list[tuple[CollectedItem, Any]]:
        """Analyze items with Claude."""
        phase_start = time.time()

        log.info("analyzing_items", count=len(items))
        results = self.analyzer.analyze_batch(items)

        self.metrics.items_analyzed = sum(1 for _, r in results if r is not None)
        self.metrics.analysis_errors = sum(1 for _, r in results if r is None)

        self.metrics.record_phase("analysis", time.time() - phase_start)
        log.info(
            "analysis_complete",
            analyzed=self.metrics.items_analyzed,
            errors=self.metrics.analysis_errors,
        )

        return results

    def _synthesize(
        self,
        analyzed: list[tuple[CollectedItem, Any]],
    ) -> Any:
        """Generate synthesis."""
        phase_start = time.time()

        log.info("synthesizing", mode=self.mode)

        if self.mode == "daily":
            synthesis = self.synthesizer.synthesize_daily(analyzed)
        elif self.mode == "weekly":
            synthesis = self.synthesizer.synthesize_weekly(analyzed)
        elif self.mode == "monthly":
            synthesis = self.synthesizer.synthesize_monthly(analyzed)
        else:
            synthesis = self.synthesizer.synthesize_daily(analyzed)

        self.metrics.record_phase("synthesis", time.time() - phase_start)
        log.info("synthesis_complete", mode=self.mode)

        return synthesis

    def _generate_output(
        self,
        synthesis: Any,
        analyzed: list[tuple[CollectedItem, Any]],
    ) -> None:
        """Generate markdown output."""
        phase_start = time.time()

        if self.mode == "daily" and synthesis:
            self.markdown_gen.generate_daily(synthesis, analyzed)
        elif self.mode == "weekly" and synthesis:
            self.markdown_gen.generate_weekly(synthesis)
        elif self.mode == "monthly" and synthesis:
            self.markdown_gen.generate_monthly(synthesis)

        # Update index
        self.markdown_gen.update_index()

        self.metrics.record_phase("output", time.time() - phase_start)
        log.info("output_generated", mode=self.mode)

    def _notify_complete(self, synthesis: Any) -> None:
        """Send completion notification."""
        if not synthesis:
            return

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if self.mode == "daily":
            highlight = synthesis.highlights[0] if synthesis.highlights else None
            self.notifier.notify_daily_complete(
                date=date,
                items_analyzed=self.metrics.items_analyzed,
                items_discarded=self.metrics.items_discarded,
                relevance_score=synthesis.relevance_score,
                highlight=highlight,
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

    def _send_email_report(self, preview_only: bool = False, recipients: list[str] | None = None) -> None:
        """Send email report if enabled."""
        email_config = self.config.notifications.email

        if not email_config.enabled:
            log.debug("email_notifications_disabled")
            return

        if self.mode not in email_config.send_on_modes:
            log.debug("mode_not_in_send_on_modes", mode=self.mode)
            return

        try:
            reporter = EmailReporter()
            success = reporter.send_daily_report(
                days=1,
                recipients=recipients,
                preview_only=preview_only,
            )
            if success:
                log.info("email_report_sent", preview=preview_only)
            else:
                log.warning("email_report_failed")
        except Exception as e:
            log.error("email_report_error", error=str(e)[:200])

    def _notify_empty(self) -> None:
        """Notify when no items collected."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.notifier.notify_daily_complete(
            date=date,
            items_analyzed=0,
            items_discarded=0,
            relevance_score=0,
        )

    def _notify_failed(self, error: str) -> None:
        """Notify on cycle failure."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.notifier.notify_cycle_failed(date=date, error=error)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Architect v2")
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Processing mode",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send email report",
    )
    parser.add_argument(
        "--email-preview",
        action="store_true",
        help="Generate email preview without sending",
    )
    parser.add_argument(
        "--email-to",
        type=str,
        help="Override email recipient",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else "INFO"
    import os
    os.environ["LOG_LEVEL"] = log_level
    configure_logging()

    # Check for API key
    settings = get_settings()
    if not settings.anthropic_api_key:
        log.error("ANTHROPIC_API_KEY not set")
        print("Error: ANTHROPIC_API_KEY environment variable is required")
        sys.exit(1)

    # Run orchestrator
    architect = AIArchitect(mode=args.mode)
    success = architect.run()

    # Handle email CLI options
    if args.email or args.email_preview:
        recipients = [args.email_to] if args.email_to else None
        architect._send_email_report(
            preview_only=args.email_preview,
            recipients=recipients,
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
