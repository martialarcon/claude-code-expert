# AI Architect v2 - Documentación Funcional

> Sistema automatizado de inteligencia técnica para el ecosistema Claude Code y desarrollo asistido por IA.

---

## Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Pipeline de Procesamiento](#pipeline-de-procesamiento)
5. [Fuentes de Datos (Collectors)](#fuentes-de-datos-collectors)
6. [Procesadores](#procesadores)
7. [Almacenamiento](#almacenamiento)
8. [Salidas Generadas](#salidas-generadas)
9. [Configuración](#configuración)
10. [Agents de Claude](#agents-de-claude)
11. [Skills Personalizados](#skills-personalizados)
12. [Notificaciones](#notificaciones)
13. [Tareas Comunes](#tareas-comunes)
14. [Solución de Problemas](#solución-de-problemas)

---

## Visión General

### ¿Qué es AI Architect v2?

AI Architect v2 es un **radar de inteligencia técnica** que recopila, analiza y sintetiza automáticamente información sobre Claude Code y el ecosistema de desarrollo asistido por IA. El sistema genera conocimiento estructurado en formato Markdown almacenado en ChromaDB para búsqueda semántica.

### Propósito

- **Monitorear** continuamente fuentes técnicas relevantes
- **Filtrar** información por relevancia y novedad
- **Analizar** contenido con modelos de lenguaje
- **Sintetizar** reportes estratégicos periódicos
- **Notificar** hallazgos importantes

### Características Principales

| Característica | Descripción |
|----------------|-------------|
| 8 Recolectores | Recopilación automática de docs, GitHub, blogs, StackOverflow, Reddit, HackerNews |
| Ranking Inteligente | Filtrado por señal con puntuación 1-10 |
| Detección de Novedad | Filtrado de duplicados mediante similitud vectorial |
| Análisis Profundo | Extracción de insights y accionabilidad |
| Síntesis Estratégica | Reportes diarios/semanales/mensuales |
| Notificaciones Push | Alertas móviles vía ntfy.sh |

---

## Arquitectura del Sistema

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI ARCHITECT V2                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌───────────┐ │
│  │  COLLECTORS │────▶│ PROCESSORS  │────▶│   STORAGE   │────▶│  OUTPUT   │ │
│  │ (8 fuentes) │     │  (4 etapas) │     │  (ChromaDB) │     │ (Markdown)│ │
│  └─────────────┘     └─────────────┘     └─────────────┘     └───────────┘ │
│        │                    │                   │                   │       │
│        │                    │                   │                   ▼       │
│        │                    │                   │            ┌───────────┐  │
│        │                    │                   │            │ NOTIFIER  │  │
│        │                    │                   │            │ (ntfy.sh) │  │
│        │                    │                   │            └───────────┘  │
│        ▼                    ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      CLAUDE API (GLM-5)                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Modos de Ejecución

| Modo | Frecuencia | Propósito |
|------|------------|-----------|
| `daily` | Diario | Digest de novedades del día |
| `weekly` | Semanal | Síntesis de patrones y tendencias |
| `monthly` | Mensual | Análisis estratégico de largo plazo |

---

## Componentes Principales

### Estructura de Directorios

```
claude-code-expert/
├── main.py                 # Punto de entrada
├── config.yaml             # Configuración central
├── requirements.txt        # Dependencias Python
├── docker-compose.yml      # Orquestación de contenedores
├── Dockerfile              # Imagen del contenedor
│
├── src/
│   ├── collectors/         # Módulos de recolección
│   │   ├── base.py         # Clase base abstracta
│   │   ├── docs.py         # Documentación oficial
│   │   ├── github_*.py     # Fuentes de GitHub
│   │   ├── blogs.py        # Feeds RSS
│   │   ├── stackoverflow.py # Preguntas técnicas
│   │   ├── reddit.py       # Discusiones Reddit
│   │   └── hackernews.py   # Noticias tech
│   │
│   ├── processors/         # Pipeline de procesamiento
│   │   ├── claude_client.py # Cliente API Claude
│   │   ├── signal_ranker.py # Ranking por señal
│   │   ├── novelty_detector.py # Detección de duplicados
│   │   ├── analyzer.py     # Análisis profundo
│   │   └── synthesizer.py  # Síntesis de reportes
│   │
│   ├── storage/            # Capa de persistencia
│   │   ├── vector_store.py # ChromaDB
│   │   └── markdown_gen.py # Generación Markdown
│   │
│   └── utils/              # Utilidades
│       ├── config.py       # Gestión de configuración
│       ├── logger.py       # Logging estructurado
│       └── notifier.py     # Notificaciones push
│
├── output/                 # Contenido generado
│   ├── daily/              # Digests diarios
│   ├── weekly/             # Reportes semanales
│   ├── monthly/            # Reportes mensuales
│   └── index.md            # Índice maestro
│
├── data/                   # Datos persistentes
│   ├── chromadb/           # Base vectorial
│   └── snapshots/          # Snapshots de docs
│
├── .claude/                # Configuración Claude Code
│   ├── agents/             # Subagentes personalizados
│   ├── skills/             # Skills personalizados
│   └── hooks/              # Hooks de validación
│
└── docs/
    └── plans/              # Documentación de diseño
```

---

## Pipeline de Procesamiento

### Etapas del Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  1. COLLECT  │───▶│  2. RANK     │───▶│  3. FILTER   │───▶│  4. ANALYZE  │───▶│  5. SYNTHESIZE│
│  Recolectar  │    │  Puntuar     │    │  Novelty     │    │  Profundizar │    │  Sintetizar   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      │                   │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼                   ▼
  Items crudos       Score 1-10        Duplicados          Insights +           Reportes
  de 8 fuentes       por señal         eliminados          Accionabilidad       Markdown
```

### Descripción de Cada Etapa

#### 1. Collection (Recolección)
- Ejecuta todos los collectors habilitados
- Normaliza los datos al formato `CollectedItem`
- Aplica deduplicación básica por ID
- Registra errores por collector

#### 2. Signal Ranking (Ranking por Señal)
- Cada item recibe puntuación de 1-10
- Filtra items por debajo del umbral mínimo (default: 4)
- Utiliza Claude para evaluación de relevancia

#### 3. Novelty Detection (Detección de Novedad)
- Compara cada item contra historial en ChromaDB
- Calcula similitud de coseno del embedding
- Filtra items con similitud > umbral (default: 0.7)

#### 4. Analysis (Análisis Profundo)
- Extrae insights específicos
- Identifica detalles técnicos
- Evalúa accionabilidad (high/medium/low)
- Determina relevancia para Claude

#### 5. Synthesis (Síntesis)
- Genera reportes agregados
- Identifica patrones y tendencias
- Calcula score de relevancia general
- Produce output Markdown

---

## Fuentes de Datos (Collectors)

### Visión General

Los collectors son módulos que implementan la clase `BaseCollector` y siguen el patrón fetch-parse.

### Fuentes Disponibles

| Collector | Tipo | Descripción | Requisitos |
|-----------|------|-------------|------------|
| `docs` | Oficial | Documentación Anthropic/Claude con diff | Ninguno |
| `github_signals` | Primario | Issues/PRs de repos críticos | GITHUB_TOKEN |
| `github_emerging` | Descubrimiento | Repos <100 estrellas con crecimiento | GITHUB_TOKEN |
| `github_repos` | Popular | Repos >100 estrellas en ecosistema AI | GITHUB_TOKEN |
| `blogs` | Editorial | Simon Willison, Anthropic blog, RSS | Ninguno |
| `stackoverflow` | Comportamiento | Preguntas taggeadas claude/anthropic | Ninguno |
| `reddit` | Comunidad | Discusiones en LocalLLaMA, ClaudeAI | Ninguno |
| `hackernews` | Noticias | Posts tech de alto engagement | Ninguno |

### Formato de Datos: CollectedItem

```python
@dataclass
class CollectedItem:
    # Identidad
    id: str                    # Hash único del contenido
    source_type: SourceType    # Tipo de fuente
    source_url: str            # URL original

    # Contenido
    title: str                 # Título del item
    content: str               # Texto completo
    summary: str | None        # Resumen (si disponible)

    # Metadatos
    author: str | None         # Autor/creador
    published_at: datetime     # Fecha publicación
    collected_at: datetime     # Fecha recolección
    metadata: dict             # Metadatos específicos

    # Estado de procesamiento
    signal_score: int | None   # Puntuación 1-10
    novelty_score: float | None # Similitud 0-1
    impact: str | None         # Clasificación de impacto
    maturity: str | None       # Estado de madurez
```

### Agregar un Nuevo Collector

1. Crear archivo en `src/collectors/nueva_fuente.py`
2. Heredar de `BaseCollector`
3. Implementar `_fetch()` y `_parse()`
4. Registrar en `main.py`

```python
from src.collectors.base import BaseCollector, CollectedItem, SourceType

class NuevaFuenteCollector(BaseCollector[RawType]):
    def __init__(self, config=None):
        super().__init__(SourceType.NUEVA_FUENTE, config)

    def _fetch(self) -> list[RawType]:
        # Obtener datos crudos de la fuente
        pass

    def _parse(self, raw: RawType) -> CollectedItem | None:
        # Convertir a CollectedItem
        pass
```

---

## Procesadores

### Signal Ranker

**Propósito:** Puntuar items por relevancia (1-10)

**Criterios de puntuación:**
- Impacto en flujos de trabajo existentes
- Novedad de la información
- Relevancia para Claude/Anthropic
- Accionabilidad inmediata

**Configuración:**
```yaml
thresholds:
  signal_score_min: 4    # Descartar items por debajo
  batch_size: 10         # Items por llamada API
```

### Novelty Detector

**Propósito:** Filtrar contenido duplicado o muy similar

**Funcionamiento:**
1. Genera embedding del item con ChromaDB
2. Busca items similares en historial
3. Si similitud > umbral, descarta el item

**Configuración:**
```yaml
thresholds:
  novelty_score_min: 0.3  # Mínimo para considerar novedoso
```

### Analyzer

**Propósito:** Análisis profundo de items individuales

**Salida (AnalysisResult):**
```python
@dataclass
class AnalysisResult:
    item_id: str
    summary: str              # Resumen 2-3 oraciones
    key_insights: list[str]   # 3-5 insights específicos
    technical_details: str    # Detalles técnicos o None
    relevance_to_claude: str  # Relación con Claude
    actionability: str        # high | medium | low
    related_topics: list[str] # Topics relacionados
    confidence: float         # 0.0 - 1.0
```

### Synthesizer

**Propósito:** Generar reportes agregados

**Modos:**
- **Daily:** Digest de novedades del día
- **Weekly:** Patrones y tendencias semanales
- **Monthly:** Análisis estratégico mensual

---

## Almacenamiento

### ChromaDB

**Propósito:** Base de datos vectorial para búsqueda semántica

**Colecciones:**
| Colección | Contenido |
|-----------|-----------|
| `items` | Items recolectados |
| `analysis` | Resultados de análisis |
| `synthesis` | Síntesis generadas |
| `snapshots` | Snapshots de documentación |

**Configuración:**
```yaml
storage:
  chromadb:
    persist_directory: "data/chromadb"
    collections:
      - "items"
      - "analysis"
      - "synthesis"
      - "snapshots"
```

### Markdown Output

**Ubicación:** `output/`

**Archivos generados:**
- `daily/YYYY-MM-DD.md` - Digest diario
- `weekly/YYYY-WW.md` - Reporte semanal
- `monthly/YYYY-MM.md` - Reporte mensual
- `index.md` - Índice maestro con enlaces

---

## Salidas Generadas

### Formato de Digest Diario

```markdown
# AI Architect Daily Digest - 2026-02-24

## Resumen
- Items analizados: 15
- Relevancia general: 7.5/10
- Collectors activos: 5/8

## Highlights

### [Título del Item Principal]
- **Fuente:** GitHub Signals
- **Score:** 9/10
- **Accionabilidad:** Alta

Descripción del item y por qué es importante...

## Insights Clave
1. Insight específico con detalles concretos
2. Otro insight con números y nombres

## Acciones Recomendadas
- [ ] Acción inmediata sugerida
- [ ] Otra acción a considerar
```

---

## Configuración

### Archivo Principal: config.yaml

```yaml
# Modelos de IA
models:
  provider: "anthropic"
  analysis: "glm-5"      # Modelo para análisis
  synthesis: "glm-5"     # Modelo para síntesis

# Umbrales de procesamiento
thresholds:
  signal_score_min: 4    # Mínimo para procesar
  novelty_score_min: 0.3 # Mínimo para considerar novedoso
  batch_size: 10         # Items por llamada API

# Modo de ejecución
mode: "daily"            # daily | weekly | monthly

# Collectors habilitados
collectors:
  docs:
    enabled: true
    sources:
      - "https://docs.anthropic.com"
    snapshot_dir: "data/snapshots"

  blogs:
    enabled: true
    feeds:
      - name: "Simon Willison"
        url: "https://simonwillison.net/atom/everything/"
    max_items: 20

  stackoverflow:
    enabled: true
    tags: ["claude", "anthropic", "llm"]
    min_score: 5
    max_items: 30

  reddit:
    enabled: true
    subreddits: ["LocalLLaMA", "ClaudeAI"]
    min_comments: 5
    max_items: 20

  hackernews:
    enabled: true
    min_points: 30
    min_comments: 3
    max_items: 20

# Almacenamiento
storage:
  chromadb:
    persist_directory: "data/chromadb"

# Salidas
output:
  daily_dir: "output/daily"
  weekly_dir: "output/weekly"
  monthly_dir: "output/monthly"
  index_file: "output/index.md"

# Notificaciones
notifications:
  ntfy:
    enabled: true
    topic: "ai-architect"
    url: "https://ntfy.sh"

# Logging
logging:
  level: "INFO"
  format: "json"
```

### Variables de Entorno (.env)

```bash
# API Keys
ANTHROPIC_API_KEY=tu_clave_aqui
GITHUB_TOKEN=tu_token_github  # Opcional

# Logging
LOG_LEVEL=INFO
```

---

## Agents de Claude

El proyecto incluye subagentes personalizados para tareas especializadas.

### Agents Disponibles

| Agent | Propósito | Ubicación |
|-------|-----------|-----------|
| `analyzer` | Análisis profundo de items | `.claude/agents/analyzer.md` |
| `ranker` | Ranking por señal | `.claude/agents/ranker.md` |
| `synthesizer` | Síntesis de reportes | `.claude/agents/synthesizer.md` |
| `competitive` | Análisis competitivo | `.claude/agents/competitive.md` |
| `edge-performance-analyzer` | Optimización Jetson | `.claude/agents/edge-performance-analyzer.md` |

### Agent Analyzer

**Propósito:** Realizar análisis comprehensivo de items individuales.

**Input:**
```json
{
  "id": "unique-identifier",
  "title": "Título del item",
  "source_type": "news|repo|blog|docs",
  "content": "Contenido completo...",
  "signal_score": 8
}
```

**Output:**
```json
{
  "summary": "2-3 oraciones de resumen",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "technical_details": {
    "technologies": ["tech1", "tech2"],
    "api_changes": "descripción de cambios"
  },
  "relevance_to_claude": "Relación con Claude",
  "actionability": "high|medium|low",
  "confidence": 0.85
}
```

---

## Skills Personalizados

### Skills Disponibles

| Skill | Invocación | Propósito |
|-------|------------|-----------|
| `runtime-test` | `/runtime-test <file.py>` | Ejecutar Python con GPU/CUDA en contenedor |
| `security-check` | `/security-check` | Validar políticas de seguridad |
| `jetson-context` | Automático | Contexto técnico Jetson para decisiones |

### Skill: runtime-test

Ejecuta código Python en el contenedor `project-runtime` con acceso completo a GPU/CUDA.

**Uso:**
```bash
/runtime-test src/test_inference.py
```

### Skill: security-check

Valida políticas de seguridad del proyecto antes de commits/PRs.

**Verifica:**
- No hay secrets hardcodeados
- Contenedores sin root
- Dependencias ARM64 compatibles
- Dockerfiles seguros

---

## Notificaciones

### Configuración ntfy.sh

El sistema envía notificaciones push a través de ntfy.sh.

**Habilitar:**
```yaml
notifications:
  ntfy:
    enabled: true
    topic: "ai-architect"
    url: "https://ntfy.sh"
```

**Suscribirse:**
```bash
# CLI
ntfy sub ai-architect

# Web
https://ntfy.sh/ai-architect
```

### Tipos de Notificaciones

| Evento | Contenido |
|--------|-----------|
| `daily_complete` | Digest completado con highlights |
| `daily_errors` | Errores en collectors |
| `weekly_complete` | Síntesis semanal lista |
| `monthly_complete` | Reporte mensual generado |
| `cycle_failed` | Error crítico en pipeline |

---

## Tareas Comunes

### Ejecutar Digest Diario

```bash
# Con Docker
docker compose exec app python main.py --mode daily

# Directo (con entorno configurado)
python main.py --mode daily
```

### Ejecutar con Verbosidad

```bash
python main.py --mode daily --verbose
```

### Ver Output Generado

```bash
# Digest de hoy
cat output/daily/$(date +%Y-%m-%d).md

# Índice maestro
cat output/index.md
```

### Habilitar/Deshabilitar Collector

Editar `config.yaml`:
```yaml
collectors:
  github_signals:
    enabled: true   # Cambiar a false para deshabilitar
```

### Agregar Nueva Fuente RSS

```yaml
collectors:
  blogs:
    feeds:
      - name: "Nueva Fuente"
        url: "https://ejemplo.com/feed.xml"
```

---

## Solución de Problemas

### Problemas Comunes

#### Error: "ANTHROPIC_API_KEY not set"

**Causa:** Variable de entorno no configurada.

**Solución:**
```bash
export ANTHROPIC_API_KEY=tu_clave
# O agregar a .env
echo "ANTHROPIC_API_KEY=tu_clave" >> .env
```

#### Collector devuelve 0 items

**Causas posibles:**
1. Collector deshabilitado en config
2. Sin conectividad a la fuente
3. Token de API requerido no configurado
4. Filtros muy restrictivos

**Diagnóstico:**
```bash
# Ver logs
docker compose logs app | grep "collector_failed"

# Ejecutar con verbose
python main.py --mode daily --verbose
```

#### Error de memoria en Jetson

**Causa:** Memoria compartida limitada (8GB).

**Solución:**
- Reducir `batch_size` en config
- Ejecutar en modo secuencial (por defecto)
- Limpiar datos antiguos de ChromaDB

### Logs Estructurados

El sistema usa logging JSON para facilitar análisis:

```json
{
  "timestamp": "2026-02-24T12:00:00Z",
  "level": "INFO",
  "message": "cycle_complete",
  "mode": "daily",
  "duration_seconds": 45,
  "items_analyzed": 15
}
```

---

## Métricas de Rendimiento

### Umbrales para Jetson Orin Nano

| Métrica | OK | Advertencia | Crítico |
|---------|-------|---------|----------|
| FPS | >=30 | 20-29 | <20 |
| Memoria GPU | <=3GB | 3-4GB | >4GB |
| CPU | <=50% | 50-75% | >75% |
| Temperatura | <=55°C | 55-60°C | >60°C |

---

## Roadmap

### Fase 2 (Semanas 3-4)
- [ ] Collector de podcasts con transcripción
- [ ] Tracking de paquetes (PyPI/npm)
- [ ] Collector de empleos (HN Who's Hiring)
- [ ] Síntesis semanal + mapper competitivo

### Fase 3 (Mes 2)
- [ ] Blogs de ingeniería (postmortems)
- [ ] Papers de ArXiv con filtros mejorados
- [ ] Transcripción de YouTube
- [ ] Tracking de programas de conferencias

### Fase 4 (Mes 3)
- [ ] Calibración de umbrales
- [ ] Optimización de prompts
- [ ] Tuning de rendimiento

---

*Documentación generada para AI Architect v2 - Febrero 2026*
