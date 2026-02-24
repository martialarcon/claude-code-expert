# ChromaDB Query Skill + Agent - Design Document

**Date:** 2026-02-24
**Status:** Approved
**Author:** Claude Code (brainstorming session)

---

## Overview

A two-component system for querying ChromaDB interactively from Claude Code:
- **Skill `/chroma-query`**: Quick access, Python code embedded
- **Agent `chroma-agent`**: Conversational, uses skill underneath

---

## Requirements

| Requirement | Decision |
|-------------|----------|
| Use case | Interactive search (user asks, agent queries ChromaDB) |
| Query types | Mixed: technical + temporal trends |
| Output format | Structured: resumen, fuentes, detalles |
| Collections | items + analysis (not synthesis) |
| Invocation | Skill for quick access + Agent for conversations |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Usuario                              │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────▼─────────┐
        │  /chroma-query    │  ← Skill (acceso rápido)
        │  "tu pregunta"    │
        └─────────┬─────────┘
                  │
        ┌─────────▼─────────┐
        │  chroma-query.md  │  ← Skill file con código Python
        │  (skills/)        │
        └─────────┬─────────┘
                  │
        ┌─────────▼─────────┐
        │  VectorStore      │  ← Código existente
        │  (items, analysis)│
        └───────────────────┘

        ┌───────────────────────────────────────────────────┐
        │  claude --agent chroma-agent                      │  ← Agente dedicado
        │  (usa el skill por debajo + orquesta conversación)│
        └───────────────────────────────────────────────────┘
```

---

## Components

### 1. Skill `/chroma-query`

**File:** `.claude/skills/chroma-query.md`

**Usage:**
```
/chroma-query "<pregunta>" [--days 7] [--collection items|analysis|both]
```

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `<pregunta>` | required | Search query |
| `--days` | none | Filter results by last N days |
| `--collection` | both | Which collection to search |

**Output format:**
```markdown
## Resumen
<1-2 frases sintetizando los hallazgos principales>

## Fuentes (N resultados)
1. **[Título]** - fecha - score: X.XX
   > Fragmento relevante...

2. **[Título]** - fecha - score: X.XX
   > Fragmento relevante...

## Detalles
<Puntos clave expandidos, patrones detectados, conexiones entre fuentes>
```

**Implementation (pseudocode):**
```python
from src.storage.vector_store import get_vector_store

vs = get_vector_store()

# Search both collections
items_results = vs.search(query, collection="items", n_results=5)
analysis_results = vs.search(query, collection="analysis", n_results=3)

# Filter by date if --days specified
if days:
    results = filter_by_date(results, days)

# Format structured output
return format_structured(results)
```

---

### 2. Agent `chroma-agent`

**File:** `.claude/agents/chroma-agent.md`

**Invocation:**
```bash
claude --agent chroma-agent
```

**Behavior:**
- Conversational agent using `/chroma-query` as primary tool
- Maintains context for follow-up questions
- Can refine searches based on previous results

**Example interaction:**
```
Usuario: ¿qué hay de nuevo sobre MCP servers?
Agente: [ejecuta /chroma-query "MCP servers" --days 7]
        → Retorna resumen estructurado

Usuario: ¿y cuáles son los más populares?
Agente: [refina búsqueda anterior con "popular" o "adoption"]
        → Retorna análisis de popularidad
```

**Comparison with direct skill:**

| Skill `/chroma-query` | Agent `chroma-agent` |
|-----------------------|----------------------|
| Single query | Multi-turn conversation |
| No context memory | Remembers previous searches |
| Immediate output | Can refine and deepen |

---

## File Structure

```
.claude/
├── skills/
│   └── chroma-query.md          # Skill con código Python embebido
│
└── agents/
    └── chroma-agent.md          # Agente que invoca el skill

scripts/
└── (sin cambios)                # No necesitamos scripts nuevos

src/storage/
└── vector_store.py              # Ya existe, lo reutilizamos
```

---

## Dependencies

**No new dependencies required:**
- Reuses existing `VectorStore` class
- Uses already installed `chromadb`
- No MCP server needed
- No additional scripts

---

## Agent Instructions (Draft)

```markdown
# chroma-agent

Eres un asistente de búsqueda especializado en el ecosistema Claude Code.

## Herramientas
- Usa /chroma-query para búsquedas en la base de datos vectorial

## Comportamiento
1. Siempre usa el skill para búsquedas (no inventes información)
2. Si la query es ambigua, pide clarificación
3. Para tendencias temporales, sugiere usar --days
4. Cita siempre las fuentes con score de relevancia
5. Mantiene contexto de la conversación para refinamientos

## Formato de respuesta
- Resumen (1-2 frases)
- Fuentes con scores
- Detalles y conexiones
```

---

## Next Steps

1. Create skill file `.claude/skills/chroma-query.md`
2. Create agent file `.claude/agents/chroma-agent.md`
3. Test skill with sample queries
4. Test agent conversation flow
5. Document usage in CLAUDE.md

---

## Success Criteria

- [ ] Skill returns structured results from ChromaDB
- [ ] Date filtering works correctly
- [ ] Agent maintains conversation context
- [ ] Output format is consistent
- [ ] No new external dependencies
