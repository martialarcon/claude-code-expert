"""
AI Architect v2 - StackOverflow Collector

Collects questions and answers related to Claude and AI development.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


@dataclass
class SOQuestion:
    """StackOverflow question data."""
    id: int
    title: str
    url: str
    body: str
    tags: list[str]
    score: int
    answer_count: int
    is_answered: bool
    author: str | None
    created_at: datetime


class StackOverflowCollector(BaseCollector[SOQuestion]):
    """
    Collector for StackOverflow questions.

    Searches for questions with relevant tags and keywords
    related to Claude and AI-assisted development.
    """

    API_BASE = "https://api.stackexchange.com/2.3"

    DEFAULT_TAGS = ["claude", "anthropic", "llm", "langchain", "openai-api"]
    SEARCH_TERMS = ["claude api", "anthropic claude", "claude-3", "claude-sonnet", "claude-opus"]

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize StackOverflow collector.

        Config options:
            tags: List of tags to search
            min_score: Minimum question score
            max_items: Maximum items to collect
            days_back: How many days back to search
        """
        super().__init__(SourceType.STACKOVERFLOW, config)

        self.tags = self.config.get("tags", self.DEFAULT_TAGS)
        self.min_score = self.config.get("min_score", 0)
        self.max_items = self.config.get("max_items", 30)
        self.days_back = self.config.get("days_back", 30)
        self.timeout = self.config.get("timeout", 30)

    def _fetch(self) -> list[SOQuestion]:
        """
        Search StackOverflow for relevant questions.

        Returns:
            List of SOQuestion objects
        """
        questions = []
        seen_ids = set()

        with httpx.Client(timeout=self.timeout) as client:
            # Search by tags
            for tag in self.tags[:3]:
                try:
                    tag_questions = self._search_by_tag(client, tag)
                    for q in tag_questions:
                        if q.id not in seen_ids:
                            seen_ids.add(q.id)
                            questions.append(q)
                except Exception as e:
                    self._log.warning(
                        "tag_search_failed",
                        tag=tag,
                        error=str(e)[:200],
                    )

            # Search by keywords
            for term in self.SEARCH_TERMS[:2]:
                try:
                    term_questions = self._search_by_term(client, term)
                    for q in term_questions:
                        if q.id not in seen_ids:
                            seen_ids.add(q.id)
                            questions.append(q)
                except Exception as e:
                    self._log.warning(
                        "term_search_failed",
                        term=term,
                        error=str(e)[:200],
                    )

        return questions[:self.max_items]

    def _search_by_tag(self, client: httpx.Client, tag: str) -> list[SOQuestion]:
        """
        Search questions by tag.

        Args:
            client: HTTP client
            tag: Tag to search

        Returns:
            List of SOQuestion objects
        """
        from datetime import timedelta

        from_date = int((datetime.now(timezone.utc) - timedelta(days=self.days_back)).timestamp())

        params = {
            "order": "desc",
            "sort": "creation",
            "tagged": tag,
            "site": "stackoverflow",
            "pagesize": 20,
            "fromdate": from_date,
            "filter": "withbody",
        }

        response = client.get(f"{self.API_BASE}/questions", params=params)
        response.raise_for_status()
        data = response.json()

        return [self._parse_api_item(item) for item in data.get("items", [])]

    def _search_by_term(self, client: httpx.Client, term: str) -> list[SOQuestion]:
        """
        Search questions by search term.

        Args:
            client: HTTP client
            term: Search term

        Returns:
            List of SOQuestion objects
        """
        params = {
            "order": "desc",
            "sort": "relevance",
            "intitle": term,
            "site": "stackoverflow",
            "pagesize": 15,
            "filter": "withbody",
        }

        response = client.get(f"{self.API_BASE}/search", params=params)
        response.raise_for_status()
        data = response.json()

        return [self._parse_api_item(item) for item in data.get("items", [])]

    def _parse_api_item(self, item: dict[str, Any]) -> SOQuestion:
        """Parse StackExchange API response item."""
        return SOQuestion(
            id=item["question_id"],
            title=self._clean_html(item.get("title", "")),
            url=f"https://stackoverflow.com/questions/{item['question_id']}",
            body=self._clean_html(item.get("body", "")),
            tags=item.get("tags", []),
            score=item.get("score", 0),
            answer_count=item.get("answer_count", 0),
            is_answered=item.get("is_answered", False),
            author=item.get("owner", {}).get("display_name"),
            created_at=datetime.fromtimestamp(item["creation_date"], tz=timezone.utc),
        )

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from text."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _parse(self, raw_item: SOQuestion) -> CollectedItem | None:
        """
        Convert SOQuestion to CollectedItem.

        Args:
            raw_item: SOQuestion

        Returns:
            CollectedItem
        """
        q = raw_item

        # Filter by score
        if q.score < self.min_score:
            return None

        # Build content
        content_parts = [
            f"**{q.title}**",
            f"Score: {q.score} | Answers: {q.answer_count} | Answered: {'Yes' if q.is_answered else 'No'}",
            f"Tags: {', '.join(q.tags)}",
            f"\n{q.body[:2000]}{'...' if len(q.body) > 2000 else ''}",
        ]

        return CollectedItem(
            id=f"so_{q.id}",
            source_type=SourceType.STACKOVERFLOW,
            source_url=q.url,
            title=q.title,
            content="\n".join(content_parts),
            summary=q.body[:500],
            author=q.author,
            published_at=q.created_at,
            metadata={
                "tags": q.tags,
                "score": q.score,
                "answer_count": q.answer_count,
                "is_answered": q.is_answered,
            },
        )


def collect_stackoverflow(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect StackOverflow questions.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = StackOverflowCollector(config)
    return collector.collect()
