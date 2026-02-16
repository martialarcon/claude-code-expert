# AI Architect v2 — Planificación Técnica Completa

**Versión:** 2.0  
**Fecha:** 2026-02-15  
**Estado:** En desarrollo  
**Hardware objetivo:** NVIDIA Jetson Orin Nano (ARM64, 8GB RAM)

---

## Índice

1. [Resumen Ejecutivo y Visión](#1-resumen-ejecutivo-y-visión)
2. [Arquitectura General del Sistema](#2-arquitectura-general-del-sistema)
3. [Modelo de Inteligencia Multicapa](#3-modelo-de-inteligencia-multicapa)
4. [Arquitectura de Fuentes de Información](#4-arquitectura-de-fuentes-de-información)
5. [Pipeline de Recolección](#5-pipeline-de-recolección)
6. [Pipeline de Procesamiento](#6-pipeline-de-procesamiento)
7. [Pipeline de Análisis con Claude](#7-pipeline-de-análisis-con-claude)
8. [Pipeline de Síntesis](#8-pipeline-de-síntesis)
9. [Almacenamiento](#9-almacenamiento)
10. [Formato de Outputs](#10-formato-de-outputs)
11. [Infraestructura y Despliegue](#11-infraestructura-y-despliegue)
12. [Fases de Implementación](#12-fases-de-implementación)
13. [Monitorización y Operaciones](#13-monitorización-y-operaciones)

---

## 1. Resumen Ejecutivo y Visión

### 1.1 Qué es AI Architect v2

AI Architect v2 es un radar de inteligencia técnica automatizado, orientado al ecosistema de Claude Code y AI-assisted development. Recopila, analiza y sintetiza información desde múltiples fuentes de señal primaria, comportamiento y producción real, generando una base de conocimiento estructurada en Markdown y almacenada en ChromaDB.

### 1.2 Evolución desde v1

El v1 es un sistema reactivo que documenta lo que ya pasó. Sus 6 fuentes originales (ArXiv, GitHub >100★, blogs/RSS, Reddit/HN, YouTube, docs oficiales) capturan conocimiento semi-público con días o semanas de retraso. Los filtros de popularidad (>10 citas en ArXiv, >100 estrellas en GitHub, >50 puntos en HN) garantizan que el sistema llegue tarde a todo lo emergente.

El v2 corrige esto con tres cambios fundamentales:

**De reactivo a predictivo.** El sistema pasa de responder "qué se publicó" a responder qué está cambiando, qué está emergiendo, qué está consolidándose, qué está fallando, y qué ventaja competitiva existe o desaparece.

**De filtro por popularidad a filtro por relevancia.** Los umbrales de v1 se reemplazan por detección de velocidad de crecimiento, novedad semántica, y profundidad técnica. Un repo con 30 estrellas ganadas en 3 días es más señal que uno con 500 estrellas estáticas.

**De fuentes editoriales a fuentes primarias.** Se añaden fuentes de señal primaria (podcasts, newsletters de alta señal), señal de comportamiento (descargas PyPI/npm, issues de repos críticos, preguntas StackOverflow), y señal profesional (job postings, conferencias, engineering blogs con postmortems).

### 1.3 Decisiones de diseño clave

| Decisión | Valor | Justificación |
|----------|-------|---------------|
| Modelo de análisis | `claude-sonnet-4-20250514` | Balance coste/calidad para análisis individual |
| Modelo de síntesis | `claude-opus-4-6` | Máxima capacidad para síntesis estratégica y detección de patrones |
| Vector store | ChromaDB | Ligero, embeddable, suficiente para el volumen esperado |
| Hardware | Jetson Orin Nano ARM64 8GB | Hardware disponible del usuario |
| Ejecución | Secuencial, no paralela | Restricción de 8GB RAM: no es viable correr ChromaDB + Claude CLI + whisper simultáneamente |
| Twitter/X | Excluido | Nitter muerto, snscrape roto, twint abandonado. No hay vía estable de acceso sin API Enterprise |
| Notificaciones | ntfy.sh | Gratuito, sin dependencias, push nativo a móvil |
| Output | Markdown + ChromaDB | Portabilidad máxima, compatible con cualquier herramienta |

### 1.4 Alcance del sistema

**Dentro del alcance:**
- Recolección automatizada diaria desde ~15 fuentes activas
- Análisis individual de cada item con Claude Sonnet
- Síntesis estratégica diaria con Claude Opus, semanal y mensual
- Detección de novedad, impacto, madurez y posición competitiva
- Almacenamiento vectorial para búsqueda semántica histórica
- Generación de reportes Markdown estructurados
- Notificaciones push con resumen del ciclo

**Fuera del alcance (v2):**
- Web UI para navegar el conocimiento
- API de consulta externa
- Procesamiento en tiempo real (el sistema es batch diario)
- Twitter/X como fuente de datos

---

## 2. Arquitectura General del Sistema

### 2.1 Estructura de directorios

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
│   │   ├── base.py              # Clase base para todos los collectors
│   │   ├── arxiv.py
│   │   ├── github_repos.py      # Repos consolidados (>100★)
│   │   ├── github_emerging.py   # Repos emergentes (<100★, crecimiento rápido)
│   │   ├── github_signals.py    # Issues, PRs, Discussions de repos críticos
│   │   ├── youtube.py
│   │   ├── podcasts.py          # NUEVO: descarga + transcripción
│   │   ├── blogs.py             # RSS feeds (blogs, newsletters)
│   │   ├── engineering_blogs.py # NUEVO: postmortems y arquitectura
│   │   ├── reddit.py
│   │   ├── hackernews.py
│   │   ├── stackoverflow.py     # NUEVO: preguntas y patrones
│   │   ├── packages.py          # NUEVO: PyPI/npm growth tracking
│   │   ├── jobs.py              # NUEVO: job postings técnicos
│   │   ├── conferences.py       # NUEVO: programas y CFPs
│   │   └── docs.py              # Docs oficiales con diff
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── claude_client.py     # Wrapper del CLI de Claude
│   │   ├── signal_ranker.py     # NUEVO: ranking por profundidad/impacto
│   │   ├── novelty_detector.py  # NUEVO: detección de novedad vs histórico
│   │   ├── impact_classifier.py # NUEVO: clasificación por dimensión
│   │   ├── maturity_classifier.py # NUEVO: nivel de madurez
│   │   ├── competitive_mapper.py  # NUEVO: mapeo competitivo
│   │   ├── analyzer.py          # Análisis individual (Claude Sonnet)
│   │   └── synthesizer.py       # Síntesis diaria/semanal/mensual (Claude Opus)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── vector_store.py      # ChromaDB
│   │   └── markdown_gen.py      # Generación de outputs Markdown
│   └── utils/
│       ├── __init__.py
│       ├── notifier.py          # ntfy.sh
│       ├── config.py            # Loader de config.yaml
│       └── logger.py
├── output/
│   ├── daily/                   # Digests diarios
│   ├── weekly/                  # NUEVO: síntesis semanales
│   ├── monthly/                 # NUEVO: reportes mensuales
│   ├── topics/                  # Índices temáticos
│   ├── competitive/             # NUEVO: matrices competitivas
│   ├── master.md
│   └── index.md
└── data/
    ├── snapshots/               # Snapshots de docs para diff
    ├── transcripts/             # NUEVO: transcripciones de podcasts
    └── packages/                # NUEVO: histórico de descargas
```

### 2.2 Contenedores Docker

| Servicio | Imagen | Propósito | Nota ARM64 |
|----------|--------|-----------|------------|
| `app` | Custom (Python 3.11 + Claude CLI) | Orquestador principal | Build multi-arch nativo |
| `chromadb` | Build from source | Base de datos vectorial | La imagen oficial no siempre publica ARM64. Usar Dockerfile con `pip install chromadb` sobre imagen base `python:3.11-slim` para ARM64 |

**Nota sobre ChromaDB en ARM64:** La imagen Docker `chromadb/chroma:latest` no garantiza soporte ARM64 consistente. La solución es construir ChromaDB desde un Dockerfile propio basado en `python:3.11-slim` (que sí es multi-arch), instalando `chromadb` vía pip. Esto funciona de forma estable en Jetson Orin Nano.

### 2.3 Flujo de datos general

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Collectors  │────▶│  Processors │────▶│   Storage   │────▶│   Output    │
│ (15 fuentes) │     │  (6 etapas) │     │  (ChromaDB) │     │  (Markdown) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                  │
                                                                  ▼
                                                           ┌─────────────┐
                                                           │  Notifier   │
                                                           │  (ntfy.sh)  │
                                                           └─────────────┘
```

**Detalle del pipeline de procesamiento:**

```
Item recolectado
  │
  ▼
Signal Ranker ──────── Descarta items de baja señal (threshold configurable)
  │
  ▼
Novelty Detector ───── Evalúa similitud con contenido histórico en ChromaDB
  │
  ▼
Impact Classifier ──── Categoriza por dimensión arquitectónica
  │
  ▼
Maturity Classifier ── Determina nivel de madurez tecnológica
  │
  ▼
Analyzer (Sonnet) ──── Análisis profundo con Claude Sonnet
  │
  ▼
Storage ────────────── Almacena en ChromaDB + genera Markdown parcial
  │
  ▼
Synthesizer (Opus) ─── Síntesis estratégica (diaria/semanal/mensual)
  │
  ▼
Competitive Mapper ─── Actualiza matriz competitiva (semanal)
  │
  ▼
Markdown Generator ─── Genera todos los outputs finales
```

### 2.4 Restricciones de hardware

El Jetson Orin Nano con 8GB de RAM impone restricciones concretas:

**Ejecución secuencial obligatoria.** No se pueden ejecutar simultáneamente ChromaDB + Claude CLI + faster-whisper. El pipeline debe orquestar cada fase en secuencia, liberando memoria entre fases.

**Pipeline de podcasts separado.** La transcripción con faster-whisper (modelo `whisper-small`) requiere ~2GB de RAM. Debe ejecutarse como pre-proceso antes del pipeline principal, almacenando las transcripciones en disco (`data/transcripts/`).

**ChromaDB en modo embedded.** En lugar de ejecutar ChromaDB como contenedor separado, se usa en modo embedded dentro del proceso Python principal. Esto evita el overhead de un segundo contenedor y simplifica la gestión de memoria.

**Orden de ejecución:**
1. Fase 0: Transcripción de podcasts (si hay nuevos episodios) → liberar whisper
2. Fase 1: Recolección de todas las fuentes → almacenar items en disco
3. Fase 2: Procesamiento por lotes → ChromaDB embedded + Claude CLI secuencial
4. Fase 3: Síntesis y generación de outputs
5. Fase 4: Notificación

---

## 3. Modelo de Inteligencia Multicapa

El v2 introduce 5 capas de análisis que transforman datos crudos en inteligencia técnica accionable. Cada capa responde a una pregunta diferente sobre el ecosistema.

### 3.1 Capa 1 — Señal Técnica Profunda

**Pregunta que responde:** ¿Qué conocimiento arquitectónico real está emergiendo?

**Fuentes que la alimentan:**
- Issues avanzadas en repos críticos (`anthropics/claude-code`, MCP servers oficiales)
- Pull Requests estructurales en proyectos populares
- GitHub Discussions técnicas con múltiples respuestas
- Preguntas complejas en StackOverflow
- Repos curados activamente mantenidos

**Resultado esperado:**
- Decisiones arquitectónicas explícitas documentadas en issues/PRs
- Problemas sistémicos que se repiten en múltiples repos
- Patrones emergentes de diseño que aún no tienen nombre formal
- Fricción real de producción (errores, limitaciones, workarounds)

**Ejemplo de señal:** Una issue en `anthropics/claude-code` con 15 comentarios donde múltiples usuarios reportan el mismo problema de context window con herramientas MCP revela un problema sistémico antes de que sea documentado oficialmente.

### 3.2 Capa 2 — Producción y Uso Real

**Pregunta que responde:** ¿Qué está funcionando (o fallando) en sistemas reales en producción?

**Fuentes que la alimentan:**
- Engineering blogs corporativos con postmortems
- Artículos con métricas reales (latencia, coste, throughput)
- Commits de migración pública entre modelos/frameworks
- Job postings técnicos que revelan stacks internos

**Señales clave monitorizadas:**
- Latencia en producción con Claude vs competidores
- Costes reales de operación (no estimaciones teóricas)
- Problemas de escalabilidad documentados
- Migraciones entre modelos (de GPT-4 a Claude, o viceversa) y sus razones
- Patrones de seguridad específicos para agentes LLM

**Ejemplo de señal:** Un post en el blog de ingeniería de Stripe que documenta por qué migraron de GPT-4 a Claude para code review interno, con métricas de precisión y coste.

### 3.3 Capa 3 — Detección Temprana de Tendencias

**Pregunta que responde:** ¿Qué anomalías sugieren tendencias antes de que sean mainstream?

**Mecanismos de detección:**
- Repos nuevos (<14 días) con crecimiento acelerado de estrellas (>100 en <7 días)
- Paquetes nuevos en PyPI/npm con adopción rápida (de 100 a 10.000 descargas semanales en dos semanas)
- Nuevas combinaciones de tags en GitHub que aparecen juntas por primera vez
- Cambios semánticos en documentación oficial (nuevos conceptos, deprecaciones)
- Talks aceptados en conferencias sobre temas que aún no tienen presencia en blogs

**Ejemplo de señal:** Un paquete npm `@anthropic-ai/mcp-toolkit` nuevo que pasa de 200 a 15.000 descargas semanales en 10 días, antes de cualquier blog post o anuncio.

### 3.4 Capa 4 — Inteligencia Competitiva

**Pregunta que responde:** ¿Cómo se compara Claude Code con los ecosistemas alternativos y qué brechas existen?

**Elementos monitorizados:**
- Nuevas features en competidores directos (GitHub Copilot, Cursor, Windsurf, Cline, Aider)
- Benchmarks actualizados y comparativas públicas
- Diferencias arquitectónicas en los approaches de cada ecosistema
- Migraciones públicas documentadas entre herramientas
- Adopción empresarial diferencial (qué herramientas adoptan las empresas y por qué)

**Output:** Matriz competitiva actualizada semanalmente con dimensiones: features, modelo subyacente, extensibilidad (MCP vs plugins propietarios), precio, limitaciones conocidas.

### 3.5 Capa 5 — Modelado Arquitectónico

**Pregunta que responde:** ¿Qué patrones y anti-patrones se están consolidando en AI-assisted development?

**Generación semanal:**
- Patrones arquitectónicos emergentes (ej: "MCP gateway pattern", "agent-in-the-loop CI/CD")
- Anti-patrones documentados (ej: "context window stuffing", "prompt chaining sin validación")
- Topologías recurrentes de sistemas multi-agente
- Combinaciones tecnológicas dominantes (ej: Claude Code + MCP + framework X)
- Cambios de paradigma detectados con evidencia

**Este es el output de mayor valor estratégico.** Mientras las capas 1-4 detectan señales individuales, la capa 5 construye modelos conceptuales que permiten tomar decisiones arquitectónicas informadas.

---

## 4. Arquitectura de Fuentes de Información

### 4.1 Principios de diseño de fuentes

Cinco principios rigen la selección y priorización de fuentes en v2:

**Profundidad > Amplitud.** Es mejor procesar 200 items de alta señal que 2.000 items de señal mixta. El sistema no busca exhaustividad sino que no se pierda nada importante.

**Señal primaria > Señal secundaria.** Una fuente primaria (alguien usando Claude Code en producción reportando un problema) es más valiosa que una fuente secundaria (un blog que resume lo que alguien reportó). El sistema prioriza siempre la fuente más cercana a la experiencia real.

**Comportamiento > Declaración.** Lo que la gente descarga, adopta y pregunta es más informativo que lo que dice que va a hacer. Los datos de npm, las preguntas de StackOverflow, y el crecimiento de repos son señales de comportamiento real.

**Velocidad de señal como dimensión explícita.** Cada fuente tiene un tiempo de latencia inherente. Una observación en un podcast de hoy es diferente de un paper sobre el mismo tema publicado en seis meses. El sistema es consciente de esta latencia para interpretar la señal correctamente.

**Relevancia semántica > Popularidad.** Para un sistema de inteligencia técnica, filtrar por popularidad garantiza llegar tarde. El filtro correcto es la relevancia semántica y la velocidad de crecimiento, no el número absoluto de citas, estrellas o puntos.

### 4.2 Mapa completo de fuentes

#### Fuentes excluidas

| Fuente | Razón de exclusión |
|--------|-------------------|
| Twitter/X | Nitter muerto (instancias públicas caídas, self-hosting inviable). snscrape roto por cambios de API de X. twint abandonado. No hay vía de acceso estable sin API Enterprise ($$$). Se documenta como fuente aspiracional para futuras versiones si el acceso cambia. |

#### Fuentes activas por categoría

**SEÑAL PRIMARIA — Velocidad: horas a días**

| # | Fuente | Método de acceso | Velocidad | Dificultad | Prioridad | Items/día estimados |
|---|--------|-----------------|-----------|------------|-----------|-------------------|
| 1 | Docs oficiales Anthropic | HTTP fetch + diff vs snapshot | Inmediata | Baja | Crítica | 0-5 (cambios) |
| 2 | GitHub Issues/PRs (repos clave) | GitHub REST API | Horas | Baja | Crítica | 10-30 |
| 3 | Simon Willison's blog | RSS (`simonwillison.net`) | Diaria | Baja | Muy alta | 1-5 |
| 4 | Podcasts técnicos (transcripciones) | Descarga RSS + faster-whisper | Días | Media | Alta | 0-3 episodios/semana |

**SEÑAL DE COMPORTAMIENTO — Velocidad: horas a semanal**

| # | Fuente | Método de acceso | Velocidad | Dificultad | Prioridad | Items/día estimados |
|---|--------|-----------------|-----------|------------|-----------|-------------------|
| 5 | GitHub repos emergentes (<100★) | GitHub REST API (growth tracking) | Diaria | Baja | Alta | 5-15 |
| 6 | GitHub repos consolidados (>100★) | GitHub REST API | Diaria | Baja | Media | 10-20 |
| 7 | Paquetes PyPI/npm (growth) | APIs de PyPI/npm | Semanal | Media | Muy alta | 5-10 (anomalías) |
| 8 | StackOverflow (patterns) | StackExchange API | Diaria | Baja | Alta | 5-15 |
| 9 | Reddit/HN (filtro revisado) | PRAW + HN API | Horas | Baja | Media | 10-20 |

**SEÑAL EDITORIAL Y ACADÉMICA — Velocidad: días a semanas**

| # | Fuente | Método de acceso | Velocidad | Dificultad | Prioridad | Items/día estimados |
|---|--------|-----------------|-----------|------------|-----------|-------------------|
| 10 | Engineering blogs (postmortems) | RSS + scraping selectivo | Variable | Baja | Alta | 1-5 |
| 11 | Newsletters de alta señal | RSS (Import AI, The Batch, AI Breakfast) | Semanal | Baja | Media | 2-5/semana |
| 12 | ArXiv (sin filtro de citas) | API HTTP vía librería `arxiv` | Semanal | Baja | Media | 10-20 |
| 13 | YouTube (transcripciones) | YouTube Data API v3 + youtube-transcript-api | Días | Baja | Baja-media | 3-5 |

**SEÑAL PROFESIONAL — Velocidad: semanal a mensual**

| # | Fuente | Método de acceso | Velocidad | Dificultad | Prioridad | Items/día estimados |
|---|--------|-----------------|-----------|------------|-----------|-------------------|
| 14 | Job postings técnicos | Scraping HN Who's Hiring + APIs | Semanal | Media | Alta | 5-10/semana |
| 15 | Conferencias (programas/CFPs) | HTTP fetch de webs de conferencias | Mensual | Baja | Media | 1-5/mes |

**Estimación total:** ~80-150 items/día en días activos, ~200-300 items/semana.

### 4.3 Detalle por fuente

#### Fuente 1: Documentación Oficial Anthropic

**Objetivo:** Detectar cambios en la documentación canónica antes de cualquier anuncio.

**URLs monitorizadas:**
- `https://docs.anthropic.com` (docs generales)
- `https://github.com/anthropics/claude-code` (README, CHANGELOG, docs/)

**Método:** HTTP fetch del contenido, almacenamiento de snapshot, comparación diff con la versión anterior. Solo se reportan diffs no triviales (se ignoran cambios de formato, typos, y actualizaciones menores de fecha).

**Filtro:** Cambios semánticos reales. Un nuevo concepto, una deprecación, un cambio de API, una nueva capability documentada.

#### Fuente 2: GitHub Issues/PRs de Repos Críticos

**Objetivo:** Capturar decisiones arquitectónicas, problemas sistémicos, y debates técnicos en tiempo real.

**Repos monitorizados:**
- `anthropics/claude-code`
- `anthropics/anthropic-sdk-python`
- `anthropics/anthropic-sdk-typescript`
- Repos oficiales de MCP servers de Anthropic
- Top 10 repos comunitarios MCP por actividad (lista actualizable en config)

**Filtro:**
- Issues con >5 comentarios O con label `bug`, `enhancement`, `architecture`
- PRs con >500 líneas cambiadas O que tocan archivos de arquitectura
- Discussions con >3 respuestas

**Método:** GitHub REST API con token autenticado.

#### Fuente 3: Simon Willison's Blog

**Objetivo:** La mejor fuente individual de tracking diario del ecosistema LLM aplicado. Cubre cambios en APIs, experimentos, y observaciones técnicas antes de que sean mainstream.

**URL:** `https://simonwillison.net/` (RSS feed)

**Filtro:** Se procesan todos los posts. La relevancia semántica al ecosistema Claude/MCP se evalúa en el Signal Ranker.

#### Fuente 4: Podcasts Técnicos

**Objetivo:** Capturar análisis profundos sobre arquitectura real, tradeoffs de diseño, y adopción empresarial que solo existen en formato conversacional.

**Podcasts monitorizados:**

| Podcast | Feed RSS | Frecuencia |
|---------|----------|------------|
| Latent Space | `https://www.latent.space/podcast` (RSS) | Semanal |
| Practical AI | `https://practicalai.fm/` (RSS) | Semanal |
| The Cognitive Revolution | `https://www.cognitiverevolution.ai/` (RSS) | Variable |
| Lex Fridman Podcast | `https://lexfridman.com/podcast/` (RSS) | Variable |
| No Priors | Feed Apple Podcasts | Semanal |

**Método:** Descarga del audio vía RSS → transcripción con faster-whisper (modelo `whisper-small`) → procesamiento del texto.

**Restricción de hardware:** La transcripción se ejecuta como pre-proceso separado (Fase 0) para liberar los ~2GB de RAM que consume whisper antes de iniciar el pipeline principal. Las transcripciones se almacenan en `data/transcripts/`.

**Filtro de relevancia:** No todos los episodios son relevantes. El Signal Ranker evalúa el título y los primeros 500 tokens de la transcripción para decidir si se procesa el episodio completo. Esto evita gastar llamadas a Claude en episodios irrelevantes.

#### Fuente 5: GitHub Repos Emergentes (<100★)

**Objetivo:** Detección temprana de proyectos con crecimiento acelerado antes de que sean mainstream.

**Criterio de inclusión:** Repos con <100 estrellas, creados en las últimas 2 semanas, que cumplan al menos una de estas condiciones:
- >100 estrellas ganadas en <7 días
- Topics que incluyan combinaciones relevantes: `claude`, `mcp`, `anthropic`, `llm-agent`, `tool-use`, `computer-use`, `multi-agent`

**Método:** GitHub REST API. Query diaria por topics + filtro por fecha de creación + cálculo de velocidad de crecimiento de estrellas.

**Tracking:** Se almacena el histórico de estrellas para calcular aceleración (no solo valor absoluto).

#### Fuente 6: GitHub Repos Consolidados (>100★)

**Objetivo:** Mantener el tracking de proyectos establecidos del ecosistema.

**Criterio de inclusión:** Repos con >100 estrellas, actualizados en las últimas 24h, con topics relevantes.

**Topics:** `claude`, `claude-code`, `mcp`, `anthropic`, `llm-agent`, `tool-use`, `computer-use`, `multi-agent`

**Método:** GitHub REST API. Idéntico al v1 pero con topics ampliados.

#### Fuente 7: Paquetes PyPI/npm (Growth Tracking)

**Objetivo:** Detectar adopción real midiendo descargas, no declaraciones.

**Paquetes monitorizados en PyPI:**
- `anthropic` (SDK oficial)
- `anthropic-cli`
- Paquetes con keyword `mcp` o `claude` en metadata
- Top 20 paquetes por descarga en la categoría LLM tooling (lista mantenida en config)

**Paquetes monitorizados en npm:**
- `@anthropic-ai/sdk`
- `@anthropic-ai/claude-code`
- Paquetes con keyword `mcp` o `claude`

**Método:** API de PyPI (`pypistats.org/api`) para descargas semanales. API de npm (`api.npmjs.org/downloads`) para descargas.

**Señal buscada:** No son los números absolutos, sino los cambios: crecimiento acelerado, nuevos paquetes con adopción rápida, o caídas en paquetes consolidados que sugieren migración.

**Almacenamiento:** Histórico semanal en `data/packages/` para calcular tendencias.

#### Fuente 8: StackOverflow

**Objetivo:** Identificar problemas reales de producción a través de las preguntas que hace la gente.

**Tags monitorizados:**
- `claude-code`
- `anthropic-api`
- `mcp` (Model Context Protocol)

**Búsquedas adicionales:** Queries de texto libre: "claude code", "mcp server", "anthropic sdk"

**Método:** StackExchange API v2.3.

**Señales buscadas:**
- Preguntas nuevas con alta actividad (>3 respuestas en <48h)
- Preguntas sin respuesta aceptada (problema no resuelto)
- Patrones de preguntas repetidas sobre el mismo tema en <2 semanas (problema sistémico)
- Nuevas respuestas con alto score en preguntas antiguas (algo cambió)

#### Fuente 9: Reddit y Hacker News

**Objetivo:** Capturar conversación técnica de la comunidad, con filtro revisado respecto a v1.

**Reddit — Subreddits:** `LocalLLaMA`, `ClaudeAI`, `programming`, `MachineLearning`

**Reddit — Filtro revisado:** Priorizar posts con alta ratio comentarios/votos (debate técnico real) sobre posts con muchos votos pero pocos comentarios (contenido viral sin profundidad). Mínimo: 5 comentarios.

**Hacker News — Filtro revisado:**
- `Ask HN:` con keywords relevantes (independiente del score): señal de problemas reales
- `Show HN:` con >3 comentarios técnicos: señal de experimentación real
- Stories generales: >30 puntos (bajado desde 50 en v1)

**Método:** PRAW para Reddit, HN API pública para Hacker News.

#### Fuente 10: Engineering Blogs (Postmortems y Arquitectura)

**Objetivo:** Capturar experiencia real de producción documentada por equipos de ingeniería.

**Blogs monitorizados (RSS):**

| Blog | URL RSS | Tipo de señal |
|------|---------|---------------|
| Netflix TechBlog | `netflixtechblog.com/feed` | Arquitectura a escala |
| Cloudflare Engineering | `blog.cloudflare.com/tag/engineering/rss` | Infraestructura y AI |
| Dropbox Tech | `dropbox.tech/feed` | Adopción enterprise |
| AWS Blog (AI) | `aws.amazon.com/blogs/machine-learning/feed` | Servicios cloud + AI |
| Anthropic Blog | `blog.anthropic.com/rss` | Fuente oficial |
| OpenAI Developer Blog | `developers.openai.com/blog/rss` | Competencia directa |

**Filtro de valor:** No todos los posts de engineering blogs son iguales. El sistema prioriza por tipo de contenido:

| Tipo de post | Valor | Acción |
|-------------|-------|--------|
| Postmortem técnico | Muy alto | Procesar siempre |
| Decisión de arquitectura con datos | Muy alto | Procesar siempre |
| Benchmark propio con metodología | Alto | Procesar si es relevante al ecosistema |
| Migración documentada (de X a Y) | Alto | Procesar si involucra LLMs/agentes |
| Tutorial de uso básico | Bajo | Descartar |
| Anuncio de feature sin detalle técnico | Medio | Procesar solo si es de Anthropic o competidor directo |

#### Fuente 11: Newsletters de Alta Señal

**Objetivo:** Capturar el análisis curado de expertos que filtran y contextualizan el ecosistema.

| Newsletter | URL/RSS | Frecuencia | Señal |
|-----------|---------|------------|-------|
| Import AI (Jack Clark) | `importai.substack.com` | Semanal | Análisis de papers y tendencias |
| The Batch (deeplearning.ai) | `deeplearning.ai/the-batch` | Semanal | Síntesis estratégica |
| AI Breakfast | `aibreakfast.com` | Diaria | Curación de señal técnica |

**Método:** RSS parsing. Se procesan como items editoriales con el pipeline estándar.

#### Fuente 12: ArXiv

**Objetivo:** Conocimiento académico riguroso, con filtro corregido respecto a v1.

**Cambios respecto a v1:**

| Aspecto | v1 | v2 |
|---------|----|----|
| Filtro de citas | >10 citas | Sin filtro de citas |
| Filtro de fecha | Sin restricción | <7 días (papers frescos) |
| Filtro de autores | Ninguno | Lista de autores de alto impacto (configurable) |
| Categorías | cs.CL, cs.SE, cs.AI | + cs.HC (Human-Computer Interaction), cs.CR (Criptografía/Seguridad en agentes) |
| Límite | 20/día | Sin límite duro; priorizar por novedad |

**Método:** API HTTP vía librería `arxiv`. Búsqueda por categorías + keywords relevantes.

#### Fuente 13: YouTube

**Objetivo:** Contenido explicativo y demostraciones, procesado vía transcripción.

**Canales monitorizados:** Anthropic oficial + canales técnicos configurables.

**Método:** YouTube Data API v3 para descubrir videos nuevos + `youtube-transcript-api` para obtener transcripciones (preferencia por transcripciones manuales sobre automáticas).

**Límite:** 5 videos/canal/día. Quota YouTube API: 10.000 unidades/día (gratis).

#### Fuente 14: Job Postings Técnicos

**Objetivo:** Detectar adopción empresarial real con meses de adelanto respecto a cualquier caso de estudio público.

**Fuentes:**
- Hacker News "Who's Hiring" (mensual): scraping de posts con keywords relevantes
- LinkedIn Jobs (si API accesible): búsquedas con keywords Claude, MCP, multi-agent

**Keywords de búsqueda:** "Claude Code", "Claude API", "MCP", "Model Context Protocol", "multi-agent systems", "AI-assisted development", "LLM agent"

**Señal:** Un anuncio que pide "experiencia en multi-agent systems con Claude, integración MCP, y evaluación de LLMs" revela la arquitectura interna de la empresa antes de cualquier blog post.

**Frecuencia:** Semanal (los job postings cambian lentamente).

#### Fuente 15: Conferencias

**Objetivo:** Capturar lo que la comunidad técnica considera importante con lead time de 2-6 meses.

**Conferencias monitorizadas:**

| Conferencia | URL | Frecuencia |
|------------|-----|------------|
| NeurIPS | `neurips.cc` | Anual (programa publicado meses antes) |
| ICLR | `iclr.cc` | Anual |
| PyCon US | `us.pycon.org` | Anual |
| SREcon | `usenix.org/conferences/byname/925` | Semi-anual |

**Señal buscada:** Títulos y abstracts de talks aceptados sobre agentes, MCP, LLMs en producción. CFPs que revelan qué temas se consideran emergentes.

**Método:** HTTP fetch de páginas de programa. Frecuencia: semanal (los programas se actualizan lentamente).

### 4.4 Fases de implementación de fuentes

| Fase | Semanas | Fuentes incluidas |
|------|---------|-------------------|
| Fase 1 — Fundación | 1-2 | Docs oficiales (1), GitHub Issues/PRs (2), Simon Willison (3), StackOverflow (8), GitHub emergentes (5), GitHub consolidados (6) |
| Fase 2 — Señal primaria | 3-4 | Podcasts (4), PyPI/npm (7), Job postings (14), Reddit/HN revisado (9), Newsletters (11) |
| Fase 3 — Señal avanzada | Mes 2 | Engineering blogs (10), ArXiv revisado (12), YouTube (13), Conferencias (15) |

---

## 5. Pipeline de Recolección

### 5.1 Visión general

El pipeline de recolección es la primera fase de ejecución. Su responsabilidad es conectarse a cada fuente, extraer items nuevos desde la última ejecución, normalizarlos a un formato común (`CollectedItem`), y almacenarlos en disco para su procesamiento posterior.

Cada collector es independiente: si uno falla, el sistema registra el error y continúa con los demás. Al final de la fase de recolección se tiene una lista de `CollectedItem` en disco y un registro de errores.

### 5.2 Schema: CollectedItem

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class SourceType(str, Enum):
    DOCS_OFFICIAL = "docs_official"
    GITHUB_ISSUES = "github_issues"
    GITHUB_PRS = "github_prs"
    GITHUB_DISCUSSIONS = "github_discussions"
    GITHUB_REPO_EMERGING = "github_repo_emerging"
    GITHUB_REPO_CONSOLIDATED = "github_repo_consolidated"
    BLOG_WILLISON = "blog_willison"
    PODCAST = "podcast"
    PYPI = "pypi"
    NPM = "npm"
    STACKOVERFLOW = "stackoverflow"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    ENGINEERING_BLOG = "engineering_blog"
    NEWSLETTER = "newsletter"
    ARXIV = "arxiv"
    YOUTUBE = "youtube"
    JOB_POSTING = "job_posting"
    CONFERENCE = "conference"

class CollectedItem(BaseModel):
    id: str = Field(description="Hash único: SHA256(source_type + url)")
    title: str
    url: str
    source_type: SourceType
    source_name: str = Field(description="Nombre legible: 'GitHub Issues - anthropics/claude-code'")
    published_at: datetime
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    content: str = Field(description="Contenido textual completo o truncado a 15.000 tokens")
    content_truncated: bool = Field(default=False)
    metadata: dict = Field(default_factory=dict, description="Datos específicos de la fuente: stars, comments, score, downloads, etc.")
```

**Campo `metadata` — ejemplos por fuente:**

| Fuente | Campos en metadata |
|--------|--------------------|
| GitHub Issues/PRs | `repo`, `labels`, `comment_count`, `state`, `lines_changed` (para PRs) |
| GitHub Repos | `stars`, `stars_7d` (ganadas en 7 días), `forks`, `topics`, `created_at` |
| StackOverflow | `score`, `answer_count`, `is_answered`, `view_count`, `tags` |
| Reddit | `score`, `num_comments`, `subreddit`, `comment_score_ratio` |
| HN | `points`, `num_comments`, `type` (ask/show/story) |
| PyPI/npm | `weekly_downloads`, `prev_weekly_downloads`, `growth_pct`, `version` |
| Podcasts | `duration_seconds`, `podcast_name`, `episode_number` |
| ArXiv | `categories`, `authors`, `pdf_url` |
| Job Postings | `company`, `location`, `keywords_matched` |
| Engineering Blogs | `company`, `post_type` (postmortem/architecture/benchmark/migration/tutorial/announcement) |
| Docs Oficiales | `diff_summary`, `sections_changed`, `change_type` (new/modified/deprecated) |

### 5.3 Clase base: BaseCollector

Todos los collectors heredan de `BaseCollector`, que define la interfaz común y el manejo de errores.

**Interfaz:**

```python
class BaseCollector(BaseModel):
    name: str
    source_type: SourceType
    enabled: bool = True
    last_run: datetime | None = None

    async def collect(self, since: datetime) -> list[CollectedItem]:
        """Recolecta items nuevos desde `since`. Cada subclase implementa esto."""
        ...

    def deduplicate(self, items: list[CollectedItem]) -> list[CollectedItem]:
        """Elimina duplicados por ID dentro del batch."""
        ...
```

**Contrato:**
- `collect()` nunca lanza excepciones no controladas. Si la fuente falla, retorna lista vacía y el error se captura en el orquestador.
- Cada collector es responsable de truncar `content` a 15.000 tokens si el contenido original es más largo.
- El campo `id` es determinista: misma fuente + misma URL siempre produce el mismo ID, lo que permite deduplicación entre ejecuciones.

### 5.4 Lógica específica por collector

#### Docs Oficiales (`docs.py`)

**Flujo:**
1. Fetch HTTP de cada URL configurada
2. Comparar con snapshot almacenado en `data/snapshots/`
3. Si hay diff no trivial → generar `CollectedItem` con el diff como `content`
4. Almacenar nuevo snapshot

**Definición de "no trivial":** Cambios que no sean solo whitespace, fechas de copyright, o versiones de footer. El diff se calcula a nivel de sección (heading H2/H3), no a nivel de línea.

#### GitHub Issues/PRs (`github_signals.py`)

**Flujo:**
1. Para cada repo configurado, query a `/repos/{owner}/{repo}/issues` con `since={last_run}`, `state=all`, `sort=updated`
2. Filtrar por criterios: >5 comentarios, labels relevantes, o >500 líneas cambiadas (PRs)
3. Para issues/PRs que pasan filtro: fetch del body + primeros 10 comentarios como `content`

**Rate limit GitHub API:** 5.000 requests/hora con token. Con ~15 repos monitorizados y queries paginadas, el consumo estimado es ~100-200 requests/ciclo. Muy dentro del límite.

#### GitHub Repos Emergentes (`github_emerging.py`)

**Flujo:**
1. Query por topics relevantes, filtro `created:>{14_days_ago}`, sort por stars
2. Para cada repo encontrado: calcular velocidad de crecimiento comparando con datos históricos almacenados
3. Filtrar: repos que han ganado >15 estrellas/día en la última semana

**Tracking de crecimiento:** Se almacena un JSON en `data/` con `{repo_full_name: {date: stars}}` para calcular aceleración.

#### Podcasts (`podcasts.py`)

**Flujo (pre-proceso, Fase 0):**
1. Parse RSS de cada podcast configurado
2. Detectar episodios nuevos (no presentes en `data/transcripts/`)
3. Descargar audio (mp3)
4. Transcribir con faster-whisper modelo `whisper-small`
5. Almacenar transcripción en `data/transcripts/{podcast_name}/{episode_id}.txt`
6. Eliminar archivo de audio (liberar disco)

**Flujo (pipeline principal):**
1. Leer transcripciones nuevas de `data/transcripts/`
2. Generar `CollectedItem` con los primeros 15.000 tokens de la transcripción como `content`

**Nota:** La transcripción solo corre si hay episodios nuevos. Si no hay, Fase 0 termina en segundos.

#### Paquetes PyPI/npm (`packages.py`)

**Flujo:**
1. Para cada paquete configurado, fetch de estadísticas de descargas semanales
2. Comparar con histórico almacenado en `data/packages/`
3. Calcular `growth_pct` respecto a la semana anterior
4. Solo generar `CollectedItem` si hay anomalía: >50% crecimiento semanal, o paquete nuevo con >1.000 descargas/semana

**Frecuencia real:** Aunque el pipeline corre diario, las estadísticas de PyPI/npm se actualizan semanalmente. El collector solo genera items cuando hay datos nuevos.

#### StackOverflow (`stackoverflow.py`)

**Flujo:**
1. Query a StackExchange API por tags y búsquedas de texto configurados
2. Filtrar por actividad reciente y criterios de señal
3. Para preguntas que pasan filtro: fetch de pregunta + top 3 respuestas como `content`

**Detección de patrones:** El collector mantiene un contador en `data/` de preguntas por tema/semana. Si >3 preguntas sobre el mismo tema en <2 semanas, genera un `CollectedItem` adicional de tipo "pattern detected" con las preguntas agrupadas.

### 5.5 Deduplicación

La deduplicación opera en dos niveles:

**Intra-ejecución:** Antes de pasar items al pipeline de procesamiento, se eliminan duplicados por `id` (mismo contenido de la misma fuente recogido por múltiples collectors).

**Inter-ejecución:** Antes de almacenar en ChromaDB, se verifica que el `id` no exista ya en el store. Si existe, se salta. Esto previene reprocesar items de días anteriores que siguen apareciendo en queries de API.

### 5.6 Manejo de errores

| Escenario | Comportamiento |
|-----------|---------------|
| API no responde (timeout) | Retry 2 veces con backoff exponencial (5s, 15s). Si falla → registrar error, continuar |
| Rate limit alcanzado | Registrar error con tiempo de reset. No reintentar en este ciclo |
| Contenido inválido/malformado | Registrar warning, saltar item, continuar |
| Credencial expirada | Registrar error crítico, notificar vía ntfy, continuar sin esa fuente |
| Collector completo falla | Registrar error, continuar con los demás collectors |

**Registro de errores:** Cada error se almacena en una lista `CollectionError` que se incluye en el digest diario.

```python
class CollectionError(BaseModel):
    collector_name: str
    source_type: SourceType
    error_type: str = Field(description="timeout | rate_limit | parse_error | auth_error | unknown")
    error_message: str
    timestamp: datetime
    retries_attempted: int
```

---

## 6. Pipeline de Procesamiento

### 6.1 Visión general

El pipeline de procesamiento toma los `CollectedItem` de la fase de recolección y los enriquece con metadatos de inteligencia: ranking de señal, novedad, impacto, y madurez. Este pipeline actúa como filtro inteligente antes del análisis profundo con Claude, reduciendo el número de items que requieren llamadas costosas al LLM.

**Flujo:**
```
CollectedItem
  │
  ▼
Signal Ranker ──── Asigna signal_score (1-10). Items con score <4 se descartan.
  │
  ▼
Novelty Detector ── Calcula novelty_score (0.0-1.0) contra histórico ChromaDB.
  │
  ▼
Impact Classifier ── Asigna impact_dimensions[] y impact_level.
  │
  ▼
Maturity Classifier ── Asigna maturity_level.
  │
  ▼
ProcessedItem (listo para análisis con Claude)
```

### 6.2 Schema: ProcessedItem

```python
class ImpactDimension(str, Enum):
    API = "api"
    INFRASTRUCTURE = "infrastructure"
    ORCHESTRATION = "orchestration"
    SECURITY = "security"
    PERFORMANCE = "performance"
    EVALUATION = "evaluation"
    TOOLING = "tooling"
    GOVERNANCE = "governance"
    BENCHMARK = "benchmark"
    DEVELOPER_EXPERIENCE = "developer_experience"

class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MaturityLevel(str, Enum):
    EXPERIMENTAL = "experimental"
    EMERGING = "emerging"
    PRODUCTION_VIABLE = "production_viable"
    CONSOLIDATED = "consolidated"
    DECLINING = "declining"

class ProcessedItem(BaseModel):
    collected_item: CollectedItem
    signal_score: int = Field(ge=1, le=10, description="Profundidad técnica + impacto potencial + evidencia práctica")
    novelty_score: float = Field(ge=0.0, le=1.0, description="0.0 = idéntico a contenido previo, 1.0 = completamente nuevo")
    impact_dimensions: list[ImpactDimension]
    impact_level: ImpactLevel
    maturity_level: MaturityLevel
    processing_metadata: dict = Field(default_factory=dict, description="Datos intermedios del procesamiento")
    discarded: bool = Field(default=False, description="True si signal_score < threshold")
    discard_reason: str | None = None
```

### 6.3 Componente: Signal Ranker

**Propósito:** Clasificar cada item por profundidad técnica, impacto potencial y evidencia práctica. El ranking determina si el item merece análisis profundo con Claude o se descarta.

**Modelo:** Claude Sonnet (`claude-sonnet-4-20250514`)

**Estrategia de eficiencia:** El Signal Ranker procesa items en batches de 10. Un solo prompt evalúa 10 items simultáneamente, devolviendo un score y justificación breve para cada uno. Esto reduce las llamadas a Claude de N a N/10.

**Prompt del Signal Ranker:**

```
Eres un analista de inteligencia técnica especializado en el ecosistema de Claude Code, 
MCP (Model Context Protocol), y AI-assisted development.

Evalúa cada uno de los siguientes {count} items y asigna un signal_score de 1 a 10.

Criterios de puntuación:
- Profundidad técnica: ¿contiene decisiones arquitectónicas, código real, métricas, o tradeoffs documentados?
- Impacto potencial: ¿afecta a cómo se construyen sistemas con Claude Code o MCP?
- Evidencia práctica: ¿viene de experiencia real (producción, benchmarks, postmortems) o es especulación/opinión?
- Novedad aparente: ¿parece información nueva o es repetición de conocimiento existente?

Escala:
- 1-3: Ruido. Contenido genérico, opinión sin evidencia, tutorial básico, marketing.
- 4-5: Señal baja. Información útil pero no urgente ni profunda.
- 6-7: Señal media. Contenido técnico con insights aplicables.
- 8-9: Señal alta. Decisión arquitectónica documentada, problema real de producción, benchmark con metodología.
- 10: Señal crítica. Cambio de paradigma, breaking change, vulnerabilidad, nueva capability fundamental.

Items a evaluar:
{items_batch_json}

Responde SOLO con un JSON array. Para cada item:
{
  "item_id": "...",
  "signal_score": N,
  "justification": "Una frase explicando el score"
}
```

**Threshold configurable:** Items con `signal_score < 4` se marcan como `discarded=True` y no pasan al análisis con Claude. El threshold es configurable en `config.yaml` (default: 4).

### 6.4 Componente: Novelty Detector

**Propósito:** Evaluar cuánto de nuevo aporta un item respecto al histórico almacenado en ChromaDB. Un item sobre un tema ya extensamente cubierto tiene menor novelty que uno que introduce un concepto no visto antes.

**Método:** No usa Claude. Usa ChromaDB directamente.

**Flujo:**
1. Tomar el `content` del item (primeros 500 tokens como texto de query)
2. Buscar los 5 documentos más similares en ChromaDB (`collection.query(query_texts=[...], n_results=5)`)
3. Calcular `novelty_score`:
   - Si no hay resultados similares (distancia > 0.8): `novelty_score = 1.0`
   - Si el resultado más similar tiene distancia < 0.3: `novelty_score = 0.1` (casi duplicado)
   - En otro caso: `novelty_score = distancia_media_top3`

**Ajuste:** Los umbrales de distancia se calibran tras las primeras semanas de operación con datos reales. Valores iniciales basados en defaults de ChromaDB con embeddings por defecto (all-MiniLM-L6-v2).

**Nota:** Este componente no requiere llamada a Claude, lo que lo hace muy barato y rápido. Es la primera línea de defensa contra contenido redundante.

### 6.5 Componente: Impact Classifier

**Propósito:** Categorizar cada item por las dimensiones arquitectónicas que afecta y su nivel de impacto.

**Modelo:** Claude Sonnet (`claude-sonnet-4-20250514`)

**Estrategia de eficiencia:** Se procesa en el mismo batch que el Signal Ranker. El prompt del Signal Ranker se extiende para pedir también dimensiones de impacto y nivel, evitando una llamada adicional.

**Extensión del prompt del Signal Ranker:**

```
Además del signal_score, para cada item proporciona:
- "impact_dimensions": lista de dimensiones afectadas. Valores válidos: 
  api, infrastructure, orchestration, security, performance, evaluation, 
  tooling, governance, benchmark, developer_experience
- "impact_level": uno de: low, medium, high, critical

Criterios de impact_level:
- low: Información contextual, no requiere acción.
- medium: Podría afectar decisiones de diseño en los próximos meses.
- high: Afecta decisiones de diseño actuales o resuelve un problema conocido.
- critical: Requiere atención inmediata. Breaking change, vulnerabilidad, o cambio fundamental.
```

**Output extendido por item:**
```json
{
  "item_id": "...",
  "signal_score": 7,
  "justification": "...",
  "impact_dimensions": ["api", "tooling"],
  "impact_level": "high"
}
```

### 6.6 Componente: Maturity Classifier

**Propósito:** Determinar en qué punto del ciclo de madurez se encuentra la tecnología o concepto descrito en el item.

**Modelo:** Incluido en el mismo batch de Claude Sonnet.

**Extensión del prompt:**

```
También para cada item proporciona:
- "maturity_level": uno de: experimental, emerging, production_viable, consolidated, declining

Criterios:
- experimental: Prueba de concepto, repo sin documentación, paper sin implementación.
- emerging: Proyecto con tracción inicial, primeros adopters, documentación incompleta.
- production_viable: Usado en producción por al menos una empresa/equipo documentada.
- consolidated: Ampliamente adoptado, documentación madura, ecosistema estable.
- declining: Alternativas mejores disponibles, mantenimiento reducido, migraciones documentadas.
```

### 6.7 Prompt unificado completo

Para maximizar eficiencia, Signal Ranker + Impact Classifier + Maturity Classifier se ejecutan en una sola llamada a Claude por batch de 10 items. El prompt completo es la combinación de los tres componentes descritos arriba.

**Resultado:** Una sola llamada a Claude Sonnet produce `signal_score`, `justification`, `impact_dimensions`, `impact_level`, y `maturity_level` para 10 items simultáneamente.

**Estimación de llamadas:** Con ~100-150 items/día y batches de 10 → 10-15 llamadas a Sonnet para el pipeline de procesamiento completo. Muy manejable.

### 6.8 Flujo de descarte

Los items descartados (`signal_score < threshold`) no se pierden completamente:
- Se almacenan en ChromaDB con metadata `discarded: true` para que el Novelty Detector pueda usarlos como referencia histórica
- Se listan en el digest diario en la sección "Items descartados" con su score y justificación
- No se envían al Analyzer (sin análisis profundo con Claude)

Esto permite auditar las decisiones de descarte y ajustar el threshold con datos reales.

---

## 7. Pipeline de Análisis con Claude

### 7.1 Visión general

El pipeline de análisis toma los `ProcessedItem` que pasaron el filtro del pipeline de procesamiento (items no descartados) y genera un análisis profundo de cada uno usando Claude Sonnet. Este es el paso que transforma datos enriquecidos en inteligencia técnica accionable.

### 7.2 Schema: AnalyzedItem

```python
class AnalyzedItem(BaseModel):
    processed_item: ProcessedItem
    summary: str = Field(description="Resumen de 2-3 oraciones")
    key_insights: list[str] = Field(description="3-5 insights principales")
    code_snippets: list[str] = Field(default_factory=list, description="Snippets de código relevantes extraídos o descritos")
    practical_applicability: str = Field(description="Cómo aplicar esto en desarrollo real con Claude Code")
    architectural_implications: str = Field(description="NUEVO en v2: qué implica para la arquitectura de sistemas con LLMs")
    related_topics: list[str] = Field(description="Temas relacionados para cross-referencia")
    tags: list[str] = Field(description="3-7 tags para clasificación")
    competitive_notes: str | None = Field(default=None, description="Notas sobre posición competitiva si aplica")
    analysis_model: str = Field(default="claude-sonnet-4-20250514")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 7.3 Prompt del Analyzer

**Modelo:** Claude Sonnet (`claude-sonnet-4-20250514`)

**Estrategia:** A diferencia del pipeline de procesamiento (batches de 10), el análisis se ejecuta item por item. Cada item requiere atención individual porque el contenido puede ser extenso (hasta 15.000 tokens) y el análisis debe ser profundo.

**Prompt completo:**

```
Eres un arquitecto senior especializado en AI-assisted development, con expertise profundo 
en Claude Code, MCP (Model Context Protocol), y sistemas multi-agente.

Analiza el siguiente recurso y genera un análisis técnico de alta calidad.

--- CONTEXTO DEL ITEM ---
Título: {title}
Fuente: {source_type} — {source_name}
URL: {url}
Fecha publicación: {published_at}
Signal Score: {signal_score}/10
Impact: {impact_level} — Dimensiones: {impact_dimensions}
Madurez: {maturity_level}

--- CONTENIDO ---
{content}

--- INSTRUCCIONES ---
Genera un análisis estructurado en JSON con los siguientes campos:

1. "summary": Resumen conciso de 2-3 oraciones. Qué es, por qué importa, cuál es la conclusión principal.

2. "key_insights": Array de 3-5 strings. Cada insight debe ser una observación técnica específica 
   y accionable, no una descripción genérica. Mal ejemplo: "Habla sobre MCP servers". 
   Buen ejemplo: "El patrón de retry con backoff exponencial en MCP tool calls reduce 
   errores de timeout un 40% según sus métricas".

3. "code_snippets": Array de strings. Si el recurso contiene o describe código relevante, 
   extrae los snippets más importantes. Si no hay código, array vacío.

4. "practical_applicability": String. Cómo puede un desarrollador que usa Claude Code 
   aplicar este conocimiento HOY. Sé concreto: qué cambiar, qué probar, qué evitar.

5. "architectural_implications": String. Qué implica este recurso para la arquitectura 
   de sistemas que usan LLMs como asistentes de desarrollo. ¿Cambia algún patrón conocido? 
   ¿Introduce un tradeoff nuevo? ¿Confirma o contradice una práctica establecida?

6. "related_topics": Array de strings. Temas relacionados para cross-referencia con otros 
   items en la base de conocimiento. Usa nombres cortos y consistentes: "mcp-servers", 
   "context-window", "multi-agent", "prompt-engineering", "code-review", etc.

7. "tags": Array de 3-7 strings. Tags para clasificación. Incluye al menos: 
   la fuente (github, arxiv, podcast...), el tema principal, y el ecosistema (claude, openai, general).

8. "competitive_notes": String o null. Si el recurso menciona comparaciones entre herramientas, 
   migraciones, benchmarks comparativos, o diferencias entre ecosistemas, documéntalas aquí. 
   Si no hay contenido competitivo, null.

Responde SOLO con el JSON, sin texto adicional.
```

### 7.4 Manejo de contenido largo

El campo `content` del `CollectedItem` puede tener hasta 15.000 tokens. Para transcripciones de podcasts o artículos largos, esto puede acercarse al límite práctico de calidad en la respuesta de Sonnet.

**Estrategia para contenido >10.000 tokens:**
1. El Analyzer envía el contenido completo pero añade al prompt: `"El contenido es extenso. Prioriza los insights más relevantes al ecosistema Claude Code/MCP. Ignora secciones no relacionadas."`
2. Si la respuesta de Claude es truncada o inválida, se reintenta con el contenido reducido a los primeros 8.000 tokens.

**Timeout:** 120 segundos por item. Si Claude no responde en ese tiempo, se registra error y se salta el item.

### 7.5 Validación del output

La respuesta de Claude se parsea como JSON y se valida contra el schema `AnalyzedItem` de Pydantic.

**Escenarios de fallo:**
| Escenario | Acción |
|-----------|--------|
| JSON inválido | Retry 1 vez con prompt añadido: "Tu respuesta anterior no fue JSON válido. Responde SOLO con JSON." |
| Campos faltantes | Rellenar con defaults (`[]` para listas, `""` para strings, `null` para opcionales) |
| Segundo retry falla | Registrar error, almacenar item sin análisis profundo (solo con datos del pipeline de procesamiento) |

### 7.6 Estimación de llamadas

**Items que pasan filtro:** ~60-100/día (asumiendo ~40% descartados por Signal Ranker)

**Llamadas al Analyzer:** 1 por item → 60-100 llamadas a Sonnet/día

**Llamadas totales al pipeline de procesamiento + análisis:** 10-15 (procesamiento en batch) + 60-100 (análisis individual) = **70-115 llamadas diarias a Claude Sonnet**.

---

## 8. Pipeline de Síntesis

### 8.1 Visión general

El pipeline de síntesis es donde el sistema pasa de "items individuales analizados" a "inteligencia técnica estratégica". Opera en tres frecuencias: diaria, semanal y mensual. Cada frecuencia responde a preguntas diferentes y genera outputs distintos.

| Frecuencia | Modelo | Input | Output |
|-----------|--------|-------|--------|
| Diaria | Claude Opus (`claude-opus-4-6`) | AnalyzedItems del día + contexto histórico de ChromaDB | Digest diario: tendencias, highlights, acciones |
| Semanal | Claude Opus (`claude-opus-4-6`) | Digests diarios de la semana + patrones acumulados | Reporte semanal: patrones emergentes, cambios de madurez, evolución competitiva |
| Mensual | Claude Opus (`claude-opus-4-6`) | Reportes semanales del mes + matriz competitiva | Reporte mensual: cambios estructurales, consolidación de tendencias, riesgos |

### 8.2 Schema: DailySynthesis

```python
class TrendDetected(BaseModel):
    name: str = Field(description="Nombre corto de la tendencia")
    description: str = Field(description="Descripción de 1-2 oraciones")
    evidence: list[str] = Field(description="IDs de items que soportan esta tendencia")
    confidence: float = Field(ge=0.0, le=1.0, description="Confianza basada en cantidad y calidad de evidencia")

class HighlightItem(BaseModel):
    item_id: str
    title: str
    source: str
    relevance_score: int
    why_it_matters: str

class RecommendedAction(BaseModel):
    action: str
    priority: str = Field(description="high | medium | low")
    related_items: list[str] = Field(description="IDs de items relacionados")

class DailySynthesis(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    day_relevance_score: int = Field(ge=1, le=10)
    total_items_collected: int
    total_items_analyzed: int
    total_items_discarded: int
    sources_active: int
    sources_failed: list[str]
    trends_detected: list[TrendDetected]
    historical_connections: list[str] = Field(description="Conexiones con contenido de días anteriores")
    highlights: list[HighlightItem]
    recommended_actions: list[RecommendedAction]
    synthesis_model: str = Field(default="claude-opus-4-6")
    synthesis_timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 8.3 Schema: WeeklySynthesis

```python
class PatternEvolution(BaseModel):
    pattern_name: str
    status: str = Field(description="new | growing | stable | declining")
    description: str
    first_seen: str = Field(description="Fecha YYYY-MM-DD en que se detectó por primera vez")
    evidence_count: int

class MaturityChange(BaseModel):
    technology: str
    previous_level: MaturityLevel
    current_level: MaturityLevel
    evidence: str

class CompetitiveShift(BaseModel):
    area: str = Field(description="Área donde hay movimiento competitivo")
    description: str
    winners: list[str]
    losers: list[str]

class WeeklySynthesis(BaseModel):
    week_start: str
    week_end: str
    week_relevance_score: int = Field(ge=1, le=10)
    total_items_week: int
    pattern_evolutions: list[PatternEvolution]
    maturity_changes: list[MaturityChange]
    competitive_shifts: list[CompetitiveShift]
    emerging_patterns: list[str] = Field(description="Patrones arquitectónicos nuevos detectados esta semana")
    anti_patterns: list[str] = Field(description="Anti-patrones documentados esta semana")
    top_highlights_week: list[HighlightItem]
    synthesis_model: str = Field(default="claude-opus-4-6")
```

### 8.4 Schema: MonthlySynthesis

```python
class StructuralChange(BaseModel):
    area: str
    description: str
    impact_assessment: str
    evidence_summary: str

class EmergingRisk(BaseModel):
    risk: str
    likelihood: str = Field(description="low | medium | high")
    potential_impact: str
    mitigation: str | None = None

class MonthlySynthesis(BaseModel):
    month: str = Field(description="YYYY-MM")
    month_relevance_score: int = Field(ge=1, le=10)
    total_items_month: int
    structural_changes: list[StructuralChange]
    consolidated_trends: list[str] = Field(description="Tendencias que se han confirmado este mes")
    emerging_risks: list[EmergingRisk]
    competitive_matrix_summary: str = Field(description="Resumen del estado competitivo del ecosistema")
    architectural_patterns_summary: str = Field(description="Patrones arquitectónicos dominantes este mes")
    key_recommendations: list[RecommendedAction]
    synthesis_model: str = Field(default="claude-opus-4-6")
```

### 8.5 Síntesis Diaria — Prompt

**Modelo:** Claude Opus (`claude-opus-4-6`)

**Input:**
1. Resúmenes de todos los `AnalyzedItem` del día (summary + key_insights + tags de cada uno)
2. Contenido relacionado de días anteriores obtenido de ChromaDB (query semántica con los temas del día, top 10 resultados)

**Prompt completo:**

```
Eres el motor de síntesis estratégica de AI Architect, un sistema de inteligencia técnica 
sobre el ecosistema de Claude Code y AI-assisted development.

Tu objetivo es transformar {count} análisis individuales de hoy en una síntesis estratégica 
que permita a un experto entender qué pasó hoy, qué significa, y qué hacer al respecto.

--- ANÁLISIS DE HOY ({count} items) ---
{daily_summaries_json}

--- CONTENIDO RELACIONADO DE DÍAS ANTERIORES ---
{related_historical_content}

--- INSTRUCCIONES ---
Genera una síntesis en JSON con los siguientes campos:

1. "day_relevance_score": Integer 1-10. ¿Cuán relevante fue el día para alguien que construye 
   con Claude Code? 1 = nada nuevo. 10 = día histórico con cambios fundamentales.

2. "trends_detected": Array de tendencias. Cada tendencia es un patrón que aparece 
   en 2+ items del día O que conecta con contenido de días anteriores. Incluye:
   - "name": nombre corto
   - "description": 1-2 oraciones
   - "evidence": array de item_ids que soportan la tendencia
   - "confidence": 0.0-1.0

3. "historical_connections": Array de strings. Conexiones explícitas con contenido previo: 
   "El tema X que apareció el día Y se confirma/contradice/expande con el item Z de hoy."

4. "highlights": Array de 1-3 items más importantes del día. Para cada uno:
   - "item_id", "title", "source", "relevance_score"
   - "why_it_matters": Por qué este item es el highlight del día (2-3 oraciones)

5. "recommended_actions": Array de acciones concretas. Cada acción es algo que el experto 
   debería hacer (investigar, probar, cambiar, leer en detalle). Incluye:
   - "action": descripción de la acción
   - "priority": high | medium | low
   - "related_items": array de item_ids

Responde SOLO con JSON válido.
```

### 8.6 Síntesis Semanal — Prompt

**Modelo:** Claude Opus (`claude-opus-4-6`)

**Input:**
1. Los 7 `DailySynthesis` de la semana (completos)
2. Todos los `AnalyzedItem` de la semana con `signal_score >= 7` (alta señal)
3. Matriz competitiva actual de ChromaDB (si existe)

**Prompt completo:**

```
Eres el motor de síntesis estratégica semanal de AI Architect.

Tienes 7 días de inteligencia técnica sobre el ecosistema Claude Code / AI-assisted development.
Tu objetivo es detectar patrones que solo son visibles a escala semanal: evoluciones, 
cambios de madurez, movimientos competitivos, y patrones arquitectónicos emergentes.

--- SÍNTESIS DIARIAS DE LA SEMANA ---
{weekly_daily_syntheses_json}

--- ITEMS DE ALTA SEÑAL (score >= 7) ---
{high_signal_items_json}

--- MATRIZ COMPETITIVA ACTUAL ---
{competitive_matrix_json}

--- INSTRUCCIONES ---
Genera una síntesis semanal en JSON:

1. "week_relevance_score": Integer 1-10 para la semana completa.

2. "pattern_evolutions": Patrones que evolucionaron esta semana.
   - "pattern_name", "status" (new|growing|stable|declining), "description", 
     "first_seen" (fecha), "evidence_count"

3. "maturity_changes": Tecnologías que cambiaron de nivel de madurez esta semana.
   - "technology", "previous_level", "current_level", "evidence"

4. "competitive_shifts": Movimientos en el paisaje competitivo.
   - "area", "description", "winners", "losers"

5. "emerging_patterns": Array de strings. Patrones arquitectónicos nuevos detectados 
   (ej: "MCP gateway pattern", "agent chain-of-thought validation").

6. "anti_patterns": Array de strings. Anti-patrones documentados esta semana.

7. "top_highlights_week": Los 3-5 items más impactantes de toda la semana.

Responde SOLO con JSON válido.
```

### 8.7 Síntesis Mensual — Prompt

**Modelo:** Claude Opus (`claude-opus-4-6`)

**Input:**
1. Los 4-5 `WeeklySynthesis` del mes
2. Items con `signal_score = 10` del mes (si los hay)
3. Histórico de matrices competitivas

**Prompt:**

```
Eres el motor de síntesis estratégica mensual de AI Architect.

Tienes un mes completo de inteligencia técnica. Tu objetivo es identificar cambios 
estructurales, consolidar tendencias, y evaluar riesgos emergentes que solo son visibles 
a escala mensual.

--- SÍNTESIS SEMANALES DEL MES ---
{monthly_weekly_syntheses_json}

--- ITEMS CRÍTICOS DEL MES (score = 10) ---
{critical_items_json}

--- INSTRUCCIONES ---
Genera una síntesis mensual en JSON:

1. "month_relevance_score": Integer 1-10 para el mes completo.

2. "structural_changes": Cambios estructurales en el ecosistema.
   - "area", "description", "impact_assessment", "evidence_summary"

3. "consolidated_trends": Tendencias que se han confirmado este mes (ya no son emergentes).

4. "emerging_risks": Riesgos detectados.
   - "risk", "likelihood" (low|medium|high), "potential_impact", "mitigation"

5. "competitive_matrix_summary": Estado competitivo del ecosistema en un párrafo.

6. "architectural_patterns_summary": Patrones arquitectónicos dominantes este mes en un párrafo.

7. "key_recommendations": Top 3-5 acciones recomendadas para el próximo mes.

Responde SOLO con JSON válido.
```

### 8.8 Componente: Competitive Mapper

**Propósito:** Mantener una matriz competitiva actualizada que compara Claude Code con alternativas.

**Ejecución:** Semanal, alimentada por items con `competitive_notes` no null.

**Schema:**

```python
class CompetitorProfile(BaseModel):
    name: str = Field(description="Claude Code | GitHub Copilot | Cursor | Windsurf | Cline | Aider | otros")
    model_backend: str = Field(description="Modelo LLM subyacente principal")
    extensibility: str = Field(description="MCP | plugins propietarios | API abierta | limitado")
    pricing_tier: str = Field(description="Rango de precio: free | $10-20/mo | $20-50/mo | enterprise")
    known_strengths: list[str]
    known_limitations: list[str]
    recent_changes: list[str] = Field(description="Cambios detectados en las últimas 4 semanas")
    last_updated: str

class CompetitiveMatrix(BaseModel):
    last_updated: str
    competitors: list[CompetitorProfile]
    key_differentiators: list[str] = Field(description="Diferenciadores principales del ecosistema Claude")
    gaps_detected: list[str] = Field(description="Áreas donde la competencia supera a Claude")
    opportunities: list[str] = Field(description="Oportunidades detectadas")
```

**Actualización:** Cada semana, el Competitive Mapper recibe los items con notas competitivas y la matriz actual, y genera una versión actualizada. Se almacena en `output/competitive/matrix-YYYY-WNN.md` y en ChromaDB.

### 8.9 Estimación de llamadas a Claude Opus

| Frecuencia | Llamadas/ciclo | Llamadas/mes |
|-----------|----------------|-------------|
| Síntesis diaria | 1 | ~30 |
| Síntesis semanal | 1 | ~4 |
| Competitive Mapper | 1 | ~4 |
| Síntesis mensual | 1 | 1 |
| **Total Opus** | — | **~39/mes** |

### 8.10 Resumen total de llamadas a Claude

| Componente | Modelo | Llamadas/día | Llamadas/mes |
|-----------|--------|-------------|-------------|
| Signal Ranker + Impact + Maturity (batch 10) | Sonnet | 10-15 | 300-450 |
| Analyzer (individual) | Sonnet | 60-100 | 1.800-3.000 |
| Síntesis diaria | Opus | 1 | 30 |
| Síntesis semanal | Opus | — | 4 |
| Competitive Mapper | Opus | — | 4 |
| Síntesis mensual | Opus | — | 1 |
| **Total Sonnet** | — | **70-115** | **2.100-3.450** |
| **Total Opus** | — | **~1** | **~39** |

---

## 9. Almacenamiento

### 9.1 Visión general

El almacenamiento en v2 opera en dos capas complementarias: ChromaDB para búsqueda semántica e histórico vectorial, y el sistema de archivos para outputs Markdown y datos auxiliares. Ambas capas se mantienen sincronizadas: todo lo que entra en ChromaDB genera o actualiza un archivo Markdown correspondiente.

### 9.2 ChromaDB — Configuración

**Modo de ejecución:** Embedded (no como contenedor separado). ChromaDB se instancia dentro del proceso Python principal usando `chromadb.PersistentClient`. Esto elimina el overhead de un segundo contenedor y simplifica la gestión de memoria en el Jetson con 8GB.

**Persistencia:** Los datos se almacenan en `data/chromadb/` y se montan como volumen Docker para persistir entre ejecuciones.

**Modelo de embeddings:** `all-MiniLM-L6-v2` (default de ChromaDB). Ligero (~80MB), funciona en ARM64, y es suficiente para la escala del sistema (~100-150 items/día, ~3.000-4.500/mes).

### 9.3 ChromaDB — Colecciones

El sistema usa 4 colecciones separadas para distintos tipos de datos:

| Colección | Contenido | Volumen estimado/mes |
|-----------|-----------|---------------------|
| `analyzed_items` | Análisis individuales completos | 2.000-3.000 docs |
| `daily_syntheses` | Síntesis diarias | 30 docs |
| `weekly_syntheses` | Síntesis semanales | 4 docs |
| `competitive_data` | Items con notas competitivas + matrices | 50-100 docs |

#### Colección: `analyzed_items`

Schema de metadatos:

```python
{
    "item_id": str,          # Hash SHA256 del CollectedItem
    "title": str,
    "url": str,
    "source_type": str,      # Valor del enum SourceType
    "source_name": str,
    "published_at": str,     # ISO 8601
    "collected_at": str,     # ISO 8601
    "signal_score": int,     # 1-10
    "novelty_score": float,  # 0.0-1.0
    "impact_level": str,     # low | medium | high | critical
    "impact_dimensions": str, # Comma-separated: "api,tooling,security"
    "maturity_level": str,   # experimental | emerging | production_viable | consolidated | declining
    "tags": str,             # Comma-separated
    "discarded": bool,       # True si fue descartado por Signal Ranker
    "has_competitive_notes": bool
}
```

**Documento almacenado (campo `documents`):** Concatenación de `summary + key_insights + practical_applicability + architectural_implications`. Este es el texto sobre el que se generan embeddings y se ejecutan búsquedas semánticas.

#### Colección: `daily_syntheses`

Schema de metadatos:

```python
{
    "date": str,               # YYYY-MM-DD
    "day_relevance_score": int,
    "total_items_collected": int,
    "total_items_analyzed": int,
    "sources_failed": str      # Comma-separated
}
```

**Documento:** JSON completo del `DailySynthesis` serializado como string. Permite búsqueda semántica sobre tendencias y highlights históricos.

#### Colección: `weekly_syntheses`

Schema de metadatos:

```python
{
    "week_start": str,
    "week_end": str,
    "week_relevance_score": int,
    "total_items_week": int
}
```

**Documento:** JSON completo del `WeeklySynthesis`.

#### Colección: `competitive_data`

Schema de metadatos:

```python
{
    "type": str,       # "item_note" | "matrix_snapshot"
    "date": str,
    "competitors_mentioned": str  # Comma-separated
}
```

**Documento:** Para items: el campo `competitive_notes` del `AnalyzedItem`. Para matrices: JSON del `CompetitiveMatrix`.

### 9.4 Consultas principales

| Consulta | Colección | Método | Uso |
|----------|-----------|--------|-----|
| Contenido similar al item actual | `analyzed_items` | `query(query_texts=[content], n_results=5)` | Novelty Detector |
| Contexto histórico para síntesis diaria | `analyzed_items` | `query(query_texts=[temas_del_dia], n_results=10, where={"discarded": False})` | Synthesizer diario |
| Tendencias históricas para síntesis semanal | `daily_syntheses` | `query(query_texts=[temas_semana], n_results=7)` | Synthesizer semanal |
| Evolución competitiva | `competitive_data` | `get(where={"type": "matrix_snapshot"}, limit=4)` | Competitive Mapper |
| Items por tag | `analyzed_items` | `get(where={"tags": {"$contains": tag}})` | Generador de topics |
| Items de alta señal recientes | `analyzed_items` | `get(where={"signal_score": {"$gte": 7}, "collected_at": {"$gte": fecha}})` | Synthesizer semanal |

### 9.5 Retención y limpieza

**Política de retención:**
- `analyzed_items`: Sin límite. El crecimiento estimado es ~36.000-54.000 docs/año, manejable para ChromaDB embedded.
- `daily_syntheses`: Sin límite (~365 docs/año).
- `weekly_syntheses`: Sin límite (~52 docs/año).
- `competitive_data`: Sin límite. Las matrices semanales son snapshots históricos útiles para análisis de tendencias.

**Estimación de almacenamiento en disco:** ~500MB-1GB/año para ChromaDB con embeddings. Aceptable para el Jetson.

**Backups:** `data/chromadb/` se puede respaldar con un simple `tar` del directorio. Se recomienda backup semanal automatizado vía cron.

### 9.6 Sistema de archivos — Estructura de datos auxiliares

```
data/
├── chromadb/                    # Persistencia ChromaDB
├── snapshots/                   # Snapshots de docs oficiales para diff
│   ├── docs.anthropic.com/
│   │   └── YYYY-MM-DD.html
│   └── claude-code-readme/
│       └── YYYY-MM-DD.md
├── transcripts/                 # Transcripciones de podcasts
│   ├── latent-space/
│   │   └── episode-XXX.txt
│   └── practical-ai/
│       └── episode-XXX.txt
├── packages/                    # Histórico de descargas PyPI/npm
│   ├── pypi/
│   │   └── weekly-YYYY-WNN.json
│   └── npm/
│       └── weekly-YYYY-WNN.json
├── github_stars/                # Tracking de crecimiento de estrellas
│   └── stars-YYYY-MM-DD.json
└── state/                       # Estado de ejecución
    ├── last_run.json            # Timestamp última ejecución exitosa
    ├── collection_errors.json   # Errores del último ciclo
    └── collector_state/         # Estado persistente por collector
        ├── stackoverflow_patterns.json
        └── github_emerging_history.json
```

---

## 10. Formato de Outputs

### 10.1 Estructura de archivos de output

```
output/
├── daily/
│   ├── 2026-02-15.md
│   ├── 2026-02-14.md
│   └── ...
├── weekly/
│   ├── 2026-W07.md
│   ├── 2026-W06.md
│   └── ...
├── monthly/
│   ├── 2026-02.md
│   ├── 2026-01.md
│   └── ...
├── topics/
│   ├── mcp-servers.md
│   ├── context-window.md
│   ├── multi-agent.md
│   ├── code-review.md
│   └── ...                      # Se crean dinámicamente según tags
├── competitive/
│   ├── matrix-latest.md         # Siempre apunta a la más reciente
│   ├── matrix-2026-W07.md
│   └── ...
├── master.md                    # Base de conocimiento acumulativa
└── index.md                     # Índice general con links a todo
```

### 10.2 Formato: Digest diario (`daily/YYYY-MM-DD.md`)

```markdown
# AI Architect Digest — YYYY-MM-DD

> **Relevancia del día:** X/10
> **Items recolectados:** N | **Analizados:** M | **Descartados:** K
> **Fuentes activas:** P de Q | **Errores:** [lista o "ninguno"]
> **Duración del ciclo:** HH:MM:SS

---

## Síntesis del Día

### Tendencias Detectadas

#### [Nombre de tendencia] (confianza: X.X)
[Descripción de 1-2 oraciones]
- Evidencia: [Item 1](url), [Item 2](url)

---

### Highlights

#### 1. [Título del item](url)
**Fuente:** source_name | **Signal:** X/10 | **Impacto:** level | **Madurez:** level
> [Por qué importa — 2-3 oraciones del campo why_it_matters]

---

### Conexiones Históricas
- [Conexión con contenido de días anteriores]

### Acciones Recomendadas
- [ ] **[alta]** [Acción 1] — Relacionado: [Item](url)
- [ ] **[media]** [Acción 2] — Relacionado: [Item](url)

---

## Items Analizados

### Señal Primaria (N items)

#### [Título](url)
- **Signal:** X/10 | **Novedad:** X.X | **Impacto:** level — dimensions | **Madurez:** level
- **Tags:** tag1, tag2, tag3
- **Resumen:** [summary]
- **Insights clave:**
  - [insight 1]
  - [insight 2]
- **Aplicabilidad:** [practical_applicability]
- **Implicaciones arquitectónicas:** [architectural_implications]
- **Código relevante:**
  ```
  [snippet si hay]
  ```
- **Notas competitivas:** [competitive_notes si hay]

---

### Señal de Comportamiento (N items)
[Misma estructura que arriba]

### Señal Editorial (N items)
[Misma estructura que arriba]

### Señal Profesional (N items)
[Misma estructura que arriba]

---

## Items Descartados (K items)

| Título | Fuente | Signal Score | Razón |
|--------|--------|-------------|-------|
| [Título](url) | source | X/10 | [justification del Signal Ranker] |

---

## Errores del Ciclo

| Collector | Tipo | Mensaje | Reintentos |
|-----------|------|---------|------------|
| [nombre] | [tipo] | [mensaje] | N |
```

### 10.3 Formato: Reporte semanal (`weekly/YYYY-WNN.md`)

```markdown
# AI Architect — Semana YYYY-WNN

> **Periodo:** YYYY-MM-DD a YYYY-MM-DD
> **Relevancia de la semana:** X/10
> **Total items:** N

---

## Patrones en Evolución

### [Patrón] — Status: [new|growing|stable|declining]
- **Primera detección:** YYYY-MM-DD
- **Evidencia esta semana:** N items
- [Descripción]

---

## Cambios de Madurez

| Tecnología | Anterior | Actual | Evidencia |
|-----------|----------|--------|-----------|
| [tech] | emerging | production_viable | [evidencia] |

---

## Movimientos Competitivos

### [Área]
[Descripción del movimiento]
- **Ganadores:** [lista]
- **Perdedores:** [lista]

---

## Patrones Arquitectónicos Emergentes
- [Patrón nuevo detectado esta semana]

## Anti-patrones Documentados
- [Anti-patrón documentado esta semana]

---

## Top Highlights de la Semana

### 1. [Título](url)
**Día:** YYYY-MM-DD | **Signal:** X/10
> [why_it_matters]

---

## Resumen de Digests Diarios

| Día | Relevancia | Items | Highlights |
|-----|-----------|-------|------------|
| Lunes | X/10 | N | [highlight] |
| Martes | X/10 | N | [highlight] |
| ... | | | |
```

### 10.4 Formato: Reporte mensual (`monthly/YYYY-MM.md`)

```markdown
# AI Architect — YYYY-MM

> **Relevancia del mes:** X/10
> **Total items:** N

---

## Cambios Estructurales

### [Área]
- **Descripción:** [qué cambió]
- **Evaluación de impacto:** [cómo afecta al ecosistema]
- **Evidencia:** [resumen de evidencia]

---

## Tendencias Consolidadas
- [Tendencia que se confirmó este mes y ya no es emergente]

---

## Riesgos Emergentes

| Riesgo | Probabilidad | Impacto Potencial | Mitigación |
|--------|-------------|-------------------|------------|
| [riesgo] | high | [impacto] | [mitigación] |

---

## Estado Competitivo
[Párrafo resumen del Competitive Mapper]

## Patrones Arquitectónicos del Mes
[Párrafo resumen de patrones dominantes]

---

## Recomendaciones para el Próximo Mes
- [ ] **[alta]** [Recomendación 1]
- [ ] **[media]** [Recomendación 2]

---

## Resumen de Semanas

| Semana | Relevancia | Items | Evento principal |
|--------|-----------|-------|-----------------|
| W01 | X/10 | N | [evento] |
| W02 | X/10 | N | [evento] |
| ... | | | |
```

### 10.5 Formato: Índice temático (`topics/[topic].md`)

```markdown
# [Topic Name]

> Última actualización: YYYY-MM-DD
> Total items: N
> Fuentes principales: GitHub (X), Blogs (Y), StackOverflow (Z)

---

## Últimos 30 días

### YYYY-MM-DD | [Título](url)
**Fuente:** source | **Signal:** X/10 | **Madurez:** level
> [summary — 1-2 oraciones]

---

## Estadísticas

| Métrica | Valor |
|---------|-------|
| Total items históricos | N |
| Signal score medio | X.X |
| Fuente más frecuente | [fuente] |
| Madurez predominante | [level] |
| Última detección | YYYY-MM-DD |
```

### 10.6 Formato: Matriz competitiva (`competitive/matrix-latest.md`)

```markdown
# Matriz Competitiva — YYYY-MM-DD

---

## Comparativa de Herramientas

| Dimensión | Claude Code | GitHub Copilot | Cursor | Windsurf | Cline | Aider |
|-----------|------------|----------------|--------|----------|-------|-------|
| Modelo backend | Claude Sonnet/Opus | GPT-4o / Claude | Claude/GPT-4o | Claude/GPT-4o | Claude/GPT-4o | Claude/GPT-4o |
| Extensibilidad | MCP (abierto) | Extensiones VS Code | Plugins propios | Plugins propios | MCP + propios | CLI plugins |
| Precio | $20/mo (Pro) | $10/mo | $20/mo | $15/mo | Gratis + API | Gratis + API |
| Fortalezas | [lista] | [lista] | [lista] | [lista] | [lista] | [lista] |
| Limitaciones | [lista] | [lista] | [lista] | [lista] | [lista] | [lista] |

---

## Cambios Recientes (últimas 4 semanas)

### [Competidor]
- [Cambio detectado con fecha y fuente]

---

## Diferenciadores Clave del Ecosistema Claude
- [diferenciador 1]

## Gaps Detectados
- [área donde la competencia supera a Claude]

## Oportunidades
- [oportunidad detectada]
```

### 10.7 Formato: Master (`master.md`)

```markdown
# AI Architect — Base de Conocimiento

> **Iniciado:** YYYY-MM-DD | **Última actualización:** YYYY-MM-DD
> **Total items analizados:** N | **Total descartados:** M

---

## Índice de Temas
| Tema | Items | Última actividad | Signal medio |
|------|-------|-----------------|-------------|
| [mcp-servers](topics/mcp-servers.md) | N | YYYY-MM-DD | X.X |
| [context-window](topics/context-window.md) | N | YYYY-MM-DD | X.X |
| ... | | | |

---

## Últimos 7 Días
| Fecha | Relevancia | Items | Top Highlight |
|-------|-----------|-------|---------------|
| [YYYY-MM-DD](daily/YYYY-MM-DD.md) | X/10 | N | [título] |
| ... | | | |

---

## Highlights Históricos (Signal 9-10)
- **YYYY-MM-DD** | [Título](url) — Signal 10/10
  > [why_it_matters]

---

## Última Matriz Competitiva
→ [Ver matriz completa](competitive/matrix-latest.md)

## Último Reporte Semanal
→ [Semana YYYY-WNN](weekly/YYYY-WNN.md)

## Último Reporte Mensual
→ [YYYY-MM](monthly/YYYY-MM.md)
```

### 10.8 Formato: Índice general (`index.md`)

```markdown
# AI Architect — Índice

> Última actualización: YYYY-MM-DD

## Navegación Rápida
- [Base de Conocimiento](master.md)
- [Matriz Competitiva](competitive/matrix-latest.md)

## Digests Diarios
| Fecha | Relevancia | Link |
|-------|-----------|------|
| YYYY-MM-DD | X/10 | [→](daily/YYYY-MM-DD.md) |

## Reportes Semanales
| Semana | Relevancia | Link |
|--------|-----------|------|
| YYYY-WNN | X/10 | [→](weekly/YYYY-WNN.md) |

## Reportes Mensuales
| Mes | Relevancia | Link |
|-----|-----------|------|
| YYYY-MM | X/10 | [→](monthly/YYYY-MM.md) |

## Temas
| Tema | Items | Link |
|------|-------|------|
| [topic] | N | [→](topics/topic.md) |
```

---

## 11. Infraestructura y Despliegue

### 11.1 Dockerfile principal

**Imagen base:** `python:3.11-slim` (soporta ARM64 nativamente).

**Dependencias de sistema:** `curl`, `git`, `ffmpeg` (para faster-whisper), Node.js (para Claude CLI).

**Componentes instalados:**
1. Claude Code CLI (vía script de instalación oficial)
2. faster-whisper (vía pip, con dependencias ONNX para ARM64)
3. Dependencias Python del proyecto

**Nota ARM64:** La instalación de Claude CLI en ARM64 requiere Node.js. El Dockerfile usa `node:lts-slim` como stage intermedio o instala Node.js directamente. Verificar que el script de instalación de Claude CLI soporte ARM64; si no, instalar vía npm global (`npm install -g @anthropic-ai/claude-code`).

### 11.2 docker-compose.yml

**Cambio respecto a v1:** Se elimina el contenedor separado de ChromaDB. Se usa ChromaDB embedded dentro del contenedor `app`. Esto simplifica el stack a un solo contenedor.

**Servicios:** Solo `app`.

**Volúmenes montados:**

| Volumen | Path contenedor | Modo | Propósito |
|---------|----------------|------|-----------|
| `~/.claude` | `/root/.claude` | ro | Sesión de Claude CLI del host |
| `./output` | `/app/output` | rw | Archivos Markdown de output |
| `./data` | `/app/data` | rw | ChromaDB, snapshots, transcripciones, estado |
| `./config.yaml` | `/app/config.yaml` | ro | Configuración |
| `./.env` | `/app/.env` | ro | Variables de entorno con API keys |

**Variables de entorno:**
- `TZ=Europe/Madrid`

### 11.3 requirements.txt (v2)

Dependencias organizadas por función:

**Collectors:**
- `arxiv>=2.0.0` — ArXiv API
- `feedparser>=6.0.0` — RSS parsing
- `google-api-python-client>=2.0.0` — YouTube Data API
- `youtube-transcript-api>=0.6.0` — Transcripciones YouTube
- `praw>=7.0.0` — Reddit API
- `httpx>=0.25.0` — HTTP async
- `beautifulsoup4>=4.12.0` — HTML parsing

**Procesamiento:**
- `pydantic>=2.0.0` — Schemas y validación
- `chromadb>=0.4.0` — Vector store embedded

**Transcripción (podcasts):**
- `faster-whisper>=0.10.0` — Transcripción de audio

**Utilidades:**
- `pyyaml>=6.0` — Config parsing
- `python-dateutil>=2.8.0` — Manejo de fechas

**No incluidas (instaladas a nivel de sistema):**
- Claude Code CLI (Node.js)
- ffmpeg (para faster-whisper)

### 11.4 config.yaml (v2 completo)

```yaml
# === GENERAL ===
schedule:
  timezone: "Europe/Madrid"
  daily_cron: "0 0 * * *"       # Medianoche
  weekly_day: "monday"           # Día de síntesis semanal
  monthly_day: 1                 # Día de síntesis mensual

notification:
  method: "ntfy"
  topic: "ai-architect"
  endpoint: "https://ntfy.sh"

# === MODELOS ===
models:
  analysis: "claude-sonnet-4-20250514"
  synthesis: "claude-opus-4-6"

processing:
  signal_threshold: 4            # Items con score < 4 se descartan
  batch_size: 10                 # Items por batch en Signal Ranker
  max_content_tokens: 15000      # Truncar contenido a este límite
  analyzer_timeout_seconds: 120
  max_retries: 2

# === FUENTES ===
docs:
  sources:
    - url: "https://docs.anthropic.com"
      name: "Anthropic Docs"
    - url: "https://github.com/anthropics/claude-code"
      name: "Claude Code Repo"
      sections: ["README.md", "CHANGELOG.md", "docs/"]

github_signals:
  repos:
    - "anthropics/claude-code"
    - "anthropics/anthropic-sdk-python"
    - "anthropics/anthropic-sdk-typescript"
  min_comments: 5
  min_pr_lines: 500
  min_discussion_replies: 3

github_repos:
  topics:
    - "claude"
    - "claude-code"
    - "mcp"
    - "anthropic"
    - "llm-agent"
    - "tool-use"
    - "computer-use"
    - "multi-agent"
  consolidated:
    min_stars: 100
    sort: "updated"
  emerging:
    max_stars: 100
    max_age_days: 14
    min_stars_velocity: 15       # Estrellas/día mínimo para considerar

blogs:
  willison:
    url: "https://simonwillison.net/atom/everything/"
  
  engineering:
    feeds:
      - url: "https://netflixtechblog.com/feed"
        name: "Netflix TechBlog"
      - url: "https://blog.cloudflare.com/tag/engineering/rss"
        name: "Cloudflare Engineering"
      - url: "https://dropbox.tech/feed"
        name: "Dropbox Tech"
      - url: "https://aws.amazon.com/blogs/machine-learning/feed"
        name: "AWS ML Blog"
      - url: "https://blog.anthropic.com/rss"
        name: "Anthropic Blog"
      - url: "https://developers.openai.com/blog/rss"
        name: "OpenAI Developer Blog"
  
  newsletters:
    feeds:
      - url: "https://importai.substack.com/feed"
        name: "Import AI"
      - url: "https://www.deeplearning.ai/the-batch/feed"
        name: "The Batch"
      - url: "https://aibreakfast.com/feed"
        name: "AI Breakfast"

podcasts:
  enabled: true
  whisper_model: "small"         # small = ~2GB RAM. Alternativa: tiny (~1GB)
  feeds:
    - url: "https://www.latent.space/feed"
      name: "Latent Space"
    - url: "https://practicalai.fm/rss"
      name: "Practical AI"
    - url: "https://www.cognitiverevolution.ai/feed"
      name: "The Cognitive Revolution"
  max_episode_age_days: 7        # Solo episodios de la última semana

packages:
  pypi:
    - "anthropic"
    - "anthropic-cli"
  npm:
    - "@anthropic-ai/sdk"
    - "@anthropic-ai/claude-code"
  keyword_search:
    - "mcp"
    - "claude"
  growth_threshold_pct: 50       # Alertar si >50% crecimiento semanal

stackoverflow:
  tags:
    - "claude-code"
    - "anthropic-api"
  search_queries:
    - "claude code"
    - "mcp server"
    - "anthropic sdk"
  pattern_threshold: 3           # N preguntas sobre mismo tema en 2 semanas = patrón

reddit:
  subreddits:
    - "LocalLLaMA"
    - "ClaudeAI"
    - "programming"
    - "MachineLearning"
  min_comments: 5
  sort: "hot"

hackernews:
  min_points_stories: 30
  include_ask_hn: true
  include_show_hn: true
  min_comments_show: 3

arxiv:
  categories:
    - "cs.CL"
    - "cs.SE"
    - "cs.AI"
    - "cs.HC"
    - "cs.CR"
  max_age_days: 7
  high_impact_authors: []        # Lista configurable de autores prioritarios

youtube:
  channels: []                   # IDs de canales (Anthropic oficial, etc.)
  max_per_channel: 5

jobs:
  hackernews_whos_hiring: true
  keywords:
    - "Claude Code"
    - "Claude API"
    - "MCP"
    - "Model Context Protocol"
    - "multi-agent"
    - "LLM agent"

conferences:
  urls:
    - url: "https://neurips.cc"
      name: "NeurIPS"
    - url: "https://iclr.cc"
      name: "ICLR"
    - url: "https://us.pycon.org"
      name: "PyCon US"

# === COMPETITIVO ===
competitive:
  competitors:
    - "Claude Code"
    - "GitHub Copilot"
    - "Cursor"
    - "Windsurf"
    - "Cline"
    - "Aider"
```

### 11.5 .env (v2)

```bash
# === APIs requeridas ===
GITHUB_TOKEN=ghp_xxx

# YouTube (solo si fuente 13 habilitada)
YOUTUBE_API_KEY=AIzaxxx

# Reddit
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT=ai-architect/2.0

# === Notificación ===
NTFY_TOPIC=ai-architect
```

### 11.6 Scheduler

**Cron del host (Jetson):**

```bash
# Pipeline diario completo — medianoche
0 0 * * * cd /home/jetson/developer/projects/ai-architect && docker compose run --rm app python main.py --mode daily >> /var/log/ai-architect/daily.log 2>&1

# Síntesis semanal — lunes a las 01:00 (tras el daily del domingo)
0 1 * * 1 cd /home/jetson/developer/projects/ai-architect && docker compose run --rm app python main.py --mode weekly >> /var/log/ai-architect/weekly.log 2>&1

# Síntesis mensual — día 1 a las 02:00
0 2 1 * * cd /home/jetson/developer/projects/ai-architect && docker compose run --rm app python main.py --mode monthly >> /var/log/ai-architect/monthly.log 2>&1

# Backup semanal de datos — domingo a las 03:00
0 3 * * 0 tar -czf /home/jetson/backups/ai-architect-$(date +\%Y\%m\%d).tar.gz /home/jetson/developer/projects/ai-architect/data/ >> /var/log/ai-architect/backup.log 2>&1
```

**Modos de ejecución de `main.py`:**

| Modo | Flag | Qué ejecuta |
|------|------|-------------|
| Daily | `--mode daily` | Fase 0 (podcasts) → Fase 1 (recolección) → Fase 2 (procesamiento) → Fase 3 (análisis) → Fase 4 (síntesis diaria) → Fase 5 (outputs) → Notificación |
| Weekly | `--mode weekly` | Lee 7 daily syntheses → Síntesis semanal → Competitive Mapper → Outputs semanales → Notificación |
| Monthly | `--mode monthly` | Lee weekly syntheses del mes → Síntesis mensual → Outputs mensuales → Notificación |
| Manual | `--mode manual --source github` | Ejecuta solo un collector específico (debug) |

### 11.7 APIs externas (v2)

| API | Uso | Coste | Auth | Rate Limit |
|-----|-----|-------|------|------------|
| Claude Code CLI | Análisis y síntesis | Suscripción existente | Session mount (~/.claude) | Depende de suscripción |
| GitHub REST API | Repos, Issues, PRs, Discussions | Gratis | Token (PAT) | 5.000 req/hora |
| ArXiv API | Papers académicos | Gratis | Ninguna | 3 req/segundo |
| YouTube Data API v3 | Búsqueda de videos | Gratis | API Key | 10.000 unidades/día |
| Reddit API (PRAW) | Posts y comentarios | Gratis | OAuth (client credentials) | 100 req/minuto |
| Hacker News API | Stories, Ask/Show HN | Gratis | Ninguna | Sin límite documentado |
| StackExchange API | Preguntas y respuestas | Gratis | Ninguna (o key opcional) | 300 req/día (sin key), 10.000/día (con key) |
| PyPI Stats API | Descargas semanales | Gratis | Ninguna | Sin límite documentado |
| npm Registry API | Descargas | Gratis | Ninguna | Sin límite documentado |
| ntfy.sh | Notificaciones push | Gratis | Ninguna | Sin límite práctico |

---

## 12. Fases de Implementación

### 12.1 Visión general

La implementación se divide en 4 fases que priorizan funcionalidad incremental: cada fase produce un sistema funcional que genera valor real, no un prototipo parcial.

| Fase | Duración | Objetivo | Resultado tangible |
|------|----------|----------|-------------------|
| 1 — Fundación | Semanas 1-2 | Pipeline mínimo funcional con 6 fuentes de alta prioridad | Digest diario generado automáticamente |
| 2 — Señal primaria | Semanas 3-4 | Añadir fuentes de señal primaria y comportamiento | Pipeline completo con 11 fuentes + síntesis semanal |
| 3 — Señal avanzada | Mes 2 | Fuentes restantes + competitive mapper + síntesis mensual | Sistema completo con 15 fuentes y 3 niveles de síntesis |
| 4 — Calibración | Mes 3 | Ajustar filtros, prompts y thresholds con datos reales | Sistema optimizado basado en métricas de operación |

### 12.2 Fase 1 — Fundación (Semanas 1-2)

**Objetivo:** Tener el pipeline mínimo funcional de extremo a extremo. Un ciclo que recolecta, procesa, analiza, sintetiza, genera Markdown, y notifica.

**Semana 1 — Infraestructura + Recolección:**

| Tarea | Detalle |
|-------|---------|
| Estructura de directorios | Crear `src/`, `output/`, `data/`, `config.yaml`, `.env` |
| Dockerfile + docker-compose | Imagen base con Python 3.11 + Claude CLI. Un solo servicio. |
| `config.py` + `logger.py` | Carga de config.yaml, logging estructurado |
| `claude_client.py` | Wrapper del CLI con retry, timeout, parsing de output |
| `base.py` (BaseCollector) | Interfaz base, manejo de errores, deduplicación |
| `docs.py` | Collector de docs oficiales con diff |
| `github_signals.py` | Issues/PRs de repos críticos |
| `github_emerging.py` | Repos emergentes <100★ |
| `github_repos.py` | Repos consolidados >100★ (migrado de v1) |
| `blogs.py` | Simon Willison + RSS genérico |
| `stackoverflow.py` | Preguntas por tags y búsqueda |

**Semana 2 — Procesamiento + Análisis + Output:**

| Tarea | Detalle |
|-------|---------|
| `signal_ranker.py` | Prompt unificado con Impact + Maturity en batches de 10 |
| `novelty_detector.py` | Búsqueda de similitud en ChromaDB |
| `vector_store.py` | ChromaDB embedded con 4 colecciones |
| `analyzer.py` | Análisis individual con Claude Sonnet |
| `synthesizer.py` | Síntesis diaria con Claude Opus |
| `markdown_gen.py` | Generación de daily digest + topics + master + index |
| `notifier.py` | Notificación vía ntfy.sh |
| `main.py` | Orquestador con modo `--mode daily` |
| Cron del host | Configurar ejecución diaria a medianoche |
| **Test end-to-end** | Ejecución completa del ciclo, verificar output |

**Entregable Fase 1:** El sistema corre diariamente y genera `output/daily/YYYY-MM-DD.md` con análisis de ~6 fuentes. Notificación push al completar.

### 12.3 Fase 2 — Señal primaria (Semanas 3-4)

**Objetivo:** Añadir las fuentes que aportan señal primaria, comportamiento y editorial. Activar síntesis semanal.

**Semana 3 — Nuevos collectors:**

| Tarea | Detalle |
|-------|---------|
| `podcasts.py` | Descarga RSS + transcripción faster-whisper. Fase 0 separada en main.py |
| `packages.py` | Tracking PyPI/npm con detección de anomalías de crecimiento |
| `jobs.py` | Scraping HN Who's Hiring con keywords |
| `reddit.py` | Migrar de v1 con nuevo filtro (ratio comentarios/votos) |
| `hackernews.py` | Migrar de v1 con nuevo filtro (Ask HN, Show HN, threshold bajado) |

**Semana 4 — Síntesis semanal + ajustes:**

| Tarea | Detalle |
|-------|---------|
| `newsletters` en `blogs.py` | Añadir Import AI, The Batch, AI Breakfast al RSS parser |
| Synthesizer semanal | Prompt semanal + schema WeeklySynthesis |
| `competitive_mapper.py` | Primera versión del competitive mapper |
| Formato semanal | `output/weekly/YYYY-WNN.md` |
| Modo `--mode weekly` en main.py | Orquestación semanal |
| Cron semanal | Lunes a las 01:00 |
| **Revisión de thresholds** | Evaluar signal_threshold, novelty_score, y calidad de prompts con datos de 2 semanas |

**Entregable Fase 2:** 11 fuentes activas. Digests diarios + reportes semanales. Competitive mapper genera primera matriz.

### 12.4 Fase 3 — Señal avanzada (Mes 2)

**Objetivo:** Completar todas las fuentes. Activar síntesis mensual. Sistema completo.

| Tarea | Detalle |
|-------|---------|
| `engineering_blogs.py` | Collector dedicado con clasificación por tipo de post |
| `arxiv.py` | Migrar de v1 con filtros corregidos (sin citas, <7 días, categorías ampliadas) |
| `youtube.py` | Migrar de v1 con transcripción vía youtube-transcript-api |
| `conferences.py` | Fetch de programas de conferencias |
| Synthesizer mensual | Prompt mensual + schema MonthlySynthesis |
| Formato mensual | `output/monthly/YYYY-MM.md` |
| Modo `--mode monthly` | Orquestación mensual |
| Cron mensual | Día 1 a las 02:00 |
| Backup automatizado | Cron semanal para tar de `data/` |
| **Test completo** | Verificar 15 fuentes, 3 niveles de síntesis, competitive mapper |

**Entregable Fase 3:** Sistema completo con 15 fuentes, síntesis diaria/semanal/mensual, competitive mapper, todos los formatos de output.

### 12.5 Fase 4 — Calibración (Mes 3)

**Objetivo:** Optimizar el sistema basándose en datos reales de operación.

| Tarea | Detalle |
|-------|---------|
| Análisis de descarte | ¿El signal_threshold=4 es correcto? ¿Se descartan items que deberían procesarse? |
| Calibración de novelty | ¿Los umbrales de distancia de ChromaDB producen novelty_scores útiles? |
| Calidad de prompts | Revisar samples de análisis y síntesis. ¿Los insights son accionables o genéricos? |
| Ajuste de filtros por fuente | ¿Algún collector produce demasiado ruido? ¿Alguno produce muy poco? |
| Performance | ¿El ciclo completa en tiempo razonable? ¿Hay cuellos de botella de memoria? |
| Refinamiento de config.yaml | Ajustar todos los parámetros configurables con datos de 1 mes |
| Documentar operaciones | Runbook con troubleshooting, FAQ, y procedimientos de mantenimiento |

**Entregable Fase 4:** Sistema calibrado con métricas de operación documentadas. config.yaml optimizado. Runbook de operaciones.

---

## 13. Monitorización y Operaciones

### 13.1 Logging

**Formato:** Logging estructurado con niveles estándar. Cada línea incluye timestamp, nivel, componente, y mensaje.

**Niveles por componente:**

| Componente | Nivel normal | Qué loguea |
|-----------|-------------|------------|
| Collectors | INFO | Items recolectados por fuente, duración |
| Collectors | WARNING | Items descartados por parse error, contenido vacío |
| Collectors | ERROR | Fuente no disponible, timeout, auth error |
| Signal Ranker | INFO | Items procesados, items descartados, scores |
| Analyzer | INFO | Items analizados, duración por item |
| Analyzer | ERROR | JSON inválido de Claude, timeout |
| Synthesizer | INFO | Síntesis generada, relevance score del día/semana |
| ChromaDB | INFO | Documentos almacenados, queries ejecutadas |
| Notifier | INFO | Notificación enviada |
| Notifier | ERROR | Fallo en envío de notificación |

**Destino:** `stdout` dentro del contenedor Docker → redirigido a `/var/log/ai-architect/` por el cron del host.

**Rotación de logs:** Configurar `logrotate` en el host para rotar logs semanalmente, retener 8 semanas.

### 13.2 Notificaciones

**Canal:** ntfy.sh (`https://ntfy.sh/ai-architect`)

**Mensajes por tipo de evento:**

| Evento | Prioridad ntfy | Formato del mensaje |
|--------|---------------|-------------------|
| Ciclo diario completado OK | default | `✅ AI Architect — YYYY-MM-DD\nItems: N analizados, K descartados\nRelevancia: X/10\nHighlight: [título]` |
| Ciclo completado con errores | high | `⚠️ AI Architect — YYYY-MM-DD\nItems: N analizados\n❌ Errores en: [collectors fallidos]` |
| Ciclo fallido completamente | urgent | `🔴 AI Architect FALLÓ — YYYY-MM-DD\n[error principal]` |
| Síntesis semanal completada | default | `📊 AI Architect Semanal — YYYY-WNN\nRelevancia: X/10\nPatrones: [lista breve]` |
| Síntesis mensual completada | default | `📈 AI Architect Mensual — YYYY-MM\nRelevancia: X/10` |
| Item con signal_score = 10 | high | `🚨 Señal crítica detectada\n[título]\n[fuente] — [url]` |

### 13.3 Métricas de operación

El sistema registra métricas en cada ejecución para detectar degradación y guiar la calibración (Fase 4).

**Schema:**

```python
class CycleMetrics(BaseModel):
    date: str
    mode: str                           # daily | weekly | monthly
    duration_seconds: int               # Duración total del ciclo
    phase_durations: dict[str, int]     # Duración por fase en segundos
    
    # Recolección
    items_collected: int
    items_by_source: dict[str, int]     # Conteo por source_type
    collection_errors: int
    collectors_failed: list[str]
    
    # Procesamiento
    items_processed: int
    items_discarded: int
    avg_signal_score: float
    avg_novelty_score: float
    signal_score_distribution: dict[int, int]  # {score: count}
    
    # Análisis
    items_analyzed: int
    analysis_errors: int
    avg_analysis_duration_seconds: float
    
    # Síntesis
    day_relevance_score: int
    synthesis_duration_seconds: int
    
    # Claude usage
    claude_calls_sonnet: int
    claude_calls_opus: int
    claude_errors: int
    
    # Storage
    chromadb_total_documents: int
    disk_usage_mb: float
```

**Almacenamiento:** Se escribe como JSON en `data/state/metrics/YYYY-MM-DD.json` tras cada ciclo.

**Uso:** Las métricas permiten responder preguntas como:
- ¿Cuánto tarda el ciclo y dónde está el cuello de botella?
- ¿Qué fuentes producen más ruido (items descartados)?
- ¿Qué fuentes fallan con más frecuencia?
- ¿La media de signal_score sube o baja con el tiempo (calidad de fuentes)?
- ¿ChromaDB crece dentro de lo esperado?

### 13.4 Manejo de errores — Estrategia global

**Principio:** Continúa y reporta. El sistema nunca aborta por un error parcial.

| Nivel de fallo | Comportamiento |
|----------------|---------------|
| Un collector falla | Registrar error → continuar con los demás → incluir en digest |
| Análisis de un item falla | Registrar error → saltar item → incluir error en digest |
| Signal Ranker falla (batch completo) | Registrar error → procesar items del batch sin ranking (signal_score=5 por defecto) → continuar |
| Síntesis diaria falla | Registrar error → generar digest sin sección de síntesis → notificar error |
| ChromaDB no disponible | Registrar error crítico → generar outputs solo en Markdown (sin vector store) → notificar urgente |
| Claude CLI no responde | Registrar error → retry con backoff → si persiste, abortar pipeline → notificar urgente |
| Disco lleno | Registrar error crítico → notificar urgente → abortar |

### 13.5 Mantenimiento rutinario

| Tarea | Frecuencia | Cómo |
|-------|-----------|------|
| Revisar logs de errores | Diaria (vía notificación) | Leer notificación push de ntfy |
| Revisar digest diario | Diaria | Abrir `output/daily/YYYY-MM-DD.md` |
| Backup de data/ | Semanal (automatizado) | Cron → `tar` de `data/` |
| Rotar logs | Semanal (automatizado) | logrotate configurado en host |
| Actualizar lista de repos críticos en config | Mensual (manual) | Editar `config.yaml` → `github_signals.repos` |
| Actualizar lista de paquetes monitorizados | Mensual (manual) | Editar `config.yaml` → `packages` |
| Calibrar thresholds | Trimestral (manual) | Analizar métricas de 3 meses → ajustar `config.yaml` |
| Actualizar dependencias Python | Trimestral (manual) | `pip install --upgrade` → rebuild Docker |
| Limpiar backups antiguos | Trimestral (manual) | Eliminar backups de >6 meses |

### 13.6 Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| No se generó digest | Cron no ejecutó | Verificar `crontab -l`, verificar logs en `/var/log/ai-architect/` |
| Digest sin items | Todos los collectors fallaron | Verificar conectividad de red, verificar API keys en `.env` |
| Signal scores todos bajos | Prompt de Signal Ranker desalineado | Revisar muestras, ajustar prompt o threshold |
| ChromaDB error on startup | Datos corruptos | Eliminar `data/chromadb/`, reconstruir (se pierden embeddings pero outputs Markdown persisten) |
| Claude CLI timeout | Rate limit de suscripción | Verificar plan de suscripción, reducir `batch_size` o `max_content_tokens` |
| Out of memory en Jetson | Procesos concurrentes | Verificar que las fases se ejecutan secuencialmente, no en paralelo |
| Podcast no se transcribe | ffmpeg faltante o whisper OOM | Verificar `ffmpeg` en Docker, probar modelo `whisper-tiny` en vez de `small` |
| Notificación no llega | ntfy topic incorrecto | Verificar `NTFY_TOPIC` en `.env`, verificar suscripción en app ntfy |

### 13.7 Consideraciones futuras (fuera de v2)

| Feature | Descripción | Complejidad |
|---------|-------------|-------------|
| Web UI | Interfaz para navegar el conocimiento acumulado. SPA con búsqueda semántica sobre ChromaDB. | Alta |
| API de consulta | Endpoint REST para hacer preguntas a la base de conocimiento. Útil para integraciones. | Media |
| Export | Generar PDFs o ebooks con contenido acumulado (mensual/trimestral). | Baja |
| Dashboard de métricas | Visualización web de `CycleMetrics` con tendencias. Grafana o similar. | Media |
| Twitter/X | Reactivar si aparece vía estable de acceso (API affordable o nuevo bridge funcional). | Depende de terceros |
| Discord/Slack | Integración con comunidades técnicas como fuente conversacional. Requiere tokens y permisos manuales. | Alta |
| Multi-hardware | Soporte para ejecución en cloud (AWS/GCP) además de Jetson. | Media |
| Auto-calibración | El sistema ajusta automáticamente thresholds basándose en feedback implícito (qué highlights se consultan más). | Alta |

---

*Fin del documento. Secciones 1-13 completas.*
