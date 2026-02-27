# Diseño: Fix Metadata Faltante en Reportes Email

**Fecha:** 2026-02-27
**Estado:** Aprobado
**Autor:** Claude + Usuario

---

## Resumen

Corregir el problema de emails con títulos "Unknown", fuentes desconocidas, texto truncado y links faltantes. La solución enriquece los metadatos almacenados en la colección `analysis` de ChromaDB.

---

## Diagnóstico del Problema

| Campo | Email Reporter Espera | Almacenado en `analysis` |
|-------|----------------------|--------------------------|
| `title` | `meta.get("title", "Unknown")` | ❌ No almacenado |
| `source` | `meta.get("source", "unknown")` | ❌ Solo `source_type` |
| `url` | `meta.get("url")` | ❌ No almacenado |
| `summary` | `meta.get("summary", doc[:300])` | ❌ No en metadata, fallback truncado |
| `signal_score` | `meta.get("signal_score", 5)` | ❌ No almacenado |

**Causa raíz:** El analyzer (`analyzer.py:237-243`) solo almacena metadatos mínimos en `analysis`, mientras que `title`, `source_url` y otros campos se guardan en `items`. El email reporter solo consulta `analysis`.

---

## Solución

**Opción elegida:** Enriquecer metadatos en la colección `analysis` durante el almacenamiento.

### Cambios en `src/processors/analyzer.py`

**Ubicación:** Método `_store_analysis()`, líneas 230-243

**Antes:**
```python
self.vector_store.add(
    collection="analysis",
    documents=[analysis_text],
    ids=[f"analysis_{item.id}"],
    metadatas=[{
        "item_id": item.id,
        "source_type": item.source_type.value,
        "actionability": result.actionability,
        "confidence": result.confidence,
    }],
)
```

**Después:**
```python
# Build analysis metadata with all fields needed for email reporter
analysis_metadata = {
    "item_id": item.id,
    "title": item.title,
    "source": item.source_type.value,
    "url": item.source_url,
    "summary": result.summary,
    "actionability": result.actionability,
    "confidence": result.confidence,
}
if item.signal_score is not None:
    analysis_metadata["signal_score"] = str(item.signal_score)

self.vector_store.add(
    collection="analysis",
    documents=[analysis_text],
    ids=[f"analysis_{item.id}"],
    metadatas=[analysis_metadata],
)
```

### Cambios en `src/notifications/email_reporter.py`

**Ubicación:** Método `_parse_analysis_item()`, líneas 164-176

**Cambio menor:** Convertir `signal_score` a int (ChromaDB almacena strings):

```python
def _parse_analysis_item(self, doc: str, meta: dict[str, Any]) -> AnalyzedItem:
    """Parse analysis document into AnalyzedItem."""
    return AnalyzedItem(
        title=meta.get("title", "Unknown"),
        source=meta.get("source", "unknown"),
        signal_score=int(meta.get("signal_score", 5)),  # Convert to int
        summary=meta.get("summary", doc[:300]),
        key_insights=meta.get("key_insights", []),
        technical_details=meta.get("technical_details"),
        relevance_to_claude=meta.get("relevance_to_claude"),
        actionability=meta.get("actionability"),
        url=meta.get("url"),
    )
```

---

## Flujo de Datos Post-Fix

```
Analyzer._store_analysis()
    │
    ▼
┌─────────────────────────────────────────────┐
│ analysis collection                          │
├─────────────────────────────────────────────┤
│ document: "{summary}\n{key_insights}"       │
│ metadata:                                    │
│   - item_id                                  │
│   - title          ← NEW                     │
│   - source         ← NEW (was source_type)   │
│   - url            ← NEW                     │
│   - summary        ← NEW                     │
│   - signal_score   ← NEW                     │
│   - actionability                            │
│   - confidence                               │
└─────────────────────────────────────────────┘
    │
    ▼
EmailReporter._parse_analysis_item()
    │
    ▼
┌─────────────────────────────────────────────┐
│ AnalyzedItem dataclass                       │
│   - title: ✓ "Título real"                  │
│   - source: ✓ "reddit" / "hackernews"       │
│   - url: ✓ "https://..."                    │
│   - summary: ✓ Texto completo               │
│   - signal_score: ✓ 7                       │
└─────────────────────────────────────────────┘
    │
    ▼
Template daily_report.html
    │
    ▼
Email con datos completos ✓
```

---

## Migración de Datos Existentes

Los análisis existentes en ChromaDB mantienen la estructura antigua. Opciones:

| Opción | Descripción | Esfuerzo |
|--------|-------------|----------|
| **A. Gradual** | Solo nuevos análisis tienen metadata completa | Bajo |
| **B. Re-análisis** | Ejecutar pipeline de análisis sobre items existentes | Medio |
| **C. Script migración** | Copiar metadata de `items` a `analysis` | Medio |

**Recomendación:** Opción A (gradual). El problema se resuelve automáticamente para nuevo contenido.

---

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `src/processors/analyzer.py` | Enriquecer `analysis_metadata` en `_store_analysis()` |
| `src/notifications/email_reporter.py` | Convertir `signal_score` a int en `_parse_analysis_item()` |

---

## Testing

1. Ejecutar pipeline de análisis sobre un item nuevo
2. Verificar metadata en ChromaDB con todos los campos
3. Generar email preview y verificar:
   - Título correcto (no "Unknown")
   - Fuente correcta
   - Link presente y funcional
   - Texto completo (no truncado)
   - Signal score visible

```bash
# Test manual
python main.py --mode daily --email --preview
```

---

## Impacto

- **Riesgo:** Bajo - solo añade campos, no elimina ni modifica existentes
- **Backwards compatible:** Sí - email reporter tiene fallbacks
- **Performance:** Sin impacto - mismo número de operaciones ChromaDB
