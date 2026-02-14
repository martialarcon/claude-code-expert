# AI Architect - Documento de Diseño

**Fecha:** 2026-02-14
**Estado:** Aprobado para implementación

---

## 1. Resumen

AI Architect es un sistema automatizado que diariamente recopila, analiza y sintetiza conocimiento sobre desarrollo de software con Claude Code desde múltiples fuentes de alta reputación. El resultado es una base de conocimiento estructurada en Markdown y actualizada diariamente.

### Objetivos
- Mantenerse actualizado sobre Claude Code, LLMs para desarrollo, MCP servers, y técnicas de AI-assisted coding
- Recopilar solo fuentes de alta reputación y calidad
- Generar análisis profundos con insights prácticos aplicables
- Detectar tendencias y patrones a través del tiempo

---

## 2. Arquitectura General

```
ai-architect/
├── Dockerfile
├── docker-compose.yml
├── main.py
├── config.yaml
├── requirements.txt
├── .env
├── src/
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── arxiv.py
│   │   ├── github.py
│   │   ├── youtube.py
│   │   ├── blogs.py
│   │   ├── reddit.py
│   │   └── docs.py
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── claude_client.py
│   │   ├── analyzer.py
│   │   └── synthesizer.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── vector_store.py
│   │   └── markdown_gen.py
│   └── utils/
│       ├── __init__.py
│       ├── notifier.py
│       ├── config.py
│       └── logger.py
└── output/
    ├── daily/
    ├── topics/
    ├── master.md
    └── index.md
```

### Contenedores Docker

| Servicio | Imagen | Propósito |
|----------|--------|-----------|
| `app` | Custom (Python 3.11 + Claude CLI) | Orquestador principal |
| `chromadb` | `chromadb/chroma:latest` | Base de datos vectorial |

### Flujo de Datos

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Collectors │────▶│  Processors │────▶│   Storage   │────▶│   Output    │
│  (6 fuentes)│     │   (Claude)  │     │  (ChromaDB) │     │  (Markdown) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                  │
                                                                  ▼
                                                           ┌─────────────┐
                                                           │  Notifier   │
                                                           │  (ntfy.sh)  │
                                                           └─────────────┘
```

---

## 3. Fuentes de Información

### 3.1 ArXiv (Papers Académicos)

**Configuración:**
- Categorías: `cs.CL`, `cs.SE`, `cs.AI`
- Filtro: Papers con >10 citas o de autores de alto impacto
- Límite: 20 resultados/día

**Método:** API HTTP vía librería `arxiv`

### 3.2 GitHub (Repositorios)

**Configuración:**
- Topics: `claude`, `claude-code`, `mcp`, `anthropic`, `llm-agent`
- Filtro: >100 stars, actualizado en últimas 24h
- Orden: por fecha de actualización
- Límite: 30 resultados/día

**Método:** GitHub REST API

### 3.3 YouTube (Videos)

**Configuración:**
- Canales predefinidos de reputación (Anthropic oficial, canales técnicos)
- Máximo 5 videos por canal/día

**Método:** YouTube Data API v3 (con transcripción vía `youtube-transcript-api`)

### 3.4 Blogs y Artículos

**Configuración:**
- RSS feeds de Dev.to, Medium, blog.anthropic.com
- Filtro por tags relevantes
- Máximo 10 artículos por feed/día

**Método:** RSS parsing con `feedparser`, web scraping cuando sea necesario

### 3.5 Reddit y Hacker News

**Configuración:**
- Subreddits: `LocalLLaMA`, `ClaudeAI`, `programming`
- Hacker News: stories con >50 points
- Límite: 15 resultados/día

**Método:** Reddit API (PRAW), Hacker News API pública

### 3.6 Documentación Oficial

**Configuración:**
- Fuentes: docs.anthropic.com, github.com/anthropics/claude-code
- Detectar cambios vs versión anterior

**Método:** HTTP fetch + diff, almacenamiento de snapshots

---

## 4. Procesamiento con IA

### 4.1 Cliente Claude

El sistema usa el CLI de Claude Code instalado en el contenedor, montando la sesión del host:

```yaml
volumes:
  - ~/.claude:/root/.claude:ro
```

**Implementación:**
```python
# src/processors/claude_client.py
import subprocess

def ask_claude(prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", model],
        capture_output=True,
        text=True,
        timeout=300
    )
    if result.returncode != 0:
        raise Exception(f"Claude CLI error: {result.stderr}")
    return result.stdout
```

### 4.2 Análisis Individual (Analyzer)

**Modelo:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)

**Prompt de análisis:**
```
Analiza este recurso sobre Claude Code/desarrollo con IA:

Título: {title}
Fuente: {source}
Contenido: {content}

Proporciona:
1. **Resumen** (2-3 oraciones)
2. **Insights clave** (3-5 puntos principales)
3. **Código relevante** (si aplica, extrae snippets o describe qué código podría inspirar)
4. **Aplicabilidad práctica** (cómo usar esto en desarrollo real con Claude Code)
5. **Relevancia** (1-10, donde 10 = esencial para usar Claude Code eficientemente)
6. **Tags** (3-5 categorías para clasificar)
```

**Output estructurado:**
```python
@dataclass
class Analysis:
    summary: str
    insights: list[str]
    code_snippets: list[str]
    applicability: str
    relevance_score: int  # 1-10
    tags: list[str]
    full_response: str
```

### 4.3 Síntesis Diaria (Synthesizer)

**Modelo:** Claude Opus 4.6 (`claude-opus-4-6-20250528`)

**Prompt de síntesis:**
```
Tienes {count} recursos analizados hoy sobre Claude Code y desarrollo con IA.
Busca EN LA BASE DE DATOS VECTORIAL contenido relacionado de días anteriores.

Recursos de hoy:
{daily_summaries}

Contenido relacionado de días anteriores:
{related_content}

Genera:
1. **Tendencias detectadas** (patrones entre múltiples fuentes)
2. **Conexiones con días anteriores** (qué temas se repiten, evolucionan)
3. **Highlight del día** (lo más importante, 1-2 items)
4. **Acciones recomendadas** (qué investigar más, qué probar)
5. **Score de relevancia del día** (1-10)
```

---

## 5. Almacenamiento

### 5.1 Vector Store (ChromaDB)

**Propósito:**
- Almacenar embeddings de análisis para búsqueda semántica
- Encontrar contenido relacionado entre días
- Detectar temas recurrentes

**Schema:**
```python
collection.add(
    ids=[item_id],
    documents=[analysis.full_text],  # Embedding automático
    metadatas=[{
        "title": item.title,
        "source": item.source,
        "url": item.url,
        "date": item.published.isoformat(),
        "relevance": analysis.relevance_score,
        "tags": ",".join(analysis.tags)
    }]
)
```

**Consultas principales:**
- Búsqueda por similitud semántica
- Filtrado por fecha (últimos N días)
- Filtrado por tags/fuentes

### 5.2 Estructura de Archivos Markdown

```
output/
├── daily/
│   ├── 2026-02-14.md
│   ├── 2026-02-13.md
│   └── ...
├── topics/
│   ├── mcp-servers.md
│   ├── code-generation.md
│   ├── prompt-engineering.md
│   ├── debugging.md
│   ├── testing.md
│   └── ...                    # Se crean dinámicamente según tags
├── master.md                  # Archivo acumulativo
└── index.md                   # Índice general
```

### 5.3 Formato de Archivos

**Digest diario (`daily/YYYY-MM-DD.md`):**

```markdown
# AI Architect Digest - YYYY-MM-DD

## Síntesis del Día
> **Relevancia:** X/10
> **Fuentes:** N items de M fuentes
> **Errores:** [lista si hay]

### Tendencias Detectadas
- [Auto-generado]

### Highlight del Día
- **[Título]** - Fuente | Relevancia: X/10
  - [Por qué importa]

### Acciones Recomendadas
- [ ] [Acción 1]
- [ ] [Acción 2]

---

## Items del Día

### [Fuente 1] (N)

#### [Título](url)
- **Relevancia:** X/10 | **Tags:** tag1, tag2
- **Resumen:** ...
- **Insights:**
  - Insight 1
  - Insight 2
- **Código relevante:**
  ```python
  [snippet si aplica]
  ```
- **Aplicabilidad:** ...

---

## Errores/Fuentes No Disponibles
- ❌ [Fuente]: [Error]
```

**Índice temático (`topics/[topic].md`):**

```markdown
# [Topic]

> Última actualización: YYYY-MM-DD

## Recientes

### YYYY-MM-DD | [Título](url)
Fuente: X | Relevancia: X/10
> Resumen breve...

---

## Estadísticas
- Total items: N
- Fuentes: GitHub (X), Blogs (Y), ...
```

**Archivo master (`master.md`):**

```markdown
# AI Architect - Base de Conocimiento

> Iniciado: YYYY-MM-DD | Última actualización: YYYY-MM-DD
> Total items: N

## Índice de Temas
- [[mcp-servers]] (N items)
- [[code-generation]] (N items)
...

## Últimos 7 Días
- YYYY-MM-DD: [Link al digest] - Relevancia X/10
...

## Highlights Históricos
- [Items con relevancia 10/10]
```

---

## 6. Orquestación

### 6.1 Flujo Principal

```python
# main.py (pseudocódigo)
async def run_daily():
    start_time = datetime.now()
    since = datetime.now() - timedelta(days=1)

    # 1. Recolectar
    collectors = [ArxivCollector(), GitHubCollector(), ...]
    for collector in collectors:
        try:
            items.extend(await collector.collect(since))
        except Exception:
            errors.append((collector.name, error))

    # 2. Analizar
    for item in items:
        analysis = await analyzer.analyze(item)
        vector_store.store(analysis, item)
        analyses.append(analysis)

    # 3. Sintetizar
    synthesis = await synthesizer.synthesize(analyses, vector_store)

    # 4. Generar Markdowns
    markdown_gen.generate_daily(analyses, synthesis, errors, start_time)
    markdown_gen.update_topics(analyses)
    markdown_gen.update_master(analyses, synthesis)
    markdown_gen.update_index()

    # 5. Notificar
    notifier.send(summary)
```

### 6.2 Manejo de Errores

**Estrategia:** Continúa y reporta

- Si un collector falla: se registra el error, continúa con los demás
- Si el análisis de un item falla: se salta ese item, continúa con los demás
- Si la síntesis falla: se generan los markdowns sin síntesis, se notifica el error
- El reporte final incluye todos los errores encontrados

### 6.3 Scheduler

**Cron del host:**

```bash
# crontab -e
0 0 * * * cd /home/jetson/developer/projects/ai-architect && docker compose run --rm app >> /var/log/ai-architect.log 2>&1
```

**Ejecución:** Diario a medianoche (00:00)

---

## 7. Notificaciones

**Método:** ntfy.sh (servicio gratuito)

**Configuración:**
```yaml
notification:
  method: "ntfy"
  topic: "ai-architect"
```

**Mensaje enviado:**
```
✅ AI Architect completado
N items analizados | Relevancia del día: X/10

⚠️ Fallos: [lista si hay]
```

**Endpoint:** `https://ntfy.sh/ai-architect`

---

## 8. Configuración

### 8.1 config.yaml

```yaml
schedule:
  timezone: "Europe/Madrid"

notification:
  method: "ntfy"
  topic: "ai-architect"

arxiv:
  categories: ["cs.CL", "cs.SE", "cs.AI"]
  min_citations: 10
  max_results: 20

github:
  topics: ["claude", "claude-code", "mcp", "anthropic", "llm-agent"]
  min_stars: 100
  max_results: 30
  sort: "updated"

youtube:
  channels:
    - "UCxxxxx"  # Anthropic oficial
    - "UCxxxxx"  # Otros canales técnicos
  max_per_channel: 5

blogs:
  feeds:
    - url: "https://blog.anthropic.com/rss"
      reputation: high
    - url: "https://dev.to/tag/claude/rss"
      reputation: medium
    - url: "https://medium.com/feed/tag/claude-ai"
      reputation: medium
  max_per_feed: 10

reddit:
  subreddits: ["LocalLLaMA", "ClaudeAI", "programming"]
  min_score: 50
  max_results: 15

hackernews:
  min_points: 50
  max_results: 10

docs:
  sources:
    - "https://docs.anthropic.com"
    - "https://github.com/anthropics/claude-code"

models:
  analysis: "claude-sonnet-4-20250514"
  synthesis: "claude-opus-4-6-20250528"
```

### 8.2 .env

```bash
# APIs requeridas
GITHUB_TOKEN=ghp_xxx
YOUTUBE_API_KEY=AIzaxxx
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx

# Notificación
NTFY_TOPIC=ai-architect
```

---

## 9. Docker

### 9.1 Dockerfile

```dockerfile
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instalar Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | sh

WORKDIR /app

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY src/ ./src/
COPY main.py .

CMD ["python", "main.py"]
```

### 9.2 docker-compose.yml

```yaml
services:
  app:
    build: .
    container_name: ai-architect
    volumes:
      - ~/.claude:/root/.claude:ro
      - ./output:/app/output
      - ./config.yaml:/app/config.yaml:ro
      - ./.env:/app/.env:ro
    environment:
      - TZ=Europe/Madrid
    depends_on:
      - chromadb

  chromadb:
    image: chromadb/chroma:latest
    container_name: ai-architect-chroma
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma
    restart: unless-stopped

volumes:
  chroma_data:
```

### 9.3 requirements.txt

```
arxiv>=2.0.0
feedparser>=6.0.0
google-api-python-client>=2.0.0
youtube-transcript-api>=0.6.0
praw>=7.0.0
httpx>=0.25.0
chromadb>=0.4.0
pyyaml>=6.0
python-dateutil>=2.8.0
beautifulsoup4>=4.12.0
```

---

## 10. APIs Externas

| API | Uso | Costo | Auth |
|-----|-----|-------|------|
| Claude Code CLI | Análisis y síntesis | Suscripción existente | Session mount |
| GitHub API | Buscar repos | Gratis 5000 req/hora | Token |
| ArXiv API | Papers académicos | Gratis | Ninguna |
| YouTube Data API | Videos | Gratis 10K quota/día | API Key |
| Reddit API | Posts | Gratis | OAuth |
| Hacker News API | Stories | Gratis | Ninguna |
| ntfy.sh | Notificaciones | Gratis | Ninguna |

---

## 11. Próximos Pasos

1. Crear estructura de directorios
2. Implementar collectors (empezando por ArXiv y GitHub)
3. Implementar claude_client y analyzer
4. Configurar ChromaDB
5. Implementar synthesizer
6. Implementar markdown_gen
7. Configurar Docker y docker-compose
8. Configurar cron del host
9. Probar ejecución completa
10. Ajustar prompts y filtros según resultados

---

## 12. Consideraciones Futuras

- **Web UI:** Interfaz para navegar el conocimiento acumulado
- **API de consulta:** Endpoint para hacer preguntas a la base de conocimiento
- **Export:** Generar PDFs o ebooks con el contenido acumulado
- **Métricas:** Dashboard con estadísticas de fuentes, relevancia, tendencias
