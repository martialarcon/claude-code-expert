# ChromaDB Query Skill + Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a skill and agent for interactive ChromaDB queries with structured output.

**Architecture:** Python helper module for querying + formatting, skill instructs Claude to use it, agent provides conversational interface.

**Tech Stack:** Python, ChromaDB (existing), pytest

---

## Task 1: Create Query Helper Module

**Files:**
- Create: `src/utils/chroma_query.py`
- Create: `tests/utils/test_chroma_query.py`

**Step 1: Write the failing test**

```python
"""Tests for chroma_query helper module."""

import pytest
from src.utils.chroma_query import (
    ChromaQueryError,
    QueryResult,
    query_chromadb,
)


class TestQueryResult:
    """Test QueryResult dataclass."""

    def test_query_result_creation(self):
        """Should create QueryResult with all fields."""
        result = QueryResult(
            title="Test Title",
            content="Test content",
            source="items",
            score=0.85,
            metadata={"date": "2026-02-24"},
        )
        assert result.title == "Test Title"
        assert result.score == 0.85


class TestQueryChromaDB:
    """Test query_chromadb function."""

    def test_query_returns_list_of_results(self, tmp_path):
        """Should return list of QueryResult objects."""
        from src.storage.vector_store import VectorStore

        # Setup test store
        vs = VectorStore(persist_directory=str(tmp_path / "chroma"))
        vs.add(
            collection="items",
            documents=["Claude Code is an AI assistant for coding"],
            ids=["test-1"],
            metadatas=[{"title": "Test Doc", "source_type": "docs"}],
        )

        results = query_chromadb(
            query="coding assistant",
            collections=["items"],
            persist_directory=str(tmp_path / "chroma"),
            n_results=5,
        )

        assert isinstance(results, list)
        assert len(results) >= 1
        assert all(isinstance(r, QueryResult) for r in results)

    def test_query_with_days_filter(self, tmp_path):
        """Should filter results by days."""
        from datetime import datetime, timedelta
        from src.storage.vector_store import VectorStore

        vs = VectorStore(persist_directory=str(tmp_path / "chroma"))

        # Old item
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        vs.add(
            collection="items",
            documents=["Old content"],
            ids=["old-1"],
            metadatas=[{"title": "Old", "date": old_date}],
        )

        # Recent item
        recent_date = datetime.now().isoformat()
        vs.add(
            collection="items",
            documents=["Recent content"],
            ids=["recent-1"],
            metadatas=[{"title": "Recent", "date": recent_date}],
        )

        results = query_chromadb(
            query="content",
            collections=["items"],
            persist_directory=str(tmp_path / "chroma"),
            n_results=5,
            days=7,
        )

        # Should only return recent item
        assert len(results) == 1
        assert results[0].title == "Recent"

    def test_query_multiple_collections(self, tmp_path):
        """Should search across multiple collections."""
        from src.storage.vector_store import VectorStore

        vs = VectorStore(persist_directory=str(tmp_path / "chroma"))
        vs.add(
            collection="items",
            documents=["Item document"],
            ids=["item-1"],
            metadatas=[{"title": "Item"}],
        )
        vs.add(
            collection="analysis",
            documents=["Analysis document"],
            ids=["analysis-1"],
            metadatas=[{"title": "Analysis"}],
        )

        results = query_chromadb(
            query="document",
            collections=["items", "analysis"],
            persist_directory=str(tmp_path / "chroma"),
            n_results=5,
        )

        assert len(results) >= 2


class TestFormatResults:
    """Test result formatting."""

    def test_format_empty_results(self):
        """Should handle empty results gracefully."""
        from src.utils.chroma_query import format_results_markdown

        output = format_results_markdown([], "test query")
        assert "No se encontraron resultados" in output

    def test_format_with_results(self):
        """Should format results in markdown."""
        from src.utils.chroma_query import format_results_markdown

        results = [
            QueryResult(
                title="Test Title",
                content="Test content here",
                source="items",
                score=0.92,
                metadata={"date": "2026-02-24", "source_type": "blog"},
            )
        ]

        output = format_results_markdown(results, "test query")

        assert "## Resumen" in output
        assert "## Fuentes" in output
        assert "Test Title" in output
        assert "0.92" in output


class TestChromaQueryError:
    """Test ChromaQueryError exception."""

    def test_error_is_exception(self):
        """Should be an exception type."""
        assert issubclass(ChromaQueryError, Exception)

    def test_error_with_message(self):
        """Should accept message argument."""
        error = ChromaQueryError("Test error")
        assert str(error) == "Test error"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_chroma_query.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.utils.chroma_query'"

**Step 3: Create the test directory**

```bash
mkdir -p tests/utils
touch tests/utils/__init__.py
```

**Step 4: Write minimal implementation**

Create `src/utils/chroma_query.py`:

```python
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
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/utils/test_chroma_query.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/utils/chroma_query.py tests/utils/
git commit -m "feat: add chroma_query helper module for structured ChromaDB queries

- QueryResult dataclass for structured results
- query_chromadb() with multi-collection and date filtering
- format_results_markdown() for structured output
- CLI entry point for skill usage

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Create the Skill

**Files:**
- Create: `.claude/skills/chroma-query/SKILL.md`

**Step 1: Create skill directory**

```bash
mkdir -p .claude/skills/chroma-query
```

**Step 2: Create SKILL.md**

```markdown
---
name: chroma-query
description: >
  Busca información en ChromaDB y retorna resultados estructurados.
  Usar cuando el usuario pregunte sobre el ecosistema Claude Code,
  tendencias, o información técnica almacenada. Invocado con /chroma-query.
---

# ChromaDB Query

Busca en la base de datos vectorial (items + analysis) y retorna
resultados con formato estructurado: resumen, fuentes, detalles.

## Uso

```
/chroma-query "tu pregunta"
/chroma-query "MCP servers" --days 7
/chroma-query "claude code patterns" --collection analysis
```

## Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| query | requerido | Texto de búsqueda |
| --days | ninguno | Filtrar a últimos N días |
| --collection | both | Colección: items, analysis, both |
| --n-results | 5 | Máximo resultados |

## Proceso

1. Ejecutar el helper Python:

```bash
python3 -m src.utils.chroma_query "QUERY" [--days N] [--collection X]
```

2. El output ya viene formateado en markdown estructurado

3. Si hay resultados, presentarlos directamente

4. Si no hay resultados, sugerir:
   - Términos más generales
   - Eliminar filtro de días
   - Colección alternativa

## Output Format

El comando retorna markdown con esta estructura:

```markdown
## Resumen
<1-2 oraciones>

## Fuentes (N resultados)
1. **Título** - fecha - score: X.XX
   > Fragmento...

## Detalles
<Por colección con temas principales>
```

## Importante

- Siempre ejecutar el comando, no inventar resultados
- Las colecciones disponibles son: items, analysis
- El score es similitud (0-1, mayor = más relevante)
- Citar fuentes con score en respuestas
```

**Step 3: Commit**

```bash
git add .claude/skills/chroma-query/SKILL.md
git commit -m "feat: add chroma-query skill for ChromaDB searches

- Skill invokes Python helper module
- Supports --days and --collection parameters
- Returns structured markdown output

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Create the Agent

**Files:**
- Create: `.claude/agents/chroma-agent.md`

**Step 1: Create agent file**

```markdown
# @chroma-agent

## Purpose

Agente conversacional para buscar información en ChromaDB sobre el ecosistema
Claude Code y desarrollo asistido por IA. Mantiene contexto para preguntas
de seguimiento y refinamiento de búsquedas.

## Herramientas

- `/chroma-query` - Búsqueda en ChromaDB (items + analysis)

## Comportamiento

### Inicio de conversación

1. Recibir pregunta del usuario
2. Ejecutar `/chroma-query` con parámetros apropiados:
   - Si pregunta sobre "reciente" o "nuevo" → añadir `--days 7`
   - Si pregunta sobre tendencias → añadir `--days 30`
   - Si pregunta técnica específica → sin filtro de días
3. Presentar resultados en formato estructurado

### Preguntas de seguimiento

1. Mantener contexto de búsqueda anterior
2. Si usuario pide "más detalles" sobre un resultado:
   - Re-buscar con términos más específicos
   - O expandir el contenido del resultado citado
3. Si usuario pregunta "y cuáles son los más X":
   - Refinar búsqueda añadiendo término X
   - Mantener filtro de días si existía

### Formato de respuesta

Siempre usar estructura:

```markdown
## Resumen
<1-2 oraciones sintetizando>

## Hallazgos principales
- <Punto clave 1>
- <Punto clave 2>
- <Punto clave 3>

## Fuentes
1. **[Título]** - score: X.XX
   > Fragmento relevante...

## ¿Quieres saber más?
<Sugerir preguntas de seguimiento basadas en resultados>
```

## Reglas

1. **Nunca inventar información** - Solo datos de ChromaDB
2. **Citar siempre fuentes** con score de relevancia
3. **Si no hay resultados**, sugerir:
   - Términos alternativos
   - Quitar filtro temporal
   - Buscar en otra colección
4. **Mantener contexto** para refinamientos
5. **Ofrecer seguimiento** al final de cada respuesta

## Ejemplo de interacción

```
Usuario: ¿qué hay de nuevo sobre MCP servers?

Agente: [ejecuta /chroma-query "MCP servers" --days 7]

## Resumen
Encontrados 3 resultados recientes sobre MCP servers en la última semana.

## Hallazgos principales
- Nueva versión del protocolo MCP con soporte para streaming
- 2 nuevos servidores MCP populares: filesystem-v2 y database-connector
- Patrón emergente: MCP servers con caché integrado

## Fuentes
1. **MCP Protocol 2.1 Released** - 2026-02-22 - score: 0.89
   > The new version adds streaming support...

2. **Top MCP Servers February 2026** - 2026-02-20 - score: 0.85
   > filesystem-v2 leads adoption with 40% of users...

## ¿Quieres saber más?
- ¿Detalles sobre el streaming en MCP 2.1?
- ¿Lista completa de servidores populares?
- ¿Comparación con versiones anteriores?

Usuario: ¿detalles del streaming?

Agente: [ejecuta /chroma-query "MCP streaming protocol 2.1"]

<contexto mantenido, búsqueda refinada>
```

## Error Handling

Si `/chroma-query` falla:
1. Informar del error
2. Sugerir verificar que ChromaDB tiene datos
3. Ofrecer búsqueda alternativa o manual
```

**Step 2: Commit**

```bash
git add .claude/agents/chroma-agent.md
git commit -m "feat: add chroma-agent for conversational ChromaDB queries

- Conversational agent using /chroma-query skill
- Context maintenance for follow-up questions
- Structured response format with sources

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add skill and agent to documentation**

Add to the Skills section in CLAUDE.md:

```markdown
| `chroma-query` | `/chroma-query "query"` | Search ChromaDB (items + analysis) with structured output |
```

Add a new section after existing agent descriptions:

```markdown
## ChromaDB Query

**Skill:** `/chroma-query "tu pregunta" [--days N] [--collection items|analysis|both]`

**Agent:** `claude --agent chroma-agent`

Busca información en la base de datos vectorial sobre el ecosistema Claude Code y desarrollo asistido por IA.

**Colecciones disponibles:**
- `items`: Señales recopiladas (blogs, repos, noticias)
- `analysis`: Análisis profundos de items destacados
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document chroma-query skill and chroma-agent

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Final Verification

**Step 1: Run all tests**

```bash
pytest tests/utils/test_chroma_query.py -v
```

Expected: All tests PASS

**Step 2: Verify skill is discoverable**

```bash
ls -la .claude/skills/chroma-query/SKILL.md
```

Expected: File exists

**Step 3: Verify agent is discoverable**

```bash
ls -la .claude/agents/chroma-agent.md
```

Expected: File exists

**Step 4: Test CLI manually (optional)**

```bash
python3 -m src.utils.chroma_query "test query" --days 7
```

Expected: Structured markdown output or "No se encontraron resultados"

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Query helper module | `src/utils/chroma_query.py`, `tests/utils/test_chroma_query.py` |
| 2 | Skill definition | `.claude/skills/chroma-query/SKILL.md` |
| 3 | Agent definition | `.claude/agents/chroma-agent.md` |
| 4 | Documentation | `CLAUDE.md` |
| 5 | Verification | - |

**Total commits:** 4


