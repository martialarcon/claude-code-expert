#!/usr/bin/env python3
"""
Test script for AI Architect notifications.

This script allows you to test the notification system without running
the full daily/weekly/monthly cycle.

Usage:
    python scripts/test_notifications.py --help
    python scripts/test_notifications.py --test daily
    python scripts/test_notifications.py --send "My custom message"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.notifier import Notifier, Priority, get_notifier


def test_daily_complete():
    """Test daily completion notification."""
    print("📤 Sending test daily complete notification...")
    notifier = get_notifier()

    result = notifier.notify_daily_complete(
        date=datetime.now().strftime("%Y-%m-%d"),
        items_analyzed=42,
        items_discarded=15,
        relevance_score=8,
        highlight="New test notification system",
    )

    if result:
        print("✅ Notification sent successfully!")
        print("   Check your ntfy.sh subscription for the message")
    else:
        print("❌ Failed to send notification (check config and internet)")

    return result


def test_daily_errors():
    """Test daily errors notification."""
    print("📤 Sending test daily errors notification...")
    notifier = get_notifier()

    result = notifier.notify_daily_errors(
        date=datetime.now().strftime("%Y-%m-%d"),
        items_analyzed=35,
        failed_collectors=["github", "arxiv"],
    )

    if result:
        print("✅ Notification sent successfully!")
        print("   Check your ntfy.sh subscription for the message")
    else:
        print("❌ Failed to send notification (check config and internet)")

    return result


def test_cycle_failed():
    """Test cycle failure notification."""
    print("📤 Sending test cycle failed notification...")
    notifier = get_notifier()

    result = notifier.notify_cycle_failed(
        date=datetime.now().strftime("%Y-%m-%d"),
        error="Test error: Connection timeout to API",
    )

    if result:
        print("✅ Notification sent successfully!")
        print("   Check your ntfy.sh subscription for the message")
    else:
        print("❌ Failed to send notification (check config and internet)")

    return result


def test_weekly_complete():
    """Test weekly completion notification."""
    print("📤 Sending test weekly complete notification...")
    notifier = get_notifier()

    result = notifier.notify_weekly_complete(
        week="Week 7, 2026",
        relevance_score=7,
        patterns=[
            "Increased AI adoption in enterprise",
            "New CUDA optimization techniques",
            "Edge AI acceleration frameworks",
        ],
    )

    if result:
        print("✅ Notification sent successfully!")
        print("   Check your ntfy.sh subscription for the message")
    else:
        print("❌ Failed to send notification (check config and internet)")

    return result


def test_monthly_complete():
    """Test monthly completion notification."""
    print("📤 Sending test monthly complete notification...")
    notifier = get_notifier()

    result = notifier.notify_monthly_complete(
        month="February 2026",
        relevance_score=8,
    )

    if result:
        print("✅ Notification sent successfully!")
        print("   Check your ntfy.sh subscription for the message")
    else:
        print("❌ Failed to send notification (check config and internet)")

    return result


def test_critical_signal():
    """Test critical signal notification."""
    print("📤 Sending test critical signal notification...")
    notifier = get_notifier()

    result = notifier.notify_critical_signal(
        title_text="Revolutionary AI Architecture Announced",
        source="GitHub",
        url="https://github.com/example/repo",
    )

    if result:
        print("✅ Notification sent successfully!")
        print("   Check your ntfy.sh subscription for the message")
    else:
        print("❌ Failed to send notification (check config and internet)")

    return result


def test_custom_message(message: str, title: str = None, priority: str = "default"):
    """Send a custom test message."""
    print(f"📤 Sending custom message...")
    notifier = get_notifier()

    priority_enum = Priority[priority.upper()] if priority else Priority.DEFAULT

    result = notifier.send(
        message=message,
        title=title or "Test Message",
        priority=priority_enum,
        tags=["test"],
    )

    if result:
        print("✅ Notification sent successfully!")
        print("   Check your ntfy.sh subscription for the message")
    else:
        print("❌ Failed to send notification (check config and internet)")

    return result


def show_config():
    """Show current notification configuration."""
    notifier = get_notifier()

    print("\n📋 Notification Configuration:")
    print(f"   Topic: {notifier.topic}")
    print(f"   Base URL: {notifier.base_url}")
    print(f"   Enabled: {notifier.enabled}")

    if notifier.enabled:
        print(f"\n📲 Subscribe to notifications at:")
        print(f"   https://ntfy.sh/{notifier.topic}")
        print(f"\n   You can:")
        print(f"   - Visit the web UI to see messages in real-time")
        print(f"   - Download the ntfy app (iOS/Android) for push notifications")
        print(f"   - Use curl to subscribe: curl ntfy.sh/{notifier.topic}")


def main():
    parser = argparse.ArgumentParser(
        description="Test AI Architect notification system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_notifications.py --config
  python scripts/test_notifications.py --test daily
  python scripts/test_notifications.py --test errors
  python scripts/test_notifications.py --test failed
  python scripts/test_notifications.py --test weekly
  python scripts/test_notifications.py --test monthly
  python scripts/test_notifications.py --test critical
  python scripts/test_notifications.py --send "My message"
  python scripts/test_notifications.py --send "My message" --title "Title" --priority high
        """,
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="Show current notification configuration",
    )

    parser.add_argument(
        "--test",
        choices=["daily", "errors", "failed", "weekly", "monthly", "critical"],
        help="Send a test notification",
    )

    parser.add_argument(
        "--send",
        metavar="MESSAGE",
        help="Send a custom message",
    )

    parser.add_argument(
        "--title",
        metavar="TITLE",
        help="Custom message title (with --send)",
    )

    parser.add_argument(
        "--priority",
        choices=["default", "low", "high", "urgent"],
        default="default",
        help="Message priority (with --send)",
    )

    args = parser.parse_args()

    # Show config if requested
    if args.config or (not args.test and not args.send):
        show_config()
        return 0

    # Test notifications
    if args.test == "daily":
        return 0 if test_daily_complete() else 1
    elif args.test == "errors":
        return 0 if test_daily_errors() else 1
    elif args.test == "failed":
        return 0 if test_cycle_failed() else 1
    elif args.test == "weekly":
        return 0 if test_weekly_complete() else 1
    elif args.test == "monthly":
        return 0 if test_monthly_complete() else 1
    elif args.test == "critical":
        return 0 if test_critical_signal() else 1

    # Custom message
    if args.send:
        return 0 if test_custom_message(args.send, args.title, args.priority) else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
