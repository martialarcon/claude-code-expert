"""
AI Architect v2 - Base Collector

Abstract base class for all data collectors with common functionality.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

from ..utils.logger import get_logger

log = get_logger("collector.base")


class SourceType(str, Enum):
    """Types of data sources."""
    DOCS = "docs"
    GITHUB_SIGNALS = "github_signals"
    GITHUB_EMERGING = "github_emerging"
    GITHUB_REPOS = "github_repos"
    BLOGS = "blogs"
    STACKOVERFLOW = "stackoverflow"
    PODCASTS = "podcasts"
    PACKAGES = "packages"
    JOBS = "jobs"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    ENGINEERING_BLOGS = "engineering_blogs"
    ARXIV = "arxiv"
    YOUTUBE = "youtube"
    CONFERENCES = "conferences"


@dataclass
class CollectedItem:
    """
    A single collected item from any source.

    This is the canonical representation of an item flowing through the pipeline.
    """
    # Identity
    id: str                              # Unique identifier (hash of content + source)
    source_type: SourceType              # Type of source
    source_url: str                      # Original URL

    # Content
    title: str                           # Item title
    content: str                         # Full text content
    summary: str | None = None           # Brief summary (if available from source)

    # Metadata
    author: str | None = None            # Author/creator
    published_at: datetime | None = None # Publication timestamp
    collected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Source-specific metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Processing state
    signal_score: int | None = None      # Assigned by signal_ranker (1-10)
    novelty_score: float | None = None   # Assigned by novelty_detector (0-1)
    impact: str | None = None            # Assigned by impact_classifier
    maturity: str | None = None          # Assigned by maturity_classifier

    def compute_id(self) -> str:
        """Generate a unique ID based on content hash."""
        content_hash = hashlib.sha256(
            f"{self.source_type}:{self.source_url}:{self.title}".encode()
        ).hexdigest()[:16]
        return f"{self.source_type.value}_{content_hash}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "source_type": self.source_type.value,
            "source_url": self.source_url,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "author": self.author,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "collected_at": self.collected_at.isoformat(),
            "metadata": self.metadata,
            "signal_score": self.signal_score,
            "novelty_score": self.novelty_score,
            "impact": self.impact,
            "maturity": self.maturity,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class CollectionResult:
    """Result of a collection run."""
    source_type: SourceType
    items: list[CollectedItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    items_before_dedup: int = 0
    items_deduplicated: int = 0

    @property
    def success(self) -> bool:
        """Whether collection was successful (has items and no critical errors)."""
        return len(self.items) > 0 or len(self.errors) == 0

    @property
    def total_count(self) -> int:
        """Total items collected."""
        return len(self.items)


T = TypeVar("T")


class BaseCollector(ABC, Generic[T]):
    """
    Abstract base class for all collectors.

    Provides:
    - Common interface with collect() and validate()
    - Deduplication support
    - Error handling
    - Logging

    Subclasses must implement:
    - _fetch(): Fetch raw data from source
    - _parse(): Parse raw data into CollectedItem objects
    """

    def __init__(self, source_type: SourceType, config: dict[str, Any] | None = None):
        """
        Initialize collector.

        Args:
            source_type: Type of data source
            config: Collector-specific configuration
        """
        self.source_type = source_type
        self.config = config or {}
        self._seen_ids: set[str] = set()
        self._log = get_logger(f"collector.{source_type.value}")

    @property
    def enabled(self) -> bool:
        """Whether this collector is enabled."""
        return self.config.get("enabled", True)

    @abstractmethod
    def _fetch(self) -> list[T]:
        """
        Fetch raw data from the source.

        Returns:
            List of raw data items (source-specific format)

        Raises:
            CollectionError: If fetching fails
        """
        pass

    @abstractmethod
    def _parse(self, raw_item: T) -> CollectedItem | None:
        """
        Parse a raw item into a CollectedItem.

        Args:
            raw_item: Raw item from source

        Returns:
            CollectedItem or None if item should be skipped
        """
        pass

    def _deduplicate(self, items: list[CollectedItem]) -> list[CollectedItem]:
        """
        Remove duplicate items based on ID.

        Args:
            items: List of items to deduplicate

        Returns:
            Deduplicated list
        """
        unique_items = []
        for item in items:
            if item.id not in self._seen_ids:
                self._seen_ids.add(item.id)
                unique_items.append(item)

        return unique_items

    def validate(self, item: CollectedItem) -> bool:
        """
        Validate a collected item.

        Override in subclasses for source-specific validation.

        Args:
            item: Item to validate

        Returns:
            True if item is valid
        """
        if not item.title or not item.title.strip():
            return False
        if not item.content or not item.content.strip():
            return False
        if not item.source_url:
            return False
        return True

    def collect(self) -> CollectionResult:
        """
        Run the collection process.

        Returns:
            CollectionResult with items and metadata
        """
        import time

        start_time = time.time()
        result = CollectionResult(source_type=self.source_type)

        if not self.enabled:
            self._log.info("collector_disabled", source_type=self.source_type.value)
            return result

        try:
            self._log.info("collection_starting", source_type=self.source_type.value)

            # Fetch raw data
            raw_items = self._fetch()
            result.items_before_dedup = len(raw_items)

            self._log.info(
                "raw_items_fetched",
                source_type=self.source_type.value,
                count=len(raw_items),
            )

            # Parse items
            parsed_items = []
            for raw_item in raw_items:
                try:
                    item = self._parse(raw_item)
                    if item and self.validate(item):
                        # Ensure ID is computed
                        if not item.id:
                            item.id = item.compute_id()
                        parsed_items.append(item)
                except Exception as e:
                    self._log.warning(
                        "parse_error",
                        source_type=self.source_type.value,
                        error=str(e)[:200],
                    )
                    result.errors.append(f"Parse error: {str(e)[:100]}")

            # Deduplicate
            result.items = self._deduplicate(parsed_items)
            result.items_deduplicated = len(parsed_items) - len(result.items)

            self._log.info(
                "collection_complete",
                source_type=self.source_type.value,
                items=len(result.items),
                deduplicated=result.items_deduplicated,
            )

        except Exception as e:
            self._log.error(
                "collection_failed",
                source_type=self.source_type.value,
                error=str(e)[:500],
            )
            result.errors.append(str(e)[:500])

        result.duration_seconds = time.time() - start_time
        return result

    def reset_seen(self) -> None:
        """Reset the seen items cache (for testing or periodic cleanup)."""
        self._seen_ids.clear()


class CollectionError(Exception):
    """Error during collection."""
    pass
