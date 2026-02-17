"""
AI Architect v2 - Vector Store (ChromaDB)

Embedded ChromaDB for vector storage with ARM64 compatibility.
"""

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("storage.vector_store")


# Default collections as per plan
DEFAULT_COLLECTIONS = ["items", "analysis", "synthesis", "snapshots"]


class VectorStore:
    """
    Wrapper for ChromaDB vector storage.

    Uses embedded mode (no separate server) for 8GB RAM constraint.
    Compatible with ARM64/Jetson Orin Nano.
    """

    def __init__(
        self,
        persist_directory: str | Path | None = None,
        collections: list[str] | None = None,
    ):
        """
        Initialize vector store.

        Args:
            persist_directory: Directory for persistent storage
            collections: List of collection names to create
        """
        config = get_config()

        self.persist_directory = Path(
            persist_directory or config.storage.chromadb.persist_directory
        )
        self.collections = collections or config.storage.chromadb.collections or DEFAULT_COLLECTIONS

        # Ensure directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client (embedded mode)
        self._client: chromadb.Client | None = None
        self._collections: dict[str, chromadb.Collection] = {}

        log.info(
            "vector_store_init",
            persist_dir=str(self.persist_directory),
            collections=self.collections,
        )

    @property
    def client(self) -> chromadb.Client:
        """Lazy load ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    def get_collection(self, name: str) -> chromadb.Collection:
        """
        Get or create a collection.

        Args:
            name: Collection name

        Returns:
            Collection object
        """
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "l2"},
            )
            log.debug("collection_created", name=name)

        return self._collections[name]

    def add(
        self,
        collection: str,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Add documents to a collection.

        Args:
            collection: Collection name
            documents: List of document texts
            ids: List of unique IDs
            metadatas: Optional list of metadata dicts
        """
        col = self.get_collection(collection)

        col.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )

        log.debug(
            "documents_added",
            collection=collection,
            count=len(documents),
        )

    def search(
        self,
        query: str,
        collection: str = "items",
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Search for similar documents.

        Args:
            query: Query text
            collection: Collection to search
            n_results: Number of results
            where: Optional metadata filter

        Returns:
            Dict with ids, documents, metadatas, distances
        """
        col = self.get_collection(collection)

        results = col.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        return results

    def search_by_embedding(
        self,
        embedding: list[float],
        collection: str = "items",
        n_results: int = 5,
    ) -> dict[str, Any]:
        """
        Search using an embedding vector.

        Args:
            embedding: Query embedding
            collection: Collection to search
            n_results: Number of results

        Returns:
            Dict with ids, documents, metadatas, distances
        """
        col = self.get_collection(collection)

        results = col.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        return results

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Get embeddings for texts.

        Uses ChromaDB's default embedding function.

        Args:
            texts: Texts to embed

        Returns:
            List of embedding vectors
        """
        # Get the default embedding function from a collection
        col = self.get_collection("items")

        # Use ChromaDB's embedding function
        embeddings = col._embedding_function(texts)

        return embeddings

    def delete(
        self,
        collection: str,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> None:
        """
        Delete documents from a collection.

        Args:
            collection: Collection name
            ids: IDs to delete
            where: Metadata filter for deletion
        """
        col = self.get_collection(collection)

        col.delete(ids=ids, where=where)

        log.debug(
            "documents_deleted",
            collection=collection,
            ids_count=len(ids) if ids else None,
        )

    def count(self, collection: str) -> int:
        """
        Count documents in a collection.

        Args:
            collection: Collection name

        Returns:
            Document count
        """
        col = self.get_collection(collection)
        return col.count()

    def get_stats(self) -> dict[str, int]:
        """
        Get statistics for all collections.

        Returns:
            Dict of collection_name -> count
        """
        stats = {}
        for name in self.collections:
            try:
                stats[name] = self.count(name)
            except Exception:
                stats[name] = 0

        return stats

    def reset(self) -> None:
        """Reset all collections (for testing)."""
        self.client.reset()
        self._collections.clear()
        log.warning("vector_store_reset")


# Global instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create the global VectorStore instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def reset_vector_store() -> None:
    """Reset the global VectorStore (for testing)."""
    global _vector_store
    if _vector_store is not None:
        _vector_store.reset()
    _vector_store = None
