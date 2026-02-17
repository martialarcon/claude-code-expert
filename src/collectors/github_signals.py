"""
AI Architect v2 - GitHub Signals Collector

Collects issues and PRs from critical repositories in the Claude ecosystem.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from github import Github, GithubException
from github.Issue import Issue
from github.PullRequest import PullRequest

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


@dataclass
class RepoTarget:
    """Target repository configuration."""
    owner: str
    repo: str


class GitHubSignalsCollector(BaseCollector[Issue | PullRequest]):
    """
    Collector for GitHub issues and PRs from critical repositories.

    Monitors repositories for:
    - New issues (bugs, features, questions)
    - Pull requests
    - Discussions (if available)
    """

    # Critical repos to monitor
    DEFAULT_REPOS = [
        RepoTarget(owner="anthropics", repo="anthropic-sdk-python"),
        RepoTarget(owner="anthropics", repo="claude-code"),
        RepoTarget(owner="anthropics", repo="claude-agent-sdk"),
    ]

    # Relevant labels to prioritize
    PRIORITY_LABELS = {
        "bug", "enhancement", "feature", "breaking-change",
        "documentation", "good first issue", "help wanted",
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize GitHub signals collector.

        Config options:
            repos: List of {owner, repo} dicts
            max_items: Maximum items per repo
            days_back: How many days back to look
            github_token: GitHub API token (optional, increases rate limits)
        """
        super().__init__(SourceType.GITHUB_SIGNALS, config)

        # Parse repo targets
        repo_configs = self.config.get("repos", [])
        self.repos = [
            RepoTarget(owner=r["owner"], repo=r["repo"])
            for r in repo_configs
        ] if repo_configs else self.DEFAULT_REPOS

        self.max_items = self.config.get("max_items", 50)
        self.days_back = self.config.get("days_back", 7)

        # Initialize GitHub client
        token = self.config.get("github_token")
        self.github = Github(token) if token else Github()

    def _fetch(self) -> list[Issue | PullRequest]:
        """
        Fetch issues and PRs from configured repositories.

        Returns:
            List of GitHub Issue and PullRequest objects
        """
        items = []

        for repo_target in self.repos:
            try:
                repo_items = self._fetch_repo(repo_target)
                items.extend(repo_items)
            except GithubException as e:
                self._log.warning(
                    "github_repo_error",
                    repo=f"{repo_target.owner}/{repo_target.repo}",
                    error=str(e)[:200],
                )

        return items[:self.max_items]

    def _fetch_repo(self, target: RepoTarget) -> list[Issue | PullRequest]:
        """
        Fetch items from a single repository.

        Args:
            target: Repository target

        Returns:
            List of issues and PRs
        """
        items = []
        repo_name = f"{target.owner}/{target.repo}"

        self._log.info("fetching_repo", repo=repo_name)

        try:
            repo = self.github.get_repo(repo_name)

            # Fetch recent issues
            issues = repo.get_issues(state="open", sort="updated")
            for issue in issues:
                if self._is_recent(issue.updated_at):
                    items.append(issue)
                else:
                    break  # Issues are sorted by update time

            # Fetch recent PRs
            pulls = repo.get_pulls(state="open", sort="updated")
            for pr in pulls:
                if self._is_recent(pr.updated_at):
                    items.append(pr)
                else:
                    break

        except GithubException as e:
            self._log.error(
                "repo_fetch_failed",
                repo=repo_name,
                error=str(e)[:200],
            )

        return items

    def _is_recent(self, dt: datetime) -> bool:
        """Check if datetime is within the lookback period."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age_days = (now - dt).days
        return age_days <= self.days_back

    def _parse(self, raw_item: Issue | PullRequest) -> CollectedItem | None:
        """
        Parse a GitHub issue or PR into a CollectedItem.

        Args:
            raw_item: GitHub Issue or PullRequest

        Returns:
            CollectedItem
        """
        is_pr = isinstance(raw_item, PullRequest)

        # Extract labels
        labels = [label.name for label in raw_item.labels]

        # Build content
        content_parts = []

        if is_pr:
            title_prefix = "[PR]"
            content_parts.append(f"**Pull Request: {raw_item.title}**")
            content_parts.append(f"State: {raw_item.state}")
            content_parts.append(f"Author: @{raw_item.user.login if raw_item.user else 'unknown'}")
            if raw_item.body:
                content_parts.append(f"\n{raw_item.body}")
        else:
            title_prefix = ""
            content_parts.append(f"**{raw_item.title}**")
            content_parts.append(f"State: {raw_item.state}")
            content_parts.append(f"Author: @{raw_item.user.login if raw_item.user else 'unknown'}")
            content_parts.append(f"Labels: {', '.join(labels) if labels else 'none'}")
            if raw_item.body:
                content_parts.append(f"\n{raw_item.body}")

        # Include comments count
        if hasattr(raw_item, "comments"):
            content_parts.append(f"\n*Comments: {raw_item.comments}*")

        title = f"{title_prefix} {raw_item.title}".strip()
        content = "\n".join(content_parts)

        return CollectedItem(
            id=f"github_{raw_item.id}",
            source_type=SourceType.GITHUB_SIGNALS,
            source_url=raw_item.html_url,
            title=title,
            content=content,
            author=raw_item.user.login if raw_item.user else None,
            published_at=raw_item.created_at.replace(tzinfo=timezone.utc),
            metadata={
                "repo": f"{raw_item.repository.full_name}" if raw_item.repository else "",
                "is_pr": is_pr,
                "state": raw_item.state,
                "labels": labels,
                "number": raw_item.number,
                "has_priority_label": bool(set(labels) & self.PRIORITY_LABELS),
                "comments_count": raw_item.comments if hasattr(raw_item, "comments") else 0,
            },
        )


def collect_github_signals(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect GitHub signals.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = GitHubSignalsCollector(config)
    return collector.collect()
