"""
AI Architect v2 - GitHub Consolidated Repos Collector

Collects established repositories with significant star counts.
Migrated from v1 with updated filters.
"""

from datetime import datetime, timezone
from typing import Any

from github import Github, GithubException
from github.Repository import Repository

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


class GitHubReposCollector(BaseCollector[Repository]):
    """
    Collector for consolidated GitHub repositories.

    Looks for repos with:
    - More than min_stars (default 100)
    - Relevant topics
    - Recent activity

    Sorts by trending weekly to find currently popular repos.
    """

    DEFAULT_TOPICS = [
        "claude",
        "anthropic",
        "llm",
        "ai-agents",
        "langchain",
        "rag",
        "prompt-engineering",
        "chatbot",
        "generative-ai",
    ]

    TRENDING_QUERIES = [
        "claude created:>2024-01-01 stars:>100",
        "anthropic-api created:>2024-01-01 stars:>100",
        "claude-sdk stars:>100",
        "anthropic claude stars:>100",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize GitHub repos collector.

        Config options:
            min_stars: Minimum stars threshold (default 100)
            topics: List of topics to search
            max_items: Maximum items to collect
            github_token: GitHub API token
        """
        super().__init__(SourceType.GITHUB_REPOS, config)

        self.min_stars = self.config.get("min_stars", 100)
        self.topics = self.config.get("topics", self.DEFAULT_TOPICS)
        self.max_items = self.config.get("max_items", 30)

        token = self.config.get("github_token")
        self.github = Github(token) if token else Github()

    def _fetch(self) -> list[Repository]:
        """
        Search for consolidated repositories.

        Returns:
            List of Repository objects
        """
        repos = []
        seen_full_names = set()

        # Search by trending queries
        for query in self.TRENDING_QUERIES[:3]:
            try:
                results = self.github.search_repositories(
                    query,
                    sort="stars",
                    order="desc",
                )

                for repo in results[:25]:
                    if repo.full_name not in seen_full_names:
                        if repo.stargazers_count >= self.min_stars:
                            seen_full_names.add(repo.full_name)
                            repos.append(repo)

            except GithubException as e:
                self._log.warning(
                    "search_failed",
                    query=query,
                    error=str(e)[:200],
                )

        # Search by topic for completeness
        for topic in self.topics[:5]:
            try:
                query = f"topic:{topic} stars:>{self.min_stars} pushed:>2024-06-01"
                results = self.github.search_repositories(query, sort="stars", order="desc")

                for repo in results[:15]:
                    if repo.full_name not in seen_full_names:
                        seen_full_names.add(repo.full_name)
                        repos.append(repo)

            except GithubException as e:
                self._log.warning(
                    "topic_search_failed",
                    topic=topic,
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

        # Build content
        content_parts = [
            f"**{repo.full_name}**",
            f"⭐ {repo.stargazers_count} stars",
            f"Language: {repo.language or 'Unknown'}",
            f"Forks: {repo.forks_count}",
            f"Open Issues: {repo.open_issues_count}",
            f"Created: {repo.created_at.strftime('%Y-%m-%d')}",
            f"Last Updated: {repo.updated_at.strftime('%Y-%m-%d')}",
        ]

        if repo.description:
            content_parts.append(f"\n{repo.description}")

        if repo.topics:
            content_parts.append(f"\nTopics: {', '.join(repo.topics[:10])}")

        if repo.homepage:
            content_parts.append(f"\nHomepage: {repo.homepage}")

        return CollectedItem(
            id=f"github_repo_{repo.id}",
            source_type=SourceType.GITHUB_REPOS,
            source_url=repo.html_url,
            title=repo.full_name,
            content="\n".join(content_parts),
            summary=repo.description,
            author=repo.owner.login if repo.owner else None,
            published_at=repo.pushed_at.replace(tzinfo=timezone.utc) if repo.pushed_at else repo.created_at.replace(tzinfo=timezone.utc),
            metadata={
                "full_name": repo.full_name,
                "stars": repo.stargazers_count,
                "language": repo.language,
                "topics": list(repo.topics) if repo.topics else [],
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "is_fork": repo.fork,
                "license": repo.license.spdx_id if repo.license else None,
                "homepage": repo.homepage,
                "has_wiki": repo.has_wiki,
                "has_pages": repo.has_pages,
            },
        )


def collect_github_repos(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect consolidated GitHub repos.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = GitHubReposCollector(config)
    return collector.collect()
