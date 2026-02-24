"""
ChromaDB Query Helper for chroma-query skill.

Provides structured querying and formatting for Claude Code agents.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..storage.vector_store import VectorStore


class ChromaQueryError(Exception):
    """Exception raised when ChromaDB query fails."""
    pass


@dataclass
class QueryResult:
    """A single query result with structured fields."""

    title: str
    content: str
    source: str
    score: float
    metadata: dict[str, Any]

    @property
    def date_str(self) -> str:
        """Return formatted date string."""
        if "date" in self.metadata:
            return self.metadata["date"][:10]  # YYYY-MM-DD
        return "unknown"


def query_chromadb(
    query: str,
    collections: list[str] | None = None,
    persist_directory: str | Path | None = None,
    n_results: int = 5,
    days: int | None = None,
) -> list[QueryResult]:
    """
    Query ChromaDB collections and return structured results.

    Args:
        query: Search query text
        collections: Collections to search (default: ["items", "analysis"])
        persist_directory: ChromaDB persist directory
        n_results: Max results per collection
        days: Filter to last N days (optional)

    Returns:
        List of QueryResult objects sorted by score

    Raises:
        ChromaQueryError: If query fails
    """
    if collections is None:
        collections = ["items", "analysis"]

    try:
        vs = VectorStore(persist_directory=persist_directory)
    except Exception as e:
        raise ChromaQueryError(f"Failed to initialize VectorStore: {e}") from e

    all_results: list[QueryResult] = []
    cutoff_date = None

    if days is not None:
        cutoff_date = datetime.now() - timedelta(days=days)

    for collection in collections:
        try:
            raw_results = vs.search(
                query=query,
                collection=collection,
                n_results=n_results,
            )

            # Parse results
            ids = raw_results.get("ids", [[]])[0]
            documents = raw_results.get("documents", [[]])[0]
            metadatas = raw_results.get("metadatas", [[]])[0]
            distances = raw_results.get("distances", [[]])[0]

            for i, doc_id in enumerate(ids):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0

                # Convert distance to similarity score (lower distance = higher score)
                score = max(0.0, 1.0 - (distance / 2.0))

                # Date filtering
                if cutoff_date and "date" in metadata:
                    try:
                        item_date = datetime.fromisoformat(metadata["date"])
                        if item_date < cutoff_date:
                            continue
                    except (ValueError, TypeError):
                        pass

                result = QueryResult(
                    title=metadata.get("title", doc_id),
                    content=documents[i] if i < len(documents) else "",
                    source=collection,
                    score=round(score, 2),
                    metadata=metadata,
                )
                all_results.append(result)

        except Exception as e:
            # Log but continue with other collections
            continue

    # Sort by score descending
    all_results.sort(key=lambda r: r.score, reverse=True)

    return all_results


def format_results_markdown(results: list[QueryResult], query: str) -> str:
    """
    Format query results as structured markdown.

    Args:
        results: List of QueryResult objects
        query: Original query string

    Returns:
        Formatted markdown string
    """
    if not results:
        return f"""## Resumen

No se encontraron resultados para: "{query}"

## Sugerencias

- Intenta con términos más generales
- Elimina el filtro de días si lo usaste
- Prueba con palabras clave alternativas
"""

    # Build summary
    top_sources = set(r.source for r in results[:3])
    sources_str = ", ".join(top_sources)

    lines = [
        f"## Resumen",
        f"",
        f"Encontrados {len(results)} resultados para \"{query}\" en: {sources_str}",
        f"",
        f"## Fuentes ({len(results)} resultados)",
        f"",
    ]

    for i, result in enumerate(results, 1):
        lines.append(f"{i}. **{result.title}** - {result.date_str} - score: {result.score}")
        # Truncate content for preview
        content_preview = result.content[:200]
        if len(result.content) > 200:
            content_preview += "..."
        lines.append(f"   > {content_preview}")
        lines.append("")

    # Add details section
    lines.extend([
        "## Detalles",
        "",
    ])

    # Group by source
    by_source: dict[str, list[QueryResult]] = {}
    for r in results:
        by_source.setdefault(r.source, []).append(r)

    for source, source_results in by_source.items():
        lines.append(f"### {source.capitalize()} ({len(source_results)} resultados)")
        lines.append("")

        # Extract key terms from titles
        titles = [r.title for r in source_results[:5]]
        lines.append("Temas principales:")
        for title in titles:
            lines.append(f"- {title}")
        lines.append("")

    return "\n".join(lines)


# CLI entry point for skill usage
def main():
    """CLI entry point for chroma-query skill."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Query ChromaDB")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--days", type=int, help="Filter to last N days")
    parser.add_argument("--collection", choices=["items", "analysis", "both"],
                       default="both", help="Collection to search")
    parser.add_argument("--n-results", type=int, default=5, help="Max results")

    args = parser.parse_args()

    collections = ["items", "analysis"] if args.collection == "both" else [args.collection]

    try:
        results = query_chromadb(
            query=args.query,
            collections=collections,
            n_results=args.n_results,
            days=args.days,
        )

        output = format_results_markdown(results, args.query)
        print(output)

    except ChromaQueryError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
