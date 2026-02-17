"""
AI Architect v2 - GitHub Emerging Repos Collector

Discovers emerging repositories with rapid growth but low star count.
"""

from datetime import datetime, timezone
from typing import Any

from github import Github, GithubException
from github.Repository import Repository

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


class GitHubEmergingCollector(BaseCollector[Repository]):
    """
    Collector for emerging GitHub repositories.

    Looks for repos with:
    - Less than max_stars (default 100)
    - High growth rate (stars gained per week)
    - Relevant topics

    Growth rate detection is more valuable than static star counts.
    """

    DEFAULT_TOPICS = [
        "claude",
        "anthropic",
        "llm",
        "ai-agents",
        "langchain",
        "rag",
        "prompt-engineering",
    ]

    SEARCH_QUERIES = [
        "claude-api",
        "anthropic-claude",
        "claude-ai",
        "claude-sdk",
        "anthropic-sdk",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize GitHub emerging repos collector.

        Config options:
            max_stars: Maximum stars threshold (default 100)
            min_growth_rate: Minimum weekly growth multiplier (default 1.5)
            topics: List of topics to search
            max_items: Maximum items to collect
            github_token: GitHub API token
        """
        super().__init__(SourceType.GITHUB_EMERGING, config)

        self.max_stars = self.config.get("max_stars", 100)
        self.min_growth_rate = self.config.get("min_growth_rate", 1.5)
        self.topics = self.config.get("topics", self.DEFAULT_TOPICS)
        self.max_items = self.config.get("max_items", 30)

        token = self.config.get("github_token")
        self.github = Github(token) if token else Github()

    def _fetch(self) -> list[Repository]:
        """
        Search for emerging repositories.

        Returns:
            List of Repository objects
        """
        repos = []
        seen_full_names = set()

        # Search by topic
        for topic in self.topics[:5]:  # Limit topics to avoid rate limits
            try:
                query = f"topic:{topic} stars:<{self.max_stars} pushed:>2024-01-01"
                results = self.github.search_repositories(query, sort="stars", order="desc")

                for repo in results[:20]:
                    if repo.full_name not in seen_full_names:
                        seen_full_names.add(repo.full_name)
                        repos.append(repo)

            except GithubException as e:
                self._log.warning(
                    "topic_search_failed",
                    topic=topic,
                    error=str(e)[:200],
                )

        # Also search by keywords
        for query_term in self.SEARCH_QUERIES[:3]:
            try:
                query = f"{query_term} stars:<{self.max_stars}"
                results = self.github.search_repositories(query, sort="updated", order="desc")

                for repo in results[:15]:
                    if repo.full_name not in seen_full_names:
                        seen_full_names.add(repo.full_name)
                        repos.append(repo)

            except GithubException as e:
                self._log.warning(
                    "keyword_search_failed",
                    query=query_term,
                    error=str(e)[:200],
                )

        return repos[:self.max_items]

    def _parse(self, raw_item: Repository) -> CollectedItem | None:
        """
        Parse a GitHub repository into a CollectedItem.

        Args:
            raw_item: GitHub Repository

        Returns:
            CollectedItem
        """
        repo = raw_item

        # Calculate estimated growth rate
        # This is approximate since GitHub API doesn't provide historical star data
        stars = repo.stargazers_count
        age_days = (datetime.now(timezone.utc) - repo.created_at.replace(tzinfo=timezone.utc)).days
        age_weeks = max(age_days / 7, 1)
        stars_per_week = stars / age_weeks

        # Skip repos with low activity
        if stars_per_week < 1:
            return None

        # Build content
        content_parts = [
            f"**{repo.full_name}**",
            f"Stars: {stars} ({stars_per_week:.1f}/week)",
            f"Language: {repo.language or 'Unknown'}",
            f"Forks: {repo.forks_count}",
            f"Open Issues: {repo.open_issues_count}",
            f"Last Updated: {repo.updated_at.strftime('%Y-%m-%d')}",
            f"\n{repo.description or 'No description'}",
        ]

        if repo.topics:
            content_parts.append(f"\nTopics: {', '.join(repo.topics[:10])}")

        return CollectedItem(
            id=f"github_emerging_{repo.id}",
            source_type=SourceType.GITHUB_EMERGING,
            source_url=repo.html_url,
            title=f"[EMERGING] {repo.full_name}",
            content="\n".join(content_parts),
            summary=repo.description,
            author=repo.owner.login if repo.owner else None,
            published_at=repo.created_at.replace(tzinfo=timezone.utc),
            metadata={
                "full_name": repo.full_name,
                "stars": stars,
                "stars_per_week": round(stars_per_week, 2),
                "language": repo.language,
                "topics": list(repo.topics) if repo.topics else [],
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "is_fork": repo.fork,
                "license": repo.license.spdx_id if repo.license else None,
            },
        )


def collect_github_emerging(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect emerging GitHub repos.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = GitHubEmergingCollector(config)
    return collector.collect()
