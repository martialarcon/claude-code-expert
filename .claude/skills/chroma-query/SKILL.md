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
