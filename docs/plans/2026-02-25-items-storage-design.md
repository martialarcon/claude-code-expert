# Items Storage in ChromaDB - Design Document

**Date:** 2026-02-25
**Status:** Approved

---

## Problem

La colección `items` de ChromaDB está vacía. El analyzer solo guarda análisis, no los items originales. El skill `/chroma-query` no puede buscar en items.

## Solution

Modificar `_store_analysis()` en `src/processors/analyzer.py` para guardar items con calidad condicional.

## Design Decisions

| Aspecto | Decisión |
|---------|----------|
| Ubicación | `_store_analysis()` en analyzer.py |
| Criterio calidad | `confidence >= 0.8` |
| Alta calidad | contenido completo + metadata rica |
| Baja calidad | título + resumen (500 chars) |
| Metadata calidad | campo `"quality": "high" \| "low"` |

## Implementation

```python
def _store_analysis(self, item: CollectedItem, result: AnalysisResult) -> None:
    """Store item and analysis in vector store."""

    # 1. Guardar ITEM con calidad condicional
    is_high_quality = result.confidence >= 0.8

    if is_high_quality:
        # Noticia importante: contenido completo + metadata rica
        item_content = f"{item.title}\n{item.content}"
        item_metadata = {
            "title": item.title,
            "source_type": item.source_type.value,
            "source_url": item.source_url,
            "date": item.published_at.isoformat() if item.published_at else None,
            "author": item.author,
            "signal_score": item.signal_score,
            "quality": "high",
        }
    else:
        # Noticia menos importante: solo título y resumen
        item_content = f"{item.title}\n{item.summary or item.content[:500]}"
        item_metadata = {
            "title": item.title,
            "source_type": item.source_type.value,
            "source_url": item.source_url,
            "quality": "low",
        }

    self.vector_store.add(
        collection="items",
        documents=[item_content],
        ids=[item.id],
        metadatas=[item_metadata],
    )

    # 2. Guardar ANÁLISIS (existente)
    analysis_text = f"{result.summary}\n" + "\n".join(result.key_insights)
    self.vector_store.add(
        collection="analysis",
        documents=[analysis_text],
        ids=[f"analysis_{item.id}"],
        metadatas=[{...}],
    )
```

## Files to Modify

- `src/processors/analyzer.py` - Añadir guardado de items en `_store_analysis()`

## Testing

- Verificar que items se guardan en colección `items`
- Verificar calidad condicional funciona correctamente
- Verificar que `/chroma-query` puede buscar en items
