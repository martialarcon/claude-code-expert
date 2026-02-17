"""
AI Architect v2 - Novelty Detector

Detects novelty of items by comparing with historical content in ChromaDB.
"""

from typing import Any

from ..collectors.base import CollectedItem
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("processor.novelty_detector")


class NoveltyDetector:
    """
    Detects how novel an item is compared to historical content.

    Uses ChromaDB vector similarity to find similar items
    and compute a novelty score.
    """

    def __init__(
        self,
        novelty_threshold: float = 0.3,
        similarity_threshold: float = 0.8,
        vector_store: Any | None = None,
    ):
        """
        Initialize novelty detector.

        Args:
            novelty_threshold: Minimum novelty to consider item novel
            similarity_threshold: Above this similarity, item is not novel
            vector_store: VectorStore instance (lazy loaded if None)
        """
        config = get_config()
        self.novelty_threshold = novelty_threshold or config.thresholds.novelty_score_min
        self.similarity_threshold = similarity_threshold
        self._vector_store = vector_store

    @property
    def vector_store(self):
        """Lazy load vector store."""
        if self._vector_store is None:
            from ..storage.vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    def compute_novelty(self, item: CollectedItem) -> float:
        """
        Compute novelty score for an item.

        Args:
            item: Item to check

        Returns:
            Novelty score (0-1, where 1 is completely novel)
        """
        # Build search text from title and content
        search_text = f"{item.title}\n{item.content[:1000]}"

        try:
            # Search for similar items
            results = self.vector_store.search(
                query=search_text,
                collection="items",
                n_results=5,
            )

            if not results or not results.get("distances"):
                # No similar items found = completely novel
                return 1.0

            # Get the best (lowest) distance
            # ChromaDB uses L2 distance by default
            distances = results["distances"][0]  # First query's results

            if not distances:
                return 1.0

            min_distance = min(distances)

            # Convert distance to similarity (0-1)
            # For L2 distance, smaller = more similar
            # Normalize to 0-1 range (assuming typical L2 distances 0-2)
            max_distance = 2.0
            similarity = 1.0 - min(min_distance / max_distance, 1.0)

            # Novelty is inverse of similarity
            novelty = 1.0 - similarity

            log.debug(
                "novelty_computed",
                item_id=item.id,
                min_distance=min_distance,
                similarity=similarity,
                novelty=novelty,
            )

            return novelty

        except Exception as e:
            log.warning(
                "novelty_check_failed",
                item_id=item.id,
                error=str(e)[:200],
            )
            # Default to moderate novelty if check fails
            return 0.5

    def check_novelty(self, item: CollectedItem) -> tuple[bool, float]:
        """
        Check if an item is novel enough to process.

        Args:
            item: Item to check

        Returns:
            Tuple of (is_novel, novelty_score)
        """
        novelty_score = self.compute_novelty(item)
        is_novel = novelty_score >= self.novelty_threshold

        return is_novel, novelty_score

    def filter_novel(
        self,
        items: list[CollectedItem],
        min_novelty: float | None = None,
    ) -> list[CollectedItem]:
        """
        Filter items to only include novel ones.

        Args:
            items: Items to filter
            min_novelty: Minimum novelty threshold (uses default if None)

        Returns:
            Filtered list with novelty scores applied
        """
        threshold = min_novelty or self.novelty_threshold
        novel_items = []

        log.info(
            "filtering_novelty",
            total_items=len(items),
            threshold=threshold,
        )

        for item in items:
            is_novel, score = self.check_novelty(item)

            if is_novel:
                item.novelty_score = score
                novel_items.append(item)
            else:
                log.debug(
                    "item_not_novel",
                    item_id=item.id,
                    novelty_score=score,
                )

        log.info(
            "novelty_filter_complete",
            passed=len(novel_items),
            filtered=len(items) - len(novel_items),
        )

        return novel_items

    def detect_duplicates(
        self,
        items: list[CollectedItem],
        similarity_threshold: float | None = None,
    ) -> list[tuple[CollectedItem, CollectedItem, float]]:
        """
        Find potential duplicates within a batch of items.

        Args:
            items: Items to check
            similarity_threshold: Threshold for duplicate detection

        Returns:
            List of (item1, item2, similarity) tuples
        """
        threshold = similarity_threshold or self.similarity_threshold
        duplicates = []

        # Batch all items for vectorization
        texts = [f"{item.title}\n{item.content[:500]}" for item in items]

        try:
            # Get embeddings for all items
            embeddings = self.vector_store.get_embeddings(texts)

            # Compare each pair
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    similarity = self._cosine_similarity(
                        embeddings[i],
                        embeddings[j],
                    )

                    if similarity >= threshold:
                        duplicates.append((items[i], items[j], similarity))

        except Exception as e:
            log.warning("duplicate_detection_failed", error=str(e)[:200])

        return duplicates

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


def detect_novelty(items: list[CollectedItem]) -> list[CollectedItem]:
    """
    Convenience function to filter items by novelty.

    Args:
        items: Items to filter

    Returns:
        Novel items with scores applied
    """
    detector = NoveltyDetector()
    return detector.filter_novel(items)
