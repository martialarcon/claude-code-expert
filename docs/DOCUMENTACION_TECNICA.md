# AI Architect v2 - Documentación Técnica

> Arquitectura detallada, APIs, modelos de datos y decisiones de diseño del sistema.

---

## Tabla de Contenidos

1. [Visión General de Arquitectura](#visión-general-de-arquitectura)
2. [Diagrama de Arquitectura](#diagrama-de-arquitectura)
3. [Stack Tecnológico](#stack-tecnológico)
4. [Modelos de Datos](#modelos-de-datos)
5. [APIs Internas](#apis-internas)
6. [Diagramas de Secuencia](#diagramas-de-secuencia)
7. [Decisiones Arquitectónicas (ADRs)](#decisiones-arquitectónicas-adrs)
8. [Integración con Claude API](#integración-con-claude-api)
9. [Almacenamiento Vectorial](#almacenamiento-vectorial)
10. [Sistema de Logging](#sistema-de-logging)
11. [Consideraciones de Rendimiento](#consideraciones-de-rendimiento)
12. [Seguridad](#seguridad)
13. [Extensibilidad](#extensibilidad)

---

## Visión General de Arquitectura

### Principios de Diseño

| Principio | Descripción |
|-----------|-------------|
| **Secuencial por defecto** | Ejecución lineal para respetar límite de 8GB RAM |
| **Zero API cost** | Uso de proxy GLM para evitar costos de Anthropic |
| **Fallbacks robustos** | Cada componente tiene fallback cuando Claude falla |
| **Lazy loading** | Recursos cargados solo cuando se necesitan |
| **Singleton pattern** | Instancias únicas de clientes costosos |

### Restricciones del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    RESTRICCIONES                            │
├─────────────────────────────────────────────────────────────┤
│  Memoria:     8GB LPDDR5 compartida (CPU + GPU)             │
│  Arquitectura: ARM64 (aarch64)                              │
│  Ejecución:   Secuencial (no paralela)                      │
│  API Cost:    $0 (proxy GLM)                                │
│  Storage:     ChromaDB embedded (no servidor separado)      │
│  Runtime:     Docker con NVIDIA runtime                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Diagrama de Arquitectura

### Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AI ARCHITECT V2                                     │
│                        Sistema de Inteligencia Técnica                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           CAPA DE ENTRADA                                 │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │   │
│  │  │  Docs   │ │ GitHub  │ │  Blogs  │ │  SO     │ │ Reddit  │ │   HN    │ │   │
│  │  │Collector│ │Collector│ │Collector│ │Collector│ │Collector│ │Collector│ │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ │   │
│  │       │           │           │           │           │           │       │   │
│  │       └───────────┴───────────┴─────┬─────┴───────────┴───────────┘       │   │
│  │                                     ▼                                     │   │
│  │                          ┌─────────────────┐                              │   │
│  │                          │  CollectedItem  │                              │   │
│  │                          │   (Normalize)   │                              │   │
│  │                          └────────┬────────┘                              │   │
│  └───────────────────────────────────┼───────────────────────────────────────┘   │
│                                      │                                           │
│  ┌───────────────────────────────────┼───────────────────────────────────────┐   │
│  │                           CAPA DE PROCESAMIENTO                           │   │
│  │                                   │                                       │   │
│  │  ┌────────────────┐    ┌─────────┴─────────┐    ┌────────────────┐       │   │
│  │  │ Signal Ranker  │───▶│ Novelty Detector  │───▶│    Analyzer    │       │   │
│  │  │   (Claude)     │    │   (ChromaDB)      │    │   (Claude)     │       │   │
│  │  └───────┬────────┘    └───────────────────┘    └───────┬────────┘       │   │
│  │          │                                                │               │   │
│  │          │  Score 1-10 + Impact + Maturity               │               │   │
│  │          │  Filter < threshold                           │               │   │
│  │          │                                                │               │   │
│  │          ▼                                                ▼               │   │
│  │  ┌────────────────────────────────────────────────────────────────┐     │   │
│  │  │                      RankedItem + AnalysisResult               │     │   │
│  │  └────────────────────────────────────────────────────────────────┘     │   │
│  │                                    │                                     │   │
│  │                                    ▼                                     │   │
│  │                         ┌─────────────────┐                              │   │
│  │                         │   Synthesizer   │                              │   │
│  │                         │   (Claude)      │                              │   │
│  │                         └────────┬────────┘                              │   │
│  └──────────────────────────────────┼───────────────────────────────────────┘   │
│                                     │                                           │
│  ┌──────────────────────────────────┼───────────────────────────────────────┐   │
│  │                           CAPA DE SALIDA                                  │   │
│  │                                  │                                       │   │
│  │           ┌──────────────────────┼──────────────────────┐               │   │
│  │           ▼                      ▼                      ▼               │   │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │   │
│  │  │   ChromaDB      │   │    Markdown     │   │     ntfy.sh     │       │   │
│  │  │  (Vector Store) │   │   Generator     │   │   (Notifier)    │       │   │
│  │  └─────────────────┘   └─────────────────┘   └─────────────────┘       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      CAPA DE INFRAESTRUCTURA                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │   Claude    │  │   Config    │  │   Logger    │  │   Docker    │     │   │
│  │  │   Client    │  │  Manager    │  │  (JSON)     │  │ Compose     │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (Orchestrator)                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ AIArchitect                                                  ││
│  │ ├── run()                                                    ││
│  │ ├── _collect()    → List[CollectedItem]                     ││
│  │ ├── _process()    → List[CollectedItem]                     ││
│  │ ├── _analyze()    → List[(CollectedItem, AnalysisResult)]   ││
│  │ ├── _synthesize() → DailySynthesis | WeeklySynthesis | ...  ││
│  │ ├── _generate_output()                                       ││
│  │ └── _notify_complete()                                       ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │   Collectors  │ │   Processors  │ │    Storage    │
    ├───────────────┤ ├───────────────┤ ├───────────────┤
    │ BaseCollector │ │ SignalRanker  │ │ VectorStore   │
    │ ├─DocsColl.   │ │ NoveltyDetect.│ │ MarkdownGen   │
    │ ├─GitHubColl. │ │ Analyzer      │ └───────────────┘
    │ ├─BlogsColl.  │ │ Synthesizer   │
    │ ├─SOColl.     │ │ ClaudeClient  │
    │ ├─RedditColl. │ └───────────────┘
    │ └─HNColl.     │
    └───────────────┘
```

---

## Stack Tecnológico

### Dependencias Principales

```yaml
# requirements.txt
anthropic>=0.18.0        # SDK de Anthropic para Claude API
chromadb>=0.4.0          # Base de datos vectorial embedded
tenacity>=8.0.0          # Retry logic con backoff exponencial
pyyaml>=6.0              # Parser de configuración
feedparser>=6.0.0        # Parser de feeds RSS/Atom
requests>=2.28.0         # Cliente HTTP
python-dateutil>=2.8.0   # Manejo de fechas
pydantic>=2.0.0          # Validación de datos
structlog>=23.0.0        # Logging estructurado
```

### Configuración de Entorno

```yaml
# docker-compose.yml
services:
  app:
    build: .
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-https://api.anthropic.com}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./config.yaml:/app/config.yaml:ro
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          memory: 2G
```

### Versiones de Python y Plataformas

| Plataforma | Python | Arquitectura | Notas |
|------------|--------|--------------|-------|
| Jetson Orin Nano | 3.10+ | ARM64 | Producción |
| Desarrollo local | 3.12 | x86_64 | Desarrollo/Testing |
| Docker | 3.12-slim | Multi-arch | Contenedor |

---

## Modelos de Datos

### CollectedItem (Modelo Central)

```python
@dataclass
class CollectedItem:
    """
    Representación canónica de un item que fluye por el pipeline.

    Este es el contrato de datos unificado para todas las fuentes.
    """

    # ===== IDENTIDAD =====
    id: str                    # Hash único: SHA256(source:url:title)[:16]
    source_type: SourceType    # Enum del tipo de fuente
    source_url: str            # URL original del contenido

    # ===== CONTENIDO =====
    title: str                 # Título del item (requerido)
    content: str               # Texto completo del contenido
    summary: str | None        # Resumen si la fuente lo proporciona

    # ===== METADATOS =====
    author: str | None         # Autor/creador
    published_at: datetime | None  # Fecha de publicación original
    collected_at: datetime     # Timestamp de recolección (auto-generado)
    metadata: dict[str, Any]   # Metadatos específicos de la fuente

    # ===== ESTADO DE PROCESAMIENTO =====
    signal_score: int | None   # Puntuación 1-10 (asignado por SignalRanker)
    novelty_score: float | None # Similitud 0-1 (asignado por NoveltyDetector)
    impact: str | None         # Dimensión de impacto (asignado por ranker)
    maturity: str | None       # Nivel de madurez (asignado por ranker)
```

### SourceType (Enum de Fuentes)

```python
class SourceType(str, Enum):
    """Tipos de fuentes de datos soportadas."""
    # Fuentes activas (Fase 1-2)
    DOCS = "docs"
    GITHUB_SIGNALS = "github_signals"
    GITHUB_EMERGING = "github_emerging"
    GITHUB_REPOS = "github_repos"
    BLOGS = "blogs"
    STACKOVERFLOW = "stackoverflow"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"

    # Fuentes planificadas (Fase 3+)
    PODCASTS = "podcasts"
    PACKAGES = "packages"
    JOBS = "jobs"
    ENGINEERING_BLOGS = "engineering_blogs"
    ARXIV = "arxiv"
    YOUTUBE = "youtube"
    CONFERENCES = "conferences"
```

### CollectionResult

```python
@dataclass
class CollectionResult:
    """Resultado de una ejecución de collector."""
    source_type: SourceType
    items: list[CollectedItem]      # Items recolectados
    errors: list[str]               # Errores encontrados
    duration_seconds: float         # Tiempo de ejecución
    items_before_dedup: int         # Items antes de deduplicación
    items_deduplicated: int         # Items eliminados por duplicados

    @property
    def success(self) -> bool:
        """True si hay items O no hay errores críticos."""
        return len(self.items) > 0 or len(self.errors) == 0
```

### AnalysisResult

```python
@dataclass
class AnalysisResult:
    """Resultado del análisis profundo de un item."""
    item_id: str                    # ID del item analizado
    summary: str                    # Resumen de 2-3 oraciones
    key_insights: list[str]         # 3-5 insights específicos
    technical_details: str | None   # Detalles técnicos o None
    relevance_to_claude: str        # Relación con Claude/Anthropic
    actionability: str              # "high" | "medium" | "low"
    related_topics: list[str]       # Topics relacionados
    confidence: float               # 0.0 - 1.0
```

### RankedItem

```python
@dataclass
class RankedItem:
    """Item con puntuación de señal."""
    item: CollectedItem
    signal_score: int               # 1-10
    impact: str                     # tooling|architecture|research|production|ecosystem
    maturity: str                   # experimental|early|growing|stable|legacy
    reasoning: str | None           # Explicación de la puntuación
```

### Síntesis

```python
@dataclass
class DailySynthesis:
    """Síntesis diaria del ecosistema."""
    date: str                       # YYYY-MM-DD
    relevance_score: int            # 1-10
    highlights: list[str]           # 3-5 hallazgos principales
    patterns: list[str]             # Patrones identificados
    recommendations: list[str]      # Acciones recomendadas
    key_changes: list[str]          # Cambios notables
    summary: str                    # Resumen ejecutivo

@dataclass
class WeeklySynthesis:
    """Síntesis semanal estratégica."""
    week: str                       # YYYY-WNN
    relevance_score: int
    top_stories: list[dict[str, str]]
    trends: list[str]
    competitive_moves: list[str]
    emerging_technologies: list[str]
    recommendations: list[str]
    summary: str

@dataclass
class MonthlySynthesis:
    """Síntesis mensual de inteligencia."""
    month: str                      # YYYY-MM
    relevance_score: int
    major_developments: list[dict[str, str]]
    trend_analysis: str
    ecosystem_changes: list[str]
    competitive_landscape: str
    predictions: list[str]
    recommendations: list[str]
    summary: str
```

---

## APIs Internas

### BaseCollector (Clase Abstracta)

```python
class BaseCollector(ABC, Generic[T]):
    """
    Interfaz base para todos los collectors.

    Métodos abstractos que DEBEN implementar las subclases:
    """

    @abstractmethod
    def _fetch(self) -> list[T]:
        """
        Obtener datos crudos de la fuente.

        Returns:
            Lista de items en formato específico de la fuente

        Raises:
            CollectionError: Si la obtención falla
        """
        pass

    @abstractmethod
    def _parse(self, raw_item: T) -> CollectedItem | None:
        """
        Parsear item crudo a CollectedItem.

        Args:
            raw_item: Item en formato específico de la fuente

        Returns:
            CollectedItem o None si debe omitirse
        """
        pass

    # Métodos proporcionados por la clase base:
    def collect(self) -> CollectionResult:
        """Ejecutar proceso completo de recolección."""
        pass

    def validate(self, item: CollectedItem) -> bool:
        """Validar que el item tiene campos requeridos."""
        pass

    def _deduplicate(self, items: list[CollectedItem]) -> list[CollectedItem]:
        """Eliminar duplicados por ID."""
        pass
```

### SignalRanker API

```python
class SignalRanker:
    """
    Ranking de items por intensidad de señal.
    """

    def __init__(
        self,
        batch_size: int = 10,        # Items por llamada API
        signal_threshold: int = 4,   # Mínimo para pasar
        client: ClaudeClient | None = None,
    ): ...

    def rank_batch(self, items: list[CollectedItem]) -> list[RankedItem]:
        """
        Puntuar un lote de items.

        Args:
            items: Lista de items (<= batch_size)

        Returns:
            Lista de RankedItem con scores
        """
        pass

    def rank_all(self, items: list[CollectedItem]) -> list[RankedItem]:
        """
        Puntuar todos los items en lotes.

        Args:
            items: Todos los items a puntuar

        Returns:
            RankedItems filtrados por threshold
        """
        pass

    def apply_scores(self, ranked_items: list[RankedItem]) -> list[CollectedItem]:
        """
        Aplicar scores de vuelta a CollectedItems.

        Args:
            ranked_items: Items con scores

        Returns:
            CollectedItems con signal_score, impact, maturity asignados
        """
        pass
```

### NoveltyDetector API

```python
class NoveltyDetector:
    """
    Filtrado de duplicados mediante similitud vectorial.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.7,  # Umbral de similitud
        vector_store: VectorStore | None = None,
    ): ...

    def is_novel(self, item: CollectedItem) -> tuple[bool, float]:
        """
        Verificar si un item es novedoso.

        Args:
            item: Item a verificar

        Returns:
            (es_novedoso, score_similitud)
        """
        pass

    def filter_novel(self, items: list[CollectedItem]) -> list[CollectedItem]:
        """
        Filtrar items que no son novedosos.

        Args:
            items: Items a filtrar

        Returns:
            Solo items novedosos
        """
        pass
```

### Analyzer API

```python
class Analyzer:
    """
    Análisis profundo de items individuales.
    """

    def __init__(
        self,
        client: ClaudeClient | None = None,
        store_results: bool = True,
    ): ...

    def analyze(self, item: CollectedItem) -> AnalysisResult | None:
        """
        Analizar un item.

        Args:
            item: Item a analizar

        Returns:
            AnalysisResult o None si falla
        """
        pass

    def analyze_batch(
        self,
        items: list[CollectedItem],
    ) -> list[tuple[CollectedItem, AnalysisResult | None]]:
        """
        Analizar múltiples items secuencialmente.

        Args:
            items: Items a analizar

        Returns:
            Lista de (item, resultado) tuples
        """
        pass
```

### Synthesizer API

```python
class Synthesizer:
    """
    Generación de síntesis estratégicas.
    """

    def synthesize_daily(
        self,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
        date: str | None = None,
    ) -> DailySynthesis | None:
        """Generar síntesis diaria."""
        pass

    def synthesize_weekly(
        self,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
        week: str | None = None,
    ) -> WeeklySynthesis | None:
        """Generar síntesis semanal."""
        pass

    def synthesize_monthly(
        self,
        items: list[tuple[CollectedItem, AnalysisResult | None]],
        month: str | None = None,
    ) -> MonthlySynthesis | None:
        """Generar síntesis mensual."""
        pass
```

### VectorStore API

```python
class VectorStore:
    """
    Wrapper para ChromaDB en modo embedded.
    """

    def add(
        self,
        collection: str,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        """Agregar documentos a una colección."""
        pass

    def search(
        self,
        query: str,
        collection: str = "items",
        n_results: int = 5,
        where: dict | None = None,
    ) -> dict[str, Any]:
        """Búsqueda por similitud de texto."""
        pass

    def search_by_embedding(
        self,
        embedding: list[float],
        collection: str = "items",
        n_results: int = 5,
    ) -> dict[str, Any]:
        """Búsqueda por embedding directo."""
        pass

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Obtener embeddings para textos."""
        pass

    def count(self, collection: str) -> int:
        """Contar documentos en colección."""
        pass

    def get_stats(self) -> dict[str, int]:
        """Estadísticas de todas las colecciones."""
        pass
```

### ClaudeClient API

```python
class ClaudeClient:
    """
    Wrapper del SDK de Anthropic con retry y parsing JSON.
    """

    def __init__(
        self,
        model: ClaudeModel | None = None,
        timeout: int = 120,
        max_retries: int = 3,
        api_key: str | None = None,
        base_url: str | None = None,
    ): ...

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        expect_json: bool = False,
    ) -> ClaudeResponse:
        """
        Enviar petición de completado.

        Args:
            prompt: Prompt del usuario
            system: Prompt de sistema (opcional)
            max_tokens: Máximo tokens en respuesta
            expect_json: Si se espera JSON, parsear automáticamente

        Returns:
            ClaudeResponse con content y json_data (si aplica)

        Raises:
            ClaudeTimeoutError: Timeout de la petición
            ClaudeAPIError: Error de la API (retryable)
            ClaudeParseError: JSON esperado pero no parseable
        """
        pass

    def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        Completado con parsing JSON obligatorio.

        Raises:
            ClaudeParseError: Si no se puede parsear como JSON
        """
        pass
```

---

## Diagramas de Secuencia

### Flujo de Ejecución Diario Completo

```
┌────────┐     ┌────────────┐     ┌───────────┐     ┌─────────────┐     ┌───────────┐     ┌──────────┐
│ main() │     │ Collectors │     │  Ranker   │     │   Novelty   │     │ Analyzer  │     │Synthesizr│
└───┬────┘     └─────┬──────┘     └─────┬─────┘     └──────┬──────┘     └─────┬─────┘     └────┬─────┘
    │                │                  │                  │                  │                │
    │  run(mode="daily")               │                  │                  │                │
    │──────────────────────────────────────────────────────────────────────────────────────────>
    │                │                  │                  │                  │                │
    │                │  collect()       │                  │                  │                │
    │                │─────────────────>│                  │                  │                │
    │                │                  │                  │                  │                │
    │                │  CollectedItem[] │                  │                  │                │
    │<───────────────────────────────────────────────────────────────────────────────────────
    │                │                  │                  │                  │                │
    │  _process(items)                  │                  │                  │                │
    │─────────────────────────────────────────────────────────────────────────────────────────>
    │                │                  │                  │                  │                │
    │                │                  │  rank_all()      │                  │                │
    │                │                  │─────────────────>│                  │                │
    │                │                  │                  │                  │                │
    │                │                  │  RankedItem[]    │                  │                │
    │                │                  │<─────────────────│                  │                │
    │                │                  │                  │                  │                │
    │                │                  │                  │  filter_novel()  │                │
    │                │                  │                  │─────────────────>│                │
    │                │                  │                  │                  │                │
    │                │                  │                  │  CollectedItem[] │                │
    │                │                  │                  │<─────────────────│                │
    │                │                  │                  │                  │                │
    │  _analyze(items)                  │                  │                  │                │
    │─────────────────────────────────────────────────────────────────────────────────────────>
    │                │                  │                  │                  │                │
    │                │                  │                  │                  │  analyze()     │
    │                │                  │                  │                  │───────────────>│
    │                │                  │                  │                  │                │
    │                │                  │                  │                  │  AnalysisRes[] │
    │                │                  │                  │                  │<───────────────│
    │                │                  │                  │                  │                │
    │  _synthesize(analyzed)            │                  │                  │                │
    │─────────────────────────────────────────────────────────────────────────────────────────>
    │                │                  │                  │                  │                │
    │                │                  │                  │                  │                │
    │  DailySynthesis                   │                  │                  │                │
    │<───────────────────────────────────────────────────────────────────────────────────────
    │                │                  │                  │                  │                │
    ▼                ▼                  ▼                  ▼                  ▼                ▼
```

### Flujo de Llamada a Claude API

```
┌──────────────┐     ┌───────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Processor   │     │ ClaudeClient  │     │ Tenacity Retry  │     │  Anthropic   │
└──────┬───────┘     └───────┬───────┘     └────────┬────────┘     └──────┬───────┘
       │                     │                      │                     │
       │  complete(prompt,   │                      │                     │
       │          expect_json=True)                │                     │
       │────────────────────>│                      │                     │
       │                     │                      │                     │
       │                     │  _execute()          │                     │
       │                     │─────────────────────>│                     │
       │                     │                      │                     │
       │                     │                      │  POST /v1/messages  │
       │                     │                      │────────────────────>│
       │                     │                      │                     │
       │                     │                      │  200 OK + response  │
       │                     │                      │<────────────────────│
       │                     │                      │                     │
       │                     │  content (raw text)  │                     │
       │                     │<─────────────────────│                     │
       │                     │                      │                     │
       │                     │  _parse_json_from_content()                │
       │                     │──────────────────────│                     │
       │                     │                      │                     │
       │                     │  json_data: dict     │                     │
       │                     │<─────────────────────│                     │
       │                     │                      │                     │
       │  ClaudeResponse(    │                      │                     │
       │    content,         │                      │                     │
       │    json_data        │                      │                     │
       │  )                  │                      │                     │
       │<────────────────────│                      │                     │
       │                     │                      │                     │
       ▼                     ▼                      ▼                     ▼
```

### Flujo de Retry con Backoff Exponencial

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ ClaudeClient │     │ Tenacity Retry  │     │  Anthropic   │
└──────┬───────┘     └────────┬────────┘     └──────┬───────┘
       │                      │                     │
       │  _execute()          │                     │
       │─────────────────────>│                     │
       │                      │                     │
       │                      │  Attempt 1          │
       │                      │────────────────────>│
       │                      │                     │
       │                      │  429 Rate Limit     │
       │                      │<────────────────────│
       │                      │                     │
       │                      │  Wait 4s (2^2)      │
       │                      │─────────────────────│
       │                      │                     │
       │                      │  Attempt 2          │
       │                      │────────────────────>│
       │                      │                     │
       │                      │  200 OK             │
       │                      │<────────────────────│
       │                      │                     │
       │  content             │                     │
       │<─────────────────────│                     │
       │                      │                     │
       ▼                      ▼                     ▼

Retry Configuration:
- stop_after_attempt(3)
- wait_exponential(multiplier=1, min=4, max=60)
- retry_on: ClaudeAPIError (rate limit, overload)
```

---

## Decisiones Arquitectónicas (ADRs)

### ADR-001: Ejecución Secuencial

**Estado:** Aceptado

**Contexto:**
El sistema debe operar en Jetson Orin Nano con 8GB de RAM compartida entre CPU y GPU.

**Decisión:**
Ejecutar el pipeline de forma secuencial en lugar de paralela.

**Consecuencias:**
- ✅ Uso de memoria predecible y bajo
- ✅ Sin race conditions ni sincronización compleja
- ✅ Debugging más sencillo
- ❌ Mayor tiempo de ejecución total
- ❌ No aprovecha paralelismo de GPU para cómputo

**Alternativas Consideradas:**
1. **Paralelismo con asyncio** - Rechazado por complejidad de gestión de memoria
2. **Multiprocessing** - Rechazado por overhead de procesos en ARM64
3. **GPU batching** - Planificado para Fase 3 con optimizaciones

---

### ADR-002: ChromaDB Embedded Mode

**Estado:** Aceptado

**Contexto:**
Necesidad de almacenamiento vectorial para detección de novedad y búsqueda semántica.

**Decisión:**
Usar ChromaDB en modo embedded (PersistentClient) sin servidor separado.

**Consecuencias:**
- ✅ Sin dependencia de servidor externo
- ✅ Persistencia en disco local
- ✅ Compatible con ARM64
- ✅ Setup simplificado
- ❌ No escalable horizontalmente
- ❌ Procesamiento de embeddings en CPU

**Alternativas Consideradas:**
1. **Pinecone** - Rechazado por costo y dependencia de red
2. **Milvus standalone** - Rechazado por requisitos de memoria
3. **Qdrant** - Alternativa válida, ChromaDB elegido por simplicidad

---

### ADR-003: Proxy GLM para Claude API

**Estado:** Aceptado

**Contexto:**
Política de "Zero API Cost" - evitar costos de Anthropic API.

**Decisión:**
Configurar `ANTHROPIC_BASE_URL` para apuntar a proxy GLM compatible con la API de Anthropic.

**Consecuencias:**
- ✅ Costo $0 en llamadas API
- ✅ Compatibilidad total con SDK de Anthropic
- ✅ Fallback fácil a API real si es necesario
- ⚠️ Latencia potencialmente diferente
- ⚠️ Capacidades del modelo pueden variar

**Implementación:**
```bash
export ANTHROPIC_API_KEY="glm-proxy-key"
export ANTHROPIC_BASE_URL="https://glm-proxy.example.com"
```

---

### ADR-004: Patrón Singleton para Clientes Costosos

**Estado:** Aceptado

**Contexto:**
Múltiples componentes necesitan acceso a ClaudeClient y VectorStore.

**Decisión:**
Implementar patrón Singleton con lazy initialization para clientes costosos.

**Consecuencias:**
- ✅ Una sola instancia de cada cliente
- ✅ Inicialización solo cuando se necesita
- ✅ Menor uso de memoria
- ❌ Estado compartido requiere cuidado en tests

**Implementación:**
```python
# Patrón utilizado
_vector_store: VectorStore | None = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
```

---

### ADR-005: Fallbacks en Cada Etapa

**Estado:** Aceptado

**Contexto:**
El sistema debe continuar operando incluso si Claude API falla.

**Decisión:**
Cada componente que depende de Claude debe tener un fallback determinístico.

**Consecuencias:**
- ✅ Resiliencia ante fallos de API
- ✅ Sistema siempre produce output
- ✅ Degradación graceful
- ❌ Calidad reducida en modo fallback

**Implementación:**
```python
class SignalRanker:
    def rank_batch(self, items):
        try:
            return self._rank_with_claude(items)
        except ClaudeClientError:
            return self._fallback_rank(items)  # Heurística simple
```

---

### ADR-006: JSON Logging Estructurado

**Estado:** Aceptado

**Contexto:**
Necesidad de observabilidad y debugging en producción.

**Decisión:**
Usar structlog para logging JSON estructurado con campos consistentes.

**Consecuencias:**
- ✅ Logs parseables por herramientas
- ✅ Correlación de eventos por trace_id
- ✅ Búsqueda eficiente
- ❌ Logs más verbosos en texto plano

**Formato de Log:**
```json
{
  "timestamp": "2026-02-24T12:00:00Z",
  "level": "INFO",
  "logger": "processor.analyzer",
  "message": "analysis_complete",
  "item_id": "docs_abc123",
  "actionability": "high",
  "confidence": 0.85
}
```

---

## Integración con Claude API

### Configuración del Cliente

```python
class ClaudeClient:
    """
    Wrapper del SDK de Anthropic.

    Soporta:
    - Base URL personalizada (proxy GLM)
    - Retry con backoff exponencial
    - Parsing automático de JSON
    - Timeouts configurables
    """

    def __init__(
        self,
        model: ClaudeModel = ClaudeModel.SONNET,
        timeout: int = 120,
        max_retries: int = 3,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        # Obtener credenciales de entorno
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")

        # Configurar cliente
        client_kwargs = {
            "api_key": self._api_key,
            "timeout": self.timeout,
        }
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        self._client = Anthropic(**client_kwargs)
```

### Modelos Disponibles

```python
class ClaudeModel(str, Enum):
    SONNET = "claude-sonnet-4-20250514"  # Análisis rápido
    OPUS = "claude-opus-4-6"              # Síntesis profunda
    GLM_5 = "glm-5"                       # Proxy GLM
    GLM_4_FLASH = "glm-4-flash"           # Proxy GLM rápido
```

### Uso por Componente

| Componente | Modelo | Propósito |
|------------|--------|-----------|
| SignalRanker | GLM-5 | Evaluación rápida de señal |
| Analyzer | GLM-5 | Análisis profundo de items |
| Synthesizer | GLM-5 | Síntesis estratégica |

### Rate Limiting y Retry

```python
@retry(
    retry=retry_if_exception_type(ClaudeAPIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=True,
)
def _execute(self, prompt: str, system: str | None, max_tokens: int) -> str:
    """
    Ejecutar petición con retry automático.

    Retry en:
    - Rate limit (429)
    - Overload (529)
    - Errores temporales (500-504)
    """
    pass
```

---

## Almacenamiento Vectorial

### Arquitectura ChromaDB

```
┌─────────────────────────────────────────────────────────────┐
│                    ChromaDB (Embedded)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   items     │  │  analysis   │  │  synthesis  │          │
│  │  collection │  │  collection │  │  collection │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         ▼                ▼                ▼                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Default Embedding Function              │   │
│  │           (all-MiniLM-L6-v2 o similar)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 HNSW Index (L2 space)                │   │
│  │           Approximate Nearest Neighbor               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Persist Directory: data/chromadb/                          │
└─────────────────────────────────────────────────────────────┘
```

### Colecciones

| Colección | Contenido | Uso Principal |
|-----------|-----------|---------------|
| `items` | Items recolectados | Deduplicación, búsqueda |
| `analysis` | Resultados de análisis | Búsqueda de insights |
| `synthesis` | Síntesis generadas | Histórico de reportes |
| `snapshots` | Snapshots de docs | Diff de documentación |

### Operaciones Principales

```python
# Agregar documento
vector_store.add(
    collection="items",
    documents=["Contenido del item..."],
    ids=["item_abc123"],
    metadatas=[{"source": "github", "score": 8}]
)

# Búsqueda por similitud
results = vector_store.search(
    query="nueva feature de Claude",
    collection="items",
    n_results=5,
    where={"source": "docs"}  # Filtro opcional
)

# Búsqueda por embedding (para detección de novedad)
embedding = vector_store.get_embeddings([item.content])[0]
similar = vector_store.search_by_embedding(
    embedding=embedding,
    collection="items",
    n_results=1
)
```

---

## Sistema de Logging

### Configuración

```python
# src/utils/logger.py
import structlog

def configure_logging(level: str = "INFO"):
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### Uso

```python
from src.utils.logger import get_logger

log = get_logger("collector.github")

# Log con campos estructurados
log.info(
    "collection_complete",
    source_type="github_signals",
    items=15,
    duration_seconds=2.5,
)

# Log de error
log.error(
    "api_error",
    endpoint="/repos/owner/repo",
    status_code=429,
    error="Rate limit exceeded",
)
```

### Niveles

| Nivel | Uso |
|-------|-----|
| DEBUG | Detalles de ejecución (verbose) |
| INFO | Eventos normales de negocio |
| WARNING | Problemas recuperables |
| ERROR | Errores que afectan operación |

---

## Consideraciones de Rendimiento

### Métricas Objetivo

| Métrica | Target | Límite |
|---------|--------|--------|
| Tiempo de ciclo diario | <5 min | <10 min |
| Memoria pico | <4 GB | <6 GB |
| Items procesados/hora | >100 | - |
| Latencia Claude API | <30s | <60s |

### Optimizaciones Implementadas

```python
# 1. Lazy loading de recursos costosos
@property
def vector_store(self):
    if self._vector_store is None:
        self._vector_store = get_vector_store()
    return self._vector_store

# 2. Singleton para clientes
_vector_store: VectorStore | None = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

# 3. Procesamiento por lotes
BATCH_SIZE = 10  # Items por llamada API

# 4. Límite de contenido
content=item.content[:4000]  # Truncar para evitar tokens excesivos

# 5. Fallback sin API
def _fallback_rank(self, items):
    # Heurística simple sin llamada a Claude
    pass
```

### Cuellos de Botella Conocidos

| Cuello de Botella | Mitigación |
|-------------------|------------|
| Latencia API Claude | Batching, timeouts, fallbacks |
| Memoria ChromaDB | Limpieza periódica, límite de colecciones |
| Network I/O | Timeouts agresivos, retry con backoff |

---

## Seguridad

### Variables de Entorno

```bash
# Requerido
ANTHROPIC_API_KEY=tu_clave_aqui

# Opcional
ANTHROPIC_BASE_URL=https://proxy.example.com
GITHUB_TOKEN=ghp_xxxx  # Para GitHub API
LOG_LEVEL=INFO
```

### Política de Secrets

- ❌ Nunca commitear `.env` o secrets
- ✅ Usar variables de entorno
- ✅ Docker secrets en producción
- ✅ Validar ausencia de secrets en hooks

### Permisos de Contenedor

```yaml
# docker-compose.yml
services:
  app:
    read_only: false
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

---

## Extensibilidad

### Agregar Nuevo Collector

1. Crear archivo en `src/collectors/nueva_fuente.py`:

```python
from .base import BaseCollector, CollectedItem, SourceType

class NuevaFuenteCollector(BaseCollector[RawType]):
    def __init__(self, config: dict | None = None):
        super().__init__(SourceType.NUEVA_FUENTE, config)

    def _fetch(self) -> list[RawType]:
        # Obtener datos de la fuente
        response = requests.get("https://api.fuente.com/data")
        return response.json()["items"]

    def _parse(self, raw: RawType) -> CollectedItem | None:
        return CollectedItem(
            id=self._compute_id(raw),
            source_type=SourceType.NUEVA_FUENTE,
            source_url=raw["url"],
            title=raw["title"],
            content=raw["content"],
            published_at=parse_date(raw["date"]),
        )
```

2. Registrar en `main.py`:

```python
collectors = [
    # ...
    ("nueva_fuente", collect_nueva_fuente),
]
```

3. Agregar configuración en `config.yaml`:

```yaml
collectors:
  nueva_fuente:
    enabled: true
    api_url: "https://api.fuente.com"
    max_items: 20
```

### Agregar Nueva Dimensión de Impacto

```python
# src/processors/signal_ranker.py
IMPACT_DIMENSIONS = [
    "tooling",
    "architecture",
    "research",
    "production",
    "ecosystem",
    "nueva_dimension",  # Agregar aquí
]
```

### Agregar Nuevo Tipo de Síntesis

1. Crear dataclass:

```python
@dataclass
class QuarterlySynthesis:
    quarter: str
    relevance_score: int
    # ... campos específicos
```

2. Agregar prompt template:

```python
QUARTERLY_SYNTHESIS_PROMPT = """..."""
```

3. Implementar método en Synthesizer:

```python
def synthesize_quarterly(self, items, quarter=None) -> QuarterlySynthesis:
    # ...
```

---

## Referencias

- [Documentación Funcional](./DOCUMENTACION_FUNCIONAL.md)
- [CLAUDE.md - Configuración del Proyecto](../CLAUDE.md)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Anthropic API Reference](https://docs.anthropic.com/)

---

*Documentación técnica generada para AI Architect v2 - Febrero 2026*
