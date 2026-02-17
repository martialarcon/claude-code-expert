"""
AI Architect v2 - Notifier

Sends notifications via ntfy.sh (free, no dependencies, mobile push).
"""

from enum import Enum
from typing import Any

import httpx

from .config import get_config, get_settings
from .logger import get_logger

log = get_logger("utils.notifier")


class Priority(str, Enum):
    """Notification priority levels."""
    DEFAULT = "default"
    LOW = "low"
    HIGH = "high"
    URGENT = "urgent"


class Notifier:
    """
    Sends notifications via ntfy.sh.

    ntfy.sh is a free, open-source notification service
    with no signup required and native mobile push.
    """

    def __init__(
        self,
        topic: str | None = None,
        enabled: bool | None = None,
    ):
        """
        Initialize notifier.

        Args:
            topic: ntfy.sh topic name
            enabled: Whether notifications are enabled
        """
        config = get_config()
        settings = get_settings()

        self.topic = topic or config.notifications.ntfy.topic or settings.ntfy_topic
        self.enabled = enabled if enabled is not None else config.notifications.ntfy.enabled
        self.base_url = config.notifications.ntfy.url or "https://ntfy.sh"

    def send(
        self,
        message: str,
        title: str | None = None,
        priority: Priority = Priority.DEFAULT,
        tags: list[str] | None = None,
        click_url: str | None = None,
    ) -> bool:
        """
        Send a notification.

        Args:
            message: Notification message
            title: Optional title
            priority: Message priority
            tags: Optional emoji tags
            click_url: URL to open when notification is clicked

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            log.debug("notifications_disabled")
            return False

        url = f"{self.base_url}/{self.topic}"

        headers = {
            "Priority": priority.value,
        }

        if title:
            headers["Title"] = title

        if tags:
            headers["Tags"] = ",".join(tags)

        if click_url:
            headers["Click"] = click_url

        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    url,
                    content=message,
                    headers=headers,
                )
                response.raise_for_status()

            log.info(
                "notification_sent",
                topic=self.topic,
                priority=priority.value,
                title=title,
            )
            return True

        except httpx.HTTPError as e:
            log.error(
                "notification_failed",
                error=str(e)[:200],
                topic=self.topic,
            )
            return False

    def notify_daily_complete(
        self,
        date: str,
        items_analyzed: int,
        items_discarded: int,
        relevance_score: int,
        highlight: str | None = None,
    ) -> bool:
        """
        Send daily cycle completion notification.

        Args:
            date: Date string
            items_analyzed: Number of items analyzed
            items_discarded: Number of items discarded
            relevance_score: Day's relevance score (1-10)
            highlight: Optional highlight text

        Returns:
            True if sent successfully
        """
        title = f"AI Architect - {date}"

        lines = [
            "✅ Daily cycle complete",
            f"Items: {items_analyzed} analyzed, {items_discarded} discarded",
            f"Relevance: {relevance_score}/10",
        ]

        if highlight:
            lines.append(f"Highlight: {highlight[:100]}")

        message = "\n".join(lines)

        return self.send(
            message=message,
            title=title,
            priority=Priority.DEFAULT,
            tags=["white_check_mark", "robot"],
        )

    def notify_daily_errors(
        self,
        date: str,
        items_analyzed: int,
        failed_collectors: list[str],
    ) -> bool:
        """
        Send daily cycle completion with errors notification.

        Args:
            date: Date string
            items_analyzed: Number of items analyzed
            failed_collectors: List of failed collector names

        Returns:
            True if sent successfully
        """
        title = f"AI Architect - {date}"

        message = (
            "⚠️ Daily cycle with errors\n"
            f"Items: {items_analyzed} analyzed\n"
            f"Errors in: {', '.join(failed_collectors[:5])}"
        )

        return self.send(
            message=message,
            title=title,
            priority=Priority.HIGH,
            tags=["warning", "robot"],
        )

    def notify_cycle_failed(
        self,
        date: str,
        error: str,
    ) -> bool:
        """
        Send cycle failure notification.

        Args:
            date: Date string
            error: Error message

        Returns:
            True if sent successfully
        """
        title = f"AI Architect FAILED - {date}"

        return self.send(
            message=f"🔴 {error[:500]}",
            title=title,
            priority=Priority.URGENT,
            tags=["rotating_light", "x"],
        )

    def notify_weekly_complete(
        self,
        week: str,
        relevance_score: int,
        patterns: list[str],
    ) -> bool:
        """
        Send weekly synthesis completion notification.

        Args:
            week: Week string
            relevance_score: Week's relevance score
            patterns: List of detected patterns

        Returns:
            True if sent successfully
        """
        title = f"AI Architect Weekly - {week}"

        pattern_text = "\n".join(f"- {p[:50]}" for p in patterns[:3])
        message = (
            "📊 Weekly synthesis\n"
            f"Relevance: {relevance_score}/10\n"
            f"\nPatterns:\n{pattern_text}"
        )

        return self.send(
            message=message,
            title=title,
            priority=Priority.DEFAULT,
            tags=["chart_with_upwards_trend", "robot"],
        )

    def notify_monthly_complete(
        self,
        month: str,
        relevance_score: int,
    ) -> bool:
        """
        Send monthly report completion notification.

        Args:
            month: Month string
            relevance_score: Month's relevance score

        Returns:
            True if sent successfully
        """
        title = f"AI Architect Monthly - {month}"

        return self.send(
            message=f"📈 Monthly report\nRelevance: {relevance_score}/10",
            title=title,
            priority=Priority.DEFAULT,
            tags=["bar_chart", "robot"],
        )

    def notify_critical_signal(
        self,
        title_text: str,
        source: str,
        url: str,
    ) -> bool:
        """
        Send critical signal notification (signal_score = 10).

        Args:
            title_text: Item title
            source: Source type
            url: Item URL

        Returns:
            True if sent successfully
        """
        title = "Critical Signal Detected"

        message = f"🚨 {title_text}\n{source} — {url}"

        return self.send(
            message=message,
            title=title,
            priority=Priority.HIGH,
            tags=["rotating_light", "fire"],
            click_url=url,
        )


# Global instance
_notifier: Notifier | None = None


def get_notifier() -> Notifier:
    """Get or create the global Notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


def notify_daily_complete(*args, **kwargs) -> bool:
    """Convenience function for daily completion notification."""
    return get_notifier().notify_daily_complete(*args, **kwargs)


def notify_cycle_failed(*args, **kwargs) -> bool:
    """Convenience function for cycle failure notification."""
    return get_notifier().notify_cycle_failed(*args, **kwargs)
