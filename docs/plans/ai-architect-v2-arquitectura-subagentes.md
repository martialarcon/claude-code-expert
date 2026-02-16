# AI Architect v2 — Arquitectura de Subagentes Claude Code

**Versión:** 1.0  
**Fecha:** 2026-02-16  
**Estado:** Aprobado para implementación  
**Documento complementario a:** `ai-architect-v2-planificacion-tecnica.md`  
**Hardware objetivo:** NVIDIA Jetson Orin Nano (ARM64, 8GB RAM)

---

## Índice

1. [Decisión Arquitectónica](#1-decisión-arquitectónica)
2. [Modelo de Ejecución](#2-modelo-de-ejecución)
3. [Estructura de Archivos de Agentes](#3-estructura-de-archivos-de-agentes)
4. [Inventario de Agentes](#4-inventario-de-agentes)
5. [Agente: Signal Ranker](#5-agente-signal-ranker)
6. [Agente: Analyzer](#6-agente-analyzer)
7. [Agente: Synthesizer](#7-agente-synthesizer)
8. [Agente: Competitive Mapper](#8-agente-competitive-mapper)
9. [Integración con el Orquestador Python](#9-integración-con-el-orquestador-python)
10. [Gestión de Errores en Subagentes](#10-gestión-de-errores-en-subagentes)
11. [Restricciones de Hardware y Ejecución](#11-restricciones-de-hardware-y-ejecución)
12. [Validación y Testing de Agentes](#12-validación-y-testing-de-agentes)
13. [Relación con los Documentos Existentes](#13-relación-con-los-documentos-existentes)

---

## 1. Decisión Arquitectónica

### 1.1 Qué cambia respecto a la planificación técnica original

La planificación técnica (`ai-architect-v2-planificacion-tecnica.md`) define las tareas de análisis como llamadas directas a Claude CLI con prompts estáticos:

```python
# Diseño original: prompt estático vía subprocess
result = subprocess.run(
    ["claude", "-p", prompt, "--model", model],
    capture_output=True, text=True, timeout=300
)
```

Este documento introduce **subagentes especializados de Claude Code** para las tareas de juicio. En lugar de pasar un prompt inline, el orquestador Python invoca un agente predefinido que ya tiene contexto sobre su rol, criterios de evaluación, y formato de output esperado.

```python
# Nuevo diseño: invocación de subagente con contexto predefinido
result = subprocess.run(
    ["claude", "-p", prompt_con_datos, "--agent", "agent-ranker"],
    capture_output=True, text=True, timeout=300
)
```

### 1.2 Qué NO cambia

Este documento no modifica ninguna de las siguientes decisiones de la planificación técnica:

- **Orquestador Python.** `main.py` sigue controlando el pipeline completo: orden de ejecución, gestión de memoria, scheduling, manejo de errores a nivel de sistema.
- **Recolectores en Python puro.** Los 15 collectors (`src/collectors/`) siguen siendo código Python determinista. No se crean agentes para recolección.
- **Schemas Pydantic.** Los modelos `CollectedItem`, `ProcessedItem`, `AnalyzedItem`, `DailySynthesis`, `WeeklySynthesis`, `MonthlySynthesis`, `CompetitiveMatrix` y todos sus submodelos permanecen exactamente como están definidos en la planificación técnica.
- **Ejecución secuencial.** Por restricción de hardware (8GB RAM), todo se ejecuta secuencialmente. No se lanzan múltiples agentes en paralelo.
- **ChromaDB embedded.** El vector store sigue operando en modo embedded dentro del proceso Python.
- **Estructura de directorios de output.** `output/daily/`, `output/weekly/`, `output/monthly/`, `output/competitive/` no cambian.
- **Notificaciones vía ntfy.sh.** Sin cambios.
- **Fases de implementación.** Las 4 fases y su roadmap siguen como están. Los agentes se crean dentro de las tareas ya definidas.

### 1.3 Por qué subagentes y no prompts estáticos

**Separación de responsabilidades.** Los prompts definidos en la planificación técnica mezclan dos cosas: instrucciones de rol (quién eres, qué criterios usas) y datos del ciclo actual (items a evaluar). Un subagente separa estas dos capas. Las instrucciones de rol viven en el archivo del agente; los datos se pasan como input en cada invocación.

**Mantenibilidad.** Modificar el comportamiento de un agente (por ejemplo, ajustar los criterios de scoring del ranker) requiere editar un solo archivo `.md`, no buscar y modificar strings de prompt dentro de código Python.

**Testabilidad.** Cada agente puede invocarse de forma independiente desde la línea de comandos para verificar su comportamiento con datos de prueba, sin necesidad de ejecutar el pipeline completo.

**Consistencia.** El agente recibe sus instrucciones de rol completas en cada invocación, eliminando el riesgo de que un cambio en el código Python altere accidentalmente el prompt.

### 1.4 Por qué subagentes y no skills

Los skills de Claude Code son archivos `SKILL.md` que definen cómo realizar un tipo de trabajo, con posibilidad de usar herramientas y subagentes propios. Se descartaron para el pipeline de análisis por tres razones:

1. **Control de ejecución.** Un skill puede decidir qué herramientas usar y en qué orden. En un sistema desatendido que corre a medianoche en un cron, necesitamos que el output sea predecible. Los subagentes reciben datos y devuelven un JSON; no toman decisiones sobre el flujo.

2. **Restricción de hardware.** El modo agéntico con tools implica que Claude Code mantiene un proceso más largo con múltiples tool calls encadenados. En el Jetson con 8GB de RAM, esto no es viable de forma fiable. Los subagentes ejecutan una sola tarea y terminan.

3. **Simplicidad.** El pipeline ya tiene un orquestador Python que controla el flujo. Añadir skills con su propio flujo agéntico crearía dos niveles de orquestación compitiendo.

Los skills sí se consideran útiles para la **Fase 4 de calibración**: el ciclo eval/improve del skill-creator puede usarse para optimizar los prompts de los agentes con datos reales. Pero eso es un proceso de desarrollo, no de ejecución en producción.

---

## 2. Modelo de Ejecución

### 2.1 Flujo general con subagentes

El flujo de datos definido en la sección 2.3 de la planificación técnica se mantiene. Lo que cambia es la implementación interna de las etapas que requieren juicio LLM.

```
Fase 0: Transcripción de podcasts (Python puro, faster-whisper)
    ↓
Fase 1: Recolección (Python puro, 15 collectors)
    ↓
Fase 2: Procesamiento
    ├── Signal Ranker ──────── @agent-ranker (Claude Sonnet, batches de 10)
    ├── Novelty Detector ───── Python puro (consulta ChromaDB, calcula similitud)
    ├── Impact Classifier ──── Integrado en @agent-ranker (mismo prompt, mismo batch)
    ├── Maturity Classifier ── Integrado en @agent-ranker (mismo prompt, mismo batch)
    └── Analyzer ───────────── @agent-analyzer (Claude Sonnet, item por item)
    ↓
Fase 3: Almacenamiento (Python puro, ChromaDB + disco)
    ↓
Fase 4: Síntesis
    ├── Síntesis diaria ────── @agent-synthesizer --mode daily (Claude Opus)
    ├── Síntesis semanal ───── @agent-synthesizer --mode weekly (Claude Opus, domingos)
    ├── Síntesis mensual ───── @agent-synthesizer --mode monthly (Claude Opus, fin de mes)
    └── Competitive Mapper ─── @agent-competitive (Claude Opus, semanal)
    ↓
Fase 5: Generación Markdown + Notificación (Python puro)
```

### 2.2 Qué etapas usan agentes y cuáles no

| Etapa | ¿Usa agente? | Justificación |
|-------|-------------|---------------|
| Recolección (15 fuentes) | No | Determinista. Llamadas a APIs, parsing, deduplicación. Un agente no aporta nada aquí. |
| Signal Ranker | Sí (`@agent-ranker`) | Requiere juicio: evaluar profundidad técnica, impacto potencial, evidencia práctica. |
| Impact Classifier | Sí (integrado en `@agent-ranker`) | Se resuelve en el mismo prompt batch que el ranking, como ya define la planificación técnica. |
| Maturity Classifier | Sí (integrado en `@agent-ranker`) | Ídem: mismo prompt batch, misma llamada. |
| Novelty Detector | No | Es una consulta de similitud coseno contra ChromaDB. Determinista. |
| Analyzer | Sí (`@agent-analyzer`) | Requiere juicio profundo: generar insights, implicaciones arquitectónicas, notas competitivas. |
| Síntesis (daily/weekly/monthly) | Sí (`@agent-synthesizer`) | Requiere juicio estratégico: detectar tendencias, conectar patrones, generar recomendaciones. |
| Competitive Mapper | Sí (`@agent-competitive`) | Requiere conocimiento de dominio especializado sobre el panorama competitivo. |
| Almacenamiento en ChromaDB | No | Operación CRUD determinista. |
| Generación Markdown | No | Plantillas + datos estructurados. Determinista. |
| Notificación | No | Llamada HTTP a ntfy.sh. Determinista. |

### 2.3 Secuencia de ejecución de agentes dentro del pipeline

Dentro de una ejecución diaria, los agentes se invocan en este orden estricto. No hay paralelismo.

```
1. @agent-ranker      × 10-15 invocaciones (batches de 10 items)
       ↓
2. Novelty Detector   × N items (Python, no agente)
       ↓
3. @agent-analyzer    × 60-100 invocaciones (un item por invocación)
       ↓
4. Almacenamiento     (Python, no agente)
       ↓
5. @agent-synthesizer × 1 invocación (modo daily)
       ↓
6. @agent-competitive × 0-1 invocaciones (solo domingos, si hay datos competitivos)
```

Los domingos se añade después del paso 5:

```
5b. @agent-synthesizer × 1 invocación (modo weekly)
```

El último día del mes se añade:

```
5c. @agent-synthesizer × 1 invocación (modo monthly)
```

---

## 3. Estructura de Archivos de Agentes

### 3.1 Ubicación dentro del proyecto

Los archivos de definición de agentes se almacenan en `.claude/agents/` dentro del directorio raíz del proyecto. Esta es la ubicación estándar que Claude Code busca cuando se invoca un agente con el flag `--agent`.

```
ai-architect/
├── .claude/
│   └── agents/
│       ├── agent-ranker.md
│       ├── agent-analyzer.md
│       ├── agent-synthesizer.md
│       └── agent-competitive.md
├── Dockerfile
├── docker-compose.yml
├── main.py
├── config.yaml
├── ...
```

### 3.2 Formato de un archivo de agente

Cada archivo de agente es un documento Markdown que Claude Code lee antes de procesar el input. El archivo contiene:

1. **Identidad y rol.** Quién es el agente, qué hace, para qué sistema trabaja.
2. **Contexto del dominio.** Información estable sobre el ecosistema que el agente necesita para tomar decisiones (competidores conocidos, dimensiones de impacto, niveles de madurez, etc.).
3. **Criterios de evaluación.** Escalas, umbrales, definiciones de cada nivel o categoría.
4. **Formato de output.** Schema JSON exacto que el agente debe producir. Incluye tipos de datos, campos obligatorios, y restricciones de valores.
5. **Restricciones.** Qué no debe hacer el agente (no inventar URLs, no especular sin evidencia, etc.).

El archivo NO contiene datos variables del ciclo actual. Esos se pasan como prompt en cada invocación.

### 3.3 Convenciones de nomenclatura

| Nombre de archivo | Nombre del agente al invocar | Descripción |
|---|---|---|
| `agent-ranker.md` | `agent-ranker` | Evaluación y scoring de items en batch |
| `agent-analyzer.md` | `agent-analyzer` | Análisis profundo individual |
| `agent-synthesizer.md` | `agent-synthesizer` | Síntesis estratégica (daily, weekly, monthly) |
| `agent-competitive.md` | `agent-competitive` | Mapeo competitivo del ecosistema |

---

## 4. Inventario de Agentes

### 4.1 Resumen

| Agente | Modelo | Granularidad | Frecuencia | Invocaciones/día | Input | Output |
|--------|--------|-------------|-----------|------------------|-------|--------|
| `@agent-ranker` | Sonnet | Batch de 10 items | Cada ciclo diario | 10-15 | Batch de `CollectedItem` (JSON) | Array de scores + impact + maturity (JSON) |
| `@agent-analyzer` | Sonnet | 1 item | Cada ciclo diario | 60-100 | 1 `ProcessedItem` con contenido completo | 1 `AnalyzedItem` (JSON) |
| `@agent-synthesizer` | Opus | Agregación | Diario + semanal + mensual | 1-3 | Summaries + histórico ChromaDB (JSON) | Síntesis estructurada (JSON) |
| `@agent-competitive` | Opus | Agregación | Semanal | 0-1 | Items con notas competitivas + matriz actual (JSON) | Matriz competitiva actualizada (JSON) |

### 4.2 Criterios de separación

Los agentes están separados por **tipo de razonamiento**, no por frecuencia temporal ni por fuente de datos:

- **`@agent-ranker`** realiza evaluación rápida y comparativa (muchos items, poco tiempo por item).
- **`@agent-analyzer`** realiza análisis profundo y generativo (un item, mucho detalle).
- **`@agent-synthesizer`** realiza razonamiento estratégico y conexión de patrones (muchos items procesados, visión macro).
- **`@agent-competitive`** realiza razonamiento comparativo de dominio específico (conocimiento del paisaje competitivo).

Esta separación permite que cada agente esté optimizado para su tipo de tarea. Si en el futuro se necesita un nuevo tipo de razonamiento (por ejemplo, análisis de seguridad), se añade un nuevo agente sin tocar los existentes.

---

## 5. Agente: Signal Ranker

### 5.1 Propósito

El Signal Ranker evalúa batches de items recolectados y asigna a cada uno: un score de señal (`signal_score`), dimensiones de impacto (`impact_dimensions`, `impact_level`), y nivel de madurez (`maturity_level`). Los items por debajo del threshold configurable se marcan como descartados y no pasan al Analyzer.

Este agente consolida en una sola invocación lo que la planificación técnica define como tres componentes separados (Signal Ranker, Impact Classifier, Maturity Classifier), ya que la planificación técnica ya establece que se resuelven en un solo prompt batch (sección 6.7 de la planificación técnica).

### 5.2 Contrato

| Campo | Valor |
|-------|-------|
| Archivo | `.claude/agents/agent-ranker.md` |
| Modelo | `claude-sonnet-4-20250514` |
| Input | JSON array de hasta 10 `CollectedItem` con campos: `id`, `title`, `url`, `source_type`, `source_name`, `published_at`, `content` (truncado a 15.000 tokens), `metadata` |
| Output | JSON array de exactamente N objetos (uno por cada item del input), cada uno con los campos definidos abajo |
| Timeout | 120 segundos |
| Reintentos | 2 (con backoff exponencial: 5s, 15s) |

### 5.3 Schema de output por item

```json
{
  "item_id": "string (SHA256 del CollectedItem)",
  "signal_score": "integer 1-10",
  "signal_justification": "string, una frase explicando el score",
  "impact_dimensions": ["string array, valores del enum ImpactDimension"],
  "impact_level": "string: low | medium | high | critical",
  "maturity_level": "string: experimental | emerging | production_viable | consolidated | declining"
}
```

Los valores válidos para `impact_dimensions` son los definidos en el enum `ImpactDimension` de la planificación técnica: `api`, `infrastructure`, `orchestration`, `security`, `performance`, `evaluation`, `tooling`, `governance`, `benchmark`, `developer_experience`.

### 5.4 Contenido del archivo del agente

El archivo `agent-ranker.md` debe incluir las siguientes secciones:

**Identidad:**
- Es un analista de inteligencia técnica especializado en el ecosistema Claude Code, MCP, y AI-assisted development.
- Trabaja como componente del sistema AI Architect v2.
- Su única tarea es evaluar items y asignar scores y clasificaciones.

**Criterios de scoring (signal_score):**
- Reproducir la escala completa definida en la sección 6.3 de la planificación técnica:
  - 1-3: Ruido. Contenido genérico, opinión sin evidencia, tutorial básico, marketing.
  - 4-5: Señal baja. Información útil pero no urgente ni profunda.
  - 6-7: Señal media. Contenido técnico con insights aplicables.
  - 8-9: Señal alta. Decisión arquitectónica documentada, problema real de producción, benchmark con metodología.
  - 10: Señal crítica. Cambio de paradigma, breaking change, vulnerabilidad, nueva capability fundamental.
- Los cuatro ejes de evaluación: profundidad técnica, impacto potencial, evidencia práctica, novedad aparente.

**Criterios de impact_dimensions:**
- Reproducir las definiciones del enum `ImpactDimension` con ejemplos de cuándo aplicar cada una.
- Un item puede tener múltiples dimensiones.

**Criterios de impact_level:**
- `low`: Afecta a un caso de uso específico o nicho.
- `medium`: Afecta a patrones de uso comunes.
- `high`: Afecta a la mayoría de usuarios del ecosistema.
- `critical`: Cambia fundamentalmente cómo se construye con Claude Code.

**Criterios de maturity_level:**
- Reproducir las definiciones del enum `MaturityLevel`:
  - `experimental`: Proof of concept, sin uso documentado en producción.
  - `emerging`: Primeros usos reales, evidencia limitada.
  - `production_viable`: Documentación de uso en producción, problemas conocidos y manejables.
  - `consolidated`: Ampliamente adoptado, best practices establecidas.
  - `declining`: Evidencia de migración hacia alternativas.

**Restricciones:**
- Responder SOLO con JSON válido, sin texto adicional.
- No inventar información que no esté en el input.
- No asignar `signal_score: 10` a menos que haya evidencia clara de cambio fundamental.
- El número de objetos en el output debe coincidir exactamente con el número de items en el input.

### 5.5 Cómo lo invoca Python

```python
# src/processors/claude_client.py

def invoke_ranker(items_batch: list[dict]) -> list[dict]:
    """
    Invoca @agent-ranker con un batch de hasta 10 CollectedItems.
    
    Args:
        items_batch: Lista de hasta 10 CollectedItem serializados como dict.
        
    Returns:
        Lista de dicts con signal_score, impact_dimensions, impact_level, 
        maturity_level para cada item.
        
    Raises:
        AgentError: Si el agente falla después de los reintentos.
        AgentOutputError: Si el output no es JSON válido o no coincide el schema.
    """
    prompt = f"""Evalúa los siguientes {len(items_batch)} items.

--- ITEMS A EVALUAR ---
{json.dumps(items_batch, ensure_ascii=False, indent=2)}

Responde SOLO con un JSON array con un objeto por cada item."""

    raw_output = run_agent(
        agent_name="agent-ranker",
        prompt=prompt,
        model="claude-sonnet-4-20250514",
        timeout=120
    )
    
    return parse_and_validate_ranker_output(raw_output, expected_count=len(items_batch))
```

El prompt que se pasa al agente contiene SOLO los datos del ciclo actual. Las instrucciones de rol, criterios de scoring, y formato de output ya están en el archivo del agente.

---

## 6. Agente: Analyzer

### 6.1 Propósito

El Analyzer genera un análisis profundo de un solo item que pasó el filtro del Signal Ranker (items no descartados). Produce insights técnicos, implicaciones arquitectónicas, aplicabilidad práctica, y notas competitivas cuando aplica.

### 6.2 Contrato

| Campo | Valor |
|-------|-------|
| Archivo | `.claude/agents/agent-analyzer.md` |
| Modelo | `claude-sonnet-4-20250514` |
| Input | JSON con un `ProcessedItem` completo: incluye `collected_item` (con `content` completo), `signal_score`, `novelty_score`, `impact_dimensions`, `impact_level`, `maturity_level` |
| Output | JSON con los campos del schema `AnalyzedItem` (sin el campo `processed_item`, que ya tiene el orquestador) |
| Timeout | 300 segundos (el contenido puede ser extenso: hasta 15.000 tokens) |
| Reintentos | 2 (con backoff exponencial: 5s, 15s) |

### 6.3 Schema de output

```json
{
  "summary": "string, 2-3 oraciones",
  "key_insights": ["string array, 3-5 insights principales"],
  "code_snippets": ["string array, snippets relevantes o descripción de código. Puede estar vacío"],
  "practical_applicability": "string, cómo aplicar en desarrollo real con Claude Code",
  "architectural_implications": "string, qué implica para la arquitectura de sistemas con LLMs",
  "related_topics": ["string array, temas para cross-referencia"],
  "tags": ["string array, 3-7 tags para clasificación"],
  "competitive_notes": "string o null, notas sobre posición competitiva si aplica"
}
```

### 6.4 Contenido del archivo del agente

El archivo `agent-analyzer.md` debe incluir las siguientes secciones:

**Identidad:**
- Es un arquitecto senior especializado en AI-assisted development, con expertise profundo en Claude Code, MCP (Model Context Protocol), y sistemas multi-agente.
- Trabaja como componente del sistema AI Architect v2.
- Su tarea es analizar un recurso técnico individual y generar un análisis de alta calidad.

**Instrucciones de análisis:**
- El `summary` debe ser autosuficiente: un lector debería entender lo esencial sin leer el contenido original.
- Los `key_insights` deben ser accionables, no descriptivos. "Claude Code ahora soporta X" es descriptivo. "El soporte de X permite eliminar el paso de Y en workflows de Z" es accionable.
- La `practical_applicability` debe ser concreta: qué haría diferente un desarrollador que trabaja con Claude Code después de leer este análisis.
- Las `architectural_implications` deben conectar con patrones más amplios: ¿cambia esto cómo se diseñan agentes? ¿Afecta a la gestión de context window? ¿Implica nuevos tradeoffs?
- Los `competitive_notes` solo se rellenan si el contenido menciona explícitamente competidores (GitHub Copilot, Cursor, Windsurf, Cline, Aider) o hace comparaciones. No inventar comparaciones que no estén en el contenido.

**Contexto del ecosistema:**
- Lista de competidores directos de Claude Code: GitHub Copilot, Cursor, Windsurf, Cline, Aider.
- Conceptos clave del ecosistema: MCP (Model Context Protocol), agentes LLM, context window management, tool use, multi-agent systems, evaluación de LLMs.
- Dimensiones de impacto (referencia al enum `ImpactDimension`): api, infrastructure, orchestration, security, performance, evaluation, tooling, governance, benchmark, developer_experience.

**Restricciones:**
- Responder SOLO con JSON válido, sin texto adicional.
- No inventar insights que no se deriven del contenido proporcionado.
- No generar `competitive_notes` si el contenido no menciona competidores.
- Los `tags` deben ser descriptivos y reutilizables, no frases completas. Ejemplo correcto: `["mcp", "context-window", "multi-agent"]`. Ejemplo incorrecto: `["artículo sobre MCP y context window"]`.

### 6.5 Cómo lo invoca Python

```python
def invoke_analyzer(processed_item: dict) -> dict:
    """
    Invoca @agent-analyzer con un ProcessedItem individual.
    
    Args:
        processed_item: ProcessedItem serializado como dict, incluyendo 
                       collected_item con content completo.
        
    Returns:
        Dict con campos del AnalyzedItem (sin processed_item).
        
    Raises:
        AgentError: Si el agente falla después de los reintentos.
        AgentOutputError: Si el output no es JSON válido o no coincide el schema.
    """
    prompt = f"""Analiza el siguiente recurso técnico.

--- RECURSO A ANALIZAR ---
{json.dumps(processed_item, ensure_ascii=False, indent=2)}

Responde SOLO con un JSON objeto con el análisis completo."""

    raw_output = run_agent(
        agent_name="agent-analyzer",
        prompt=prompt,
        model="claude-sonnet-4-20250514",
        timeout=300
    )
    
    return parse_and_validate_analyzer_output(raw_output)
```

---

## 7. Agente: Synthesizer

### 7.1 Propósito

El Synthesizer genera síntesis estratégicas que transforman análisis individuales en inteligencia accionable. Un solo agente cubre las tres frecuencias temporales (diaria, semanal, mensual). La diferencia entre frecuencias es el tipo y volumen de input, y las preguntas que debe responder, no el tipo de razonamiento.

### 7.2 Contrato

| Campo | Valor |
|-------|-------|
| Archivo | `.claude/agents/agent-synthesizer.md` |
| Modelo | `claude-opus-4-6` |
| Input | JSON con campo `mode` ("daily", "weekly", "monthly") y los datos correspondientes (ver detalle por modo abajo) |
| Output | JSON con el schema correspondiente al modo (ver detalle por modo abajo) |
| Timeout | 600 segundos (la síntesis puede ser compleja, especialmente en modo monthly) |
| Reintentos | 2 (con backoff exponencial: 10s, 30s) |

### 7.3 Modos de operación

#### Modo daily

**Input:**

```json
{
  "mode": "daily",
  "date": "YYYY-MM-DD",
  "analyzed_items_count": 85,
  "analyzed_items_summaries": [
    {
      "item_id": "...",
      "title": "...",
      "source_type": "...",
      "signal_score": 7,
      "summary": "...",
      "key_insights": ["..."],
      "tags": ["..."]
    }
  ],
  "related_historical_content": [
    {
      "item_id": "...",
      "title": "...",
      "date": "YYYY-MM-DD",
      "summary": "...",
      "similarity_score": 0.85
    }
  ]
}
```

**Output:** Schema `DailySynthesis` como está definido en la sección 8.5 de la planificación técnica:

```json
{
  "day_relevance_score": "integer 1-10",
  "trends_detected": [
    {
      "name": "string",
      "description": "string, 1-2 oraciones",
      "evidence": ["item_id array"],
      "confidence": "float 0.0-1.0"
    }
  ],
  "historical_connections": ["string array"],
  "highlights": [
    {
      "item_id": "string",
      "title": "string",
      "source": "string",
      "relevance_score": "integer",
      "why_it_matters": "string, 2-3 oraciones"
    }
  ],
  "recommended_actions": [
    {
      "action": "string",
      "priority": "high | medium | low",
      "related_items": ["item_id array"]
    }
  ]
}
```

#### Modo weekly

**Input:**

```json
{
  "mode": "weekly",
  "week_start": "YYYY-MM-DD",
  "week_end": "YYYY-MM-DD",
  "daily_syntheses": ["array de 7 DailySynthesis completas"],
  "high_signal_items": ["array de AnalyzedItem con signal_score >= 7"],
  "competitive_matrix_current": { "... o null si no existe aún" }
}
```

**Output:** Schema `WeeklySynthesis` como está definido en la sección 8.6 de la planificación técnica:

```json
{
  "week_relevance_score": "integer 1-10",
  "pattern_evolutions": [
    {
      "pattern_name": "string",
      "status": "new | growing | stable | declining",
      "description": "string",
      "first_seen": "YYYY-MM-DD",
      "evidence_count": "integer"
    }
  ],
  "maturity_changes": [
    {
      "technology": "string",
      "previous_level": "string",
      "current_level": "string",
      "evidence": "string"
    }
  ],
  "competitive_shifts": [
    {
      "area": "string",
      "description": "string",
      "winners": ["string array"],
      "losers": ["string array"]
    }
  ],
  "emerging_patterns": ["string array"],
  "anti_patterns": ["string array"],
  "top_highlights_week": ["array de 3-5 highlights"]
}
```

#### Modo monthly

**Input:**

```json
{
  "mode": "monthly",
  "month": "YYYY-MM",
  "weekly_syntheses": ["array de 4-5 WeeklySynthesis del mes"],
  "critical_items": ["array de AnalyzedItem con signal_score = 10, puede estar vacío"]
}
```

**Output:** Schema `MonthlySynthesis` como está definido en la sección 8.7 de la planificación técnica:

```json
{
  "month_relevance_score": "integer 1-10",
  "structural_changes": [
    {
      "area": "string",
      "description": "string",
      "impact_assessment": "string",
      "evidence_summary": "string"
    }
  ],
  "consolidated_trends": ["string array"],
  "emerging_risks": [
    {
      "risk": "string",
      "likelihood": "low | medium | high",
      "potential_impact": "string",
      "mitigation": "string"
    }
  ],
  "competitive_matrix_summary": "string, un párrafo",
  "architectural_patterns_summary": "string, un párrafo",
  "key_recommendations": ["string array, 3-5 acciones"]
}
```

### 7.4 Contenido del archivo del agente

El archivo `agent-synthesizer.md` debe incluir las siguientes secciones:

**Identidad:**
- Es el motor de síntesis estratégica de AI Architect v2, un sistema de inteligencia técnica sobre el ecosistema Claude Code y AI-assisted development.
- Su objetivo es transformar análisis individuales en inteligencia estratégica que permita a un experto técnico tomar decisiones informadas.

**Modos de operación:**
- El agente opera en tres modos, determinados por el campo `mode` del input.
- Cada modo tiene un horizonte temporal, tipo de preguntas, y schema de output diferente.
- El agente debe identificar el modo del input y aplicar las instrucciones correspondientes.

**Instrucciones por modo:**

Para `daily`:
- Detectar patrones que aparecen en 2+ items del día O que conectan con contenido de días anteriores.
- Las `historical_connections` deben ser explícitas: "El tema X que apareció el día Y se confirma/contradice/expande con el item Z de hoy."
- Las `recommended_actions` deben ser concretas: investigar, probar, cambiar, leer en detalle. No acciones vagas.
- El `day_relevance_score` debe calibrarse: la mayoría de días deberían estar entre 3-6. Un 8+ requiere que haya sucedido algo realmente significativo.

Para `weekly`:
- Detectar patrones que solo son visibles a escala semanal: evoluciones de tendencias, cambios de madurez, movimientos competitivos.
- Los `pattern_evolutions` deben tener `first_seen` real, no inventado.
- Los `maturity_changes` solo deben incluirse si hay evidencia de cambio real durante la semana.
- Los `emerging_patterns` se refieren a patrones arquitectónicos (por ejemplo: "MCP gateway pattern", "agent chain-of-thought validation").

Para `monthly`:
- Identificar cambios estructurales que solo son visibles a escala mensual.
- Los `structural_changes` deben ser significativos: no repetir tendencias semanales, sino señalar cambios de fondo.
- Las `key_recommendations` deben ser acciones estratégicas, no tácticas.

**Restricciones:**
- Responder SOLO con JSON válido, sin texto adicional.
- No inventar tendencias sin evidencia en los datos proporcionados.
- No repetir los mismos highlights en diferentes niveles de síntesis.
- Los `confidence` scores en tendencias diarias deben ser conservadores: 0.8+ solo si hay evidencia fuerte.

### 7.5 Cómo lo invoca Python

```python
def invoke_synthesizer(mode: str, synthesis_data: dict) -> dict:
    """
    Invoca @agent-synthesizer con datos de síntesis para el modo especificado.
    
    Args:
        mode: "daily", "weekly", o "monthly"
        synthesis_data: Dict con los datos correspondientes al modo.
                       Debe incluir campo "mode" ya seteado.
        
    Returns:
        Dict con el schema de síntesis correspondiente al modo.
        
    Raises:
        AgentError: Si el agente falla después de los reintentos.
        AgentOutputError: Si el output no es JSON válido o no coincide el schema.
    """
    prompt = f"""Genera una síntesis {mode}.

--- DATOS DE ENTRADA ---
{json.dumps(synthesis_data, ensure_ascii=False, indent=2)}

Responde SOLO con un JSON objeto con la síntesis completa."""

    raw_output = run_agent(
        agent_name="agent-synthesizer",
        prompt=prompt,
        model="claude-opus-4-6",
        timeout=600
    )
    
    return parse_and_validate_synthesis_output(raw_output, mode=mode)
```

---

## 8. Agente: Competitive Mapper

### 8.1 Propósito

El Competitive Mapper mantiene una matriz competitiva actualizada que compara Claude Code con las alternativas del ecosistema. Se ejecuta semanalmente y recibe los items que tienen notas competitivas (`competitive_notes` no null) junto con la matriz actual (si existe).

### 8.2 Contrato

| Campo | Valor |
|-------|-------|
| Archivo | `.claude/agents/agent-competitive.md` |
| Modelo | `claude-opus-4-6` |
| Input | JSON con: items con notas competitivas de la semana, y la matriz competitiva actual (o null en la primera ejecución) |
| Output | JSON con el schema `CompetitiveMatrix` completo y actualizado |
| Timeout | 600 segundos |
| Reintentos | 2 (con backoff exponencial: 10s, 30s) |

### 8.3 Schema de input

```json
{
  "week": "YYYY-WNN",
  "items_with_competitive_notes": [
    {
      "item_id": "string",
      "title": "string",
      "source_type": "string",
      "summary": "string",
      "competitive_notes": "string"
    }
  ],
  "current_matrix": {
    "last_updated": "YYYY-WNN o null",
    "competitors": ["array de CompetitorProfile o vacío"],
    "key_differentiators": ["string array"],
    "gaps_detected": ["string array"],
    "opportunities": ["string array"]
  }
}
```

Si es la primera ejecución (no existe matriz previa), `current_matrix` se envía como:

```json
{
  "current_matrix": null
}
```

### 8.4 Schema de output

El output sigue el schema `CompetitiveMatrix` definido en la sección 8.8 de la planificación técnica:

```json
{
  "last_updated": "YYYY-WNN",
  "competitors": [
    {
      "name": "string: Claude Code | GitHub Copilot | Cursor | Windsurf | Cline | Aider | otros",
      "model_backend": "string",
      "extensibility": "string: MCP | plugins propietarios | API abierta | limitado",
      "pricing_tier": "string: free | $10-20/mo | $20-50/mo | enterprise",
      "known_strengths": ["string array"],
      "known_limitations": ["string array"],
      "recent_changes": ["string array, cambios de las últimas 4 semanas"],
      "last_updated": "YYYY-WNN"
    }
  ],
  "key_differentiators": ["string array, diferenciadores del ecosistema Claude"],
  "gaps_detected": ["string array, áreas donde la competencia supera a Claude"],
  "opportunities": ["string array, oportunidades detectadas"]
}
```

### 8.5 Contenido del archivo del agente

El archivo `agent-competitive.md` debe incluir las siguientes secciones:

**Identidad:**
- Es un analista de inteligencia competitiva especializado en herramientas de AI-assisted development.
- Trabaja como componente del sistema AI Architect v2.
- Su tarea es mantener una visión actualizada y precisa del panorama competitivo.

**Conocimiento base de competidores:**
- Perfiles iniciales de cada competidor con información estable:
  - **Claude Code** (Anthropic): CLI + agente, extensible vía MCP, modelos Claude.
  - **GitHub Copilot** (Microsoft/GitHub): Integración IDE, GitHub ecosystem, modelos OpenAI + propios.
  - **Cursor** (Anysphere): IDE completo, fork de VS Code, multi-model.
  - **Windsurf** (Codeium): IDE completo, modelos propios + terceros.
  - **Cline** (community): Extensión VS Code open source, multi-model.
  - **Aider** (community): CLI open source, multi-model, git-aware.
- Este conocimiento base se usa como punto de partida y se actualiza con la evidencia que llega cada semana.

**Dimensiones de comparación:**
- Features principales (code generation, code review, debugging, refactoring, multi-file editing)
- Modelo LLM subyacente
- Extensibilidad (MCP vs plugins propietarios)
- Pricing
- Limitaciones conocidas
- Presencia enterprise

**Instrucciones de actualización:**
- Si `current_matrix` es null, generar la primera versión basándose en el conocimiento base y los items proporcionados.
- Si `current_matrix` tiene datos, actualizar solo los campos donde los items de la semana aportan evidencia nueva.
- Los `recent_changes` deben limpiarse: eliminar cambios con más de 4 semanas de antigüedad.
- No inventar cambios que no estén respaldados por los items proporcionados.
- Si no hay items con notas competitivas en una semana, devolver la matriz sin cambios excepto `last_updated`.

**Restricciones:**
- Responder SOLO con JSON válido, sin texto adicional.
- No especular sobre features no anunciados.
- No incluir información de pricing que no provenga de fuentes verificables.
- Mantener la objetividad: documentar tanto las ventajas como las desventajas de Claude Code.

### 8.6 Cómo lo invoca Python

```python
def invoke_competitive_mapper(competitive_data: dict) -> dict:
    """
    Invoca @agent-competitive con items competitivos y la matriz actual.
    
    Args:
        competitive_data: Dict con items_with_competitive_notes y current_matrix.
        
    Returns:
        Dict con CompetitiveMatrix actualizada.
        
    Raises:
        AgentError: Si el agente falla después de los reintentos.
        AgentOutputError: Si el output no es JSON válido o no coincide el schema.
    """
    prompt = f"""Actualiza la matriz competitiva con los datos de esta semana.

--- DATOS DE ENTRADA ---
{json.dumps(competitive_data, ensure_ascii=False, indent=2)}

Responde SOLO con un JSON objeto con la matriz competitiva completa actualizada."""

    raw_output = run_agent(
        agent_name="agent-competitive",
        prompt=prompt,
        model="claude-opus-4-6",
        timeout=600
    )
    
    return parse_and_validate_competitive_output(raw_output)
```

---

## 9. Integración con el Orquestador Python

### 9.1 Cambios en `claude_client.py`

El módulo `src/processors/claude_client.py` definido en la planificación técnica necesita refactorizarse para soportar invocación de agentes. La función base `ask_claude()` se mantiene como fallback, pero se añade una nueva función `run_agent()` que es la que usan los procesadores.

**Función `run_agent()` — interfaz principal:**

```python
def run_agent(
    agent_name: str,
    prompt: str,
    model: str,
    timeout: int = 300,
    max_retries: int = 2
) -> str:
    """
    Invoca un subagente de Claude Code.
    
    Args:
        agent_name: Nombre del agente (sin extensión). Ejemplo: "agent-ranker"
        prompt: Datos a procesar (NO instrucciones de rol, esas están en el agente).
        model: Modelo a usar. Ejemplo: "claude-sonnet-4-20250514"
        timeout: Timeout en segundos.
        max_retries: Número máximo de reintentos.
        
    Returns:
        Output crudo del agente como string.
        
    Raises:
        AgentError: Si el agente falla después de todos los reintentos.
    """
```

**Lógica de invocación:**

```python
result = subprocess.run(
    ["claude", "-p", prompt, "--agent", agent_name, "--model", model],
    capture_output=True,
    text=True,
    timeout=timeout
)
```

**Importante:** La invocación exacta del CLI con el flag `--agent` depende de la versión de Claude Code instalada en el contenedor Docker. La sintaxis mostrada arriba es la esperada, pero debe validarse durante la implementación de la Fase 1 contra la versión concreta del CLI disponible.

### 9.2 Validación de output

Cada función `invoke_*` incluye una capa de validación entre el output crudo del agente y el resultado devuelto al orquestador. Esta validación:

1. **Parsea el JSON.** Si el output no es JSON válido, se loguea el error y se reintenta.
2. **Valida el schema.** Se compara contra los modelos Pydantic existentes (`ProcessedItem`, `AnalyzedItem`, etc.). Si faltan campos obligatorios o los tipos no coinciden, se loguea el error y se reintenta.
3. **Valida las restricciones de negocio.** Por ejemplo: `signal_score` entre 1-10, `impact_level` dentro de los valores del enum, número de items en output igual al número en input (para el ranker).

**Implementación de validación:**

```python
def parse_and_validate_ranker_output(raw_output: str, expected_count: int) -> list[dict]:
    """
    Parsea y valida el output del @agent-ranker.
    
    Validaciones:
    1. JSON válido
    2. Es un array
    3. Tiene exactamente expected_count elementos
    4. Cada elemento tiene los campos obligatorios
    5. signal_score entre 1-10
    6. impact_level en valores válidos
    7. maturity_level en valores válidos
    8. impact_dimensions contiene solo valores del enum
    """
```

Si la validación falla después de los reintentos, el batch se marca como fallido y se incluye en el registro de errores del ciclo. Los items del batch no se descartan: se saltan el ranking y pasan al Analyzer con un `signal_score` por defecto de 5 (para no perder items por un fallo transitorio del agente).

### 9.3 Cambios en los procesadores existentes

Los módulos definidos en la planificación técnica que ahora delegan a agentes:

| Módulo actual | Cambio |
|---|---|
| `signal_ranker.py` | Reemplaza la lógica de prompt inline por llamada a `invoke_ranker()`. Mantiene la lógica de batching (dividir items en grupos de 10) y la lógica de descarte (marcar items con `signal_score < threshold`). |
| `impact_classifier.py` | Se elimina como módulo separado. Su lógica está integrada en `@agent-ranker`. |
| `maturity_classifier.py` | Se elimina como módulo separado. Su lógica está integrada en `@agent-ranker`. |
| `analyzer.py` | Reemplaza la lógica de prompt inline por llamada a `invoke_analyzer()`. Mantiene la lógica de iteración item por item y la construcción del `AnalyzedItem` final (combina output del agente con `ProcessedItem`). |
| `synthesizer.py` | Reemplaza los tres prompts inline por llamada a `invoke_synthesizer(mode)`. Mantiene la lógica de determinación del modo (¿es domingo? ¿es fin de mes?) y la preparación de datos de input. |
| `competitive_mapper.py` | Reemplaza el prompt inline por llamada a `invoke_competitive_mapper()`. Mantiene la lógica de filtrado de items con `competitive_notes` y la carga/guardado de la matriz desde ChromaDB. |
| `novelty_detector.py` | Sin cambios. Sigue siendo Python puro con consultas a ChromaDB. |

### 9.4 Flujo de datos completo con agentes

```
main.py::run_daily_cycle()
│
├── Fase 0: transcribe_podcasts() ← Python puro
│
├── Fase 1: collect_all() ← Python puro
│   └── for each collector: collector.collect(since)
│   └── deduplicate(all_items)
│
├── Fase 2: process_all(collected_items)
│   │
│   ├── signal_ranker.rank_batch(items[0:10])
│   │   └── claude_client.invoke_ranker(batch) ← @agent-ranker
│   ├── signal_ranker.rank_batch(items[10:20])
│   │   └── claude_client.invoke_ranker(batch) ← @agent-ranker
│   ├── ... (hasta procesar todos los items)
│   │
│   ├── filter_discarded(all_ranked_items, threshold=4)
│   │
│   ├── for item in non_discarded:
│   │   ├── novelty_detector.check(item) ← Python puro, ChromaDB
│   │   └── analyzer.analyze(item)
│   │       └── claude_client.invoke_analyzer(item) ← @agent-analyzer
│   │
│   └── vector_store.store_all(analyzed_items)
│
├── Fase 3: synthesize()
│   │
│   ├── synthesizer.daily(analyzed_items, historical_context)
│   │   └── claude_client.invoke_synthesizer("daily", data) ← @agent-synthesizer
│   │
│   ├── if is_sunday:
│   │   ├── synthesizer.weekly(daily_syntheses, high_signal_items)
│   │   │   └── claude_client.invoke_synthesizer("weekly", data) ← @agent-synthesizer
│   │   └── competitive_mapper.update(competitive_items, current_matrix)
│   │       └── claude_client.invoke_competitive_mapper(data) ← @agent-competitive
│   │
│   └── if is_end_of_month:
│       └── synthesizer.monthly(weekly_syntheses, critical_items)
│           └── claude_client.invoke_synthesizer("monthly", data) ← @agent-synthesizer
│
├── Fase 4: generate_outputs() ← Python puro
│   └── markdown_gen.generate_all()
│
└── Fase 5: notify() ← Python puro
    └── notifier.send_push()
```

---

## 10. Gestión de Errores en Subagentes

### 10.1 Tipos de error

| Tipo de error | Causa | Comportamiento |
|---|---|---|
| `AgentTimeoutError` | El agente no responde dentro del timeout | Reintento hasta max_retries. Si falla, el batch/item se salta. |
| `AgentProcessError` | El subprocess devuelve código de salida no-0 | Reintento. Si persiste, se loguea stderr y el batch/item se salta. |
| `AgentOutputError` | El output no es JSON válido | Reintento. Si persiste, se loguea el output crudo y el batch/item se salta. |
| `AgentSchemaError` | El JSON es válido pero no cumple el schema esperado | Reintento. Si persiste, se loguea el output y se intenta extracción parcial. |

### 10.2 Política de reintentos

```python
RETRY_CONFIG = {
    "agent-ranker": {
        "max_retries": 2,
        "backoff_seconds": [5, 15],
        "timeout": 120
    },
    "agent-analyzer": {
        "max_retries": 2,
        "backoff_seconds": [5, 15],
        "timeout": 300
    },
    "agent-synthesizer": {
        "max_retries": 2,
        "backoff_seconds": [10, 30],
        "timeout": 600
    },
    "agent-competitive": {
        "max_retries": 2,
        "backoff_seconds": [10, 30],
        "timeout": 600
    }
}
```

### 10.3 Comportamiento ante fallo total

Si un agente falla todos los reintentos:

**`@agent-ranker` falla:** Los items del batch no se descartan. Se les asigna `signal_score: 5` (valor neutro) y `impact_level: medium`, `maturity_level: emerging` como defaults conservadores. Se procesan normalmente por el Analyzer. Se registra un `ProcessingError` en el digest diario.

**`@agent-analyzer` falla para un item:** El item se almacena en ChromaDB con un `AnalyzedItem` parcial donde `summary` es el `title` del `CollectedItem`, `key_insights` está vacío, y se marca con un flag `analysis_failed: true` en `processing_metadata`. Se incluye en el digest diario con una nota de que el análisis no se completó. Se registra el error.

**`@agent-synthesizer` falla:** Se genera una síntesis mínima automática con Python (sin LLM): listado de los items del día ordenados por `signal_score`, sin tendencias ni conexiones históricas. El `day_relevance_score` se calcula como promedio de `signal_scores`. Se marca como `synthesis_automated: true`. Se registra el error y se notifica vía ntfy.sh como alerta.

**`@agent-competitive` falla:** Se mantiene la matriz de la semana anterior sin cambios. Se registra el error. No es crítico porque la frecuencia es semanal.

### 10.4 Registro de errores de agentes

Los errores de agentes se almacenan en una estructura adicional dentro del digest diario:

```python
class AgentError(BaseModel):
    agent_name: str
    error_type: str  # timeout | process | output | schema
    error_message: str
    raw_output: str | None  # Output crudo si lo hay, para debugging
    input_summary: str  # Resumen del input que causó el error (no el input completo por espacio)
    timestamp: datetime
    retries_attempted: int
    fallback_applied: str  # Descripción del fallback que se aplicó
```

---

## 11. Restricciones de Hardware y Ejecución

### 11.1 Impacto de los subagentes en el uso de memoria

La invocación de un subagente vía `subprocess.run()` lanza un proceso Claude Code que:

1. Lee el archivo del agente desde `.claude/agents/`.
2. Combina las instrucciones del agente con el prompt proporcionado.
3. Envía la petición al modelo Claude (Sonnet o Opus).
4. Recibe la respuesta y la devuelve por stdout.
5. El proceso termina.

El proceso es efímero: se crea y destruye en cada invocación. No mantiene estado entre llamadas. El consumo de memoria es el del proceso CLI de Claude Code, que es significativamente menor que correr ChromaDB o faster-whisper.

### 11.2 Orden de ejecución y memoria

El orden de ejecución definido en la sección 2.4 de la planificación técnica se mantiene:

1. **Fase 0:** Transcripción de podcasts (faster-whisper, ~2GB RAM) → liberar whisper.
2. **Fase 1:** Recolección (Python puro, bajo consumo de memoria).
3. **Fase 2:** Procesamiento (ChromaDB embedded + invocaciones secuenciales de agentes). ChromaDB consume RAM persistente (~500MB-1GB con el volumen esperado). Los agentes se invocan uno a uno: no hay dos procesos Claude Code corriendo simultáneamente.
4. **Fase 3:** Síntesis (invocaciones de agentes, ChromaDB sigue activo para consultas históricas).
5. **Fase 4:** Generación de outputs y notificación (bajo consumo).

### 11.3 Estimación de tiempo de ejecución

| Componente | Invocaciones | Tiempo estimado por invocación | Tiempo total estimado |
|---|---|---|---|
| `@agent-ranker` | 10-15 | 15-30 segundos | 2.5-7.5 minutos |
| `@agent-analyzer` | 60-100 | 30-60 segundos | 30-100 minutos |
| `@agent-synthesizer` (daily) | 1 | 60-120 segundos | 1-2 minutos |
| `@agent-synthesizer` (weekly) | 0-1 | 120-300 segundos | 0-5 minutos |
| `@agent-competitive` | 0-1 | 120-300 segundos | 0-5 minutos |
| **Total pipeline LLM** | | | **~35-120 minutos** |

El cuello de botella es el Analyzer (60-100 invocaciones individuales). Esto no cambia respecto al diseño original: la planificación técnica ya anticipaba este volumen de llamadas a Sonnet.

---

## 12. Validación y Testing de Agentes

### 12.1 Test manual desde CLI

Cada agente puede probarse de forma independiente sin ejecutar el pipeline. Para validar que un agente funciona correctamente:

1. Crear un archivo JSON de prueba con datos representativos del input que recibiría el agente.
2. Invocar el agente desde la línea de comandos.
3. Verificar que el output es JSON válido y cumple el schema esperado.

**Ejemplo para `@agent-ranker`:**

```bash
# Crear test_ranker_input.json con un batch de 3 items representativos
claude -p "$(cat test_ranker_input.json)" --agent agent-ranker --model claude-sonnet-4-20250514
```

**Ejemplo para `@agent-synthesizer` modo daily:**

```bash
# Crear test_synthesis_input.json con summaries de items y contenido histórico
claude -p "$(cat test_synthesis_input.json)" --agent agent-synthesizer --model claude-opus-4-6
```

### 12.2 Datos de test

Para cada agente se debe crear un directorio `tests/agents/` con archivos de input representativos:

```
tests/
└── agents/
    ├── ranker/
    │   ├── input_batch_typical.json      # 10 items de diversas fuentes
    │   ├── input_batch_all_noise.json    # 10 items de baja señal (esperamos scores 1-3)
    │   ├── input_batch_critical.json     # Items con breaking changes (esperamos score 9-10)
    │   └── expected_schemas.py           # Validaciones Pydantic del output
    ├── analyzer/
    │   ├── input_github_issue.json       # Item de GitHub Issues
    │   ├── input_blog_post.json          # Item de blog con métricas
    │   ├── input_competitive.json        # Item con menciones a competidores
    │   └── expected_schemas.py
    ├── synthesizer/
    │   ├── input_daily_typical.json      # Día normal con 80 items
    │   ├── input_weekly_typical.json     # Semana con 7 síntesis diarias
    │   ├── input_monthly_typical.json    # Mes con 4 síntesis semanales
    │   └── expected_schemas.py
    └── competitive/
        ├── input_first_run.json          # Primera ejecución (current_matrix: null)
        ├── input_weekly_update.json      # Actualización semanal con 5 items competitivos
        └── expected_schemas.py
```

### 12.3 Validación automatizada

El script `tests/test_agents.py` ejecuta cada agente con cada input de test y valida:

1. El output es JSON parseable.
2. El output cumple el schema Pydantic correspondiente.
3. Los valores están dentro de los rangos válidos.
4. El número de items en output coincide con el input (para el ranker).

Este script se ejecuta como parte del flujo de CI/CD o manualmente durante la Fase 4 de calibración.

### 12.4 Calibración de agentes (Fase 4)

Durante la Fase 4 del roadmap de implementación (Mes 3), los agentes se calibran con datos reales acumulados de los meses anteriores:

1. Extraer items reales con su `signal_score` y compararlos con el scoring manual del usuario.
2. Identificar patrones de sobre-scoring o sub-scoring.
3. Ajustar los criterios en los archivos de agente.
4. Re-ejecutar con datos históricos y comparar resultados.
5. Repetir hasta convergencia.

El ciclo eval/improve del skill-creator de Claude Code puede adaptarse para este proceso, aunque se aplica sobre archivos de agente (`.md`) en lugar de skills.

---

## 13. Relación con los Documentos Existentes

### 13.1 Mapa de documentación

| Documento | Contenido | Relación con este documento |
|---|---|---|
| `AI_Architect_v2_Marco_Estrategico.md` | Visión, modelo de inteligencia multicapa, pipeline conceptual, nuevos componentes lógicos | Este documento implementa los componentes lógicos como agentes concretos. |
| `AI_Architect_Fuentes_v2.docx` / `AI_Architect_v2_Fuentes_Informacion.pdf` | Marco de fuentes de información, análisis de cada fuente, fases de implementación sugeridas | Los agentes no modifican las fuentes. La recolección sigue en Python puro. |
| `ai-architect-v2-planificacion-tecnica.md` | Especificación técnica completa: schemas, prompts, flujos, almacenamiento, fases | **Este es el documento padre.** Los agentes implementan los prompts y flujos de procesamiento definidos allí. Los schemas Pydantic no cambian. |
| `2026-02-14-ai-architect-design.md` | Diseño del v1 original | Referencia histórica. Los agentes son específicos del v2. |
| **Este documento** | Arquitectura de subagentes | Complementa la planificación técnica con la capa de agentes. |

### 13.2 Qué secciones de la planificación técnica se ven afectadas

| Sección | Impacto |
|---|---|
| §2.1 Estructura de directorios | Añadir `.claude/agents/` con los 4 archivos de agente |
| §2.3 Flujo de datos general | Sin cambios en el diagrama. La implementación interna de cada etapa cambia. |
| §5 Pipeline de Recolección | Sin cambios |
| §6 Pipeline de Procesamiento | `signal_ranker.py` usa `@agent-ranker`. `impact_classifier.py` y `maturity_classifier.py` se eliminan como módulos separados. `novelty_detector.py` sin cambios. |
| §7 Pipeline de Análisis | `analyzer.py` usa `@agent-analyzer`. El prompt se mueve al archivo del agente. |
| §8 Pipeline de Síntesis | `synthesizer.py` usa `@agent-synthesizer`. `competitive_mapper.py` usa `@agent-competitive`. Los prompts se mueven a los archivos de agente. |
| §9 Almacenamiento | Sin cambios |
| §10 Formato de Outputs | Sin cambios |
| §11 Infraestructura | Añadir `.claude/agents/` al contenedor Docker (COPY en Dockerfile) |
| §12 Fases de Implementación | Los agentes se crean dentro de las tareas ya definidas. No se añaden fases nuevas. |
| §13 Monitorización | Añadir métricas de agentes: tasa de error por agente, tiempo promedio por invocación, tasa de reintentos. |

### 13.3 Integración en las fases de implementación

Los agentes se implementan progresivamente dentro de las fases ya definidas:

**Fase 1 (Semanas 1-2):**
- Semana 1: Crear `run_agent()` en `claude_client.py`. Crear `agent-ranker.md` y `agent-analyzer.md`.
- Semana 2: Crear `agent-synthesizer.md` (solo modo daily). Integrar las invocaciones en `signal_ranker.py`, `analyzer.py`, `synthesizer.py`.

**Fase 2 (Semanas 3-4):**
- Activar modo weekly en `agent-synthesizer.md`.
- Crear `agent-competitive.md`.

**Fase 3 (Mes 2):**
- Activar modo monthly en `agent-synthesizer.md`.
- Ajuste fino de los agentes con datos acumulados de las primeras semanas.

**Fase 4 (Mes 3):**
- Calibración sistemática de todos los agentes con datos reales.
- Ajuste de criterios, escalas, y restricciones basándose en métricas de operación.

---

## Apéndice A: Checklist de Implementación

Para cada agente, verificar antes de considerarlo listo para producción:

- [ ] Archivo `.md` creado en `.claude/agents/`
- [ ] Función `invoke_*` implementada en `claude_client.py`
- [ ] Validación de output con schema Pydantic implementada
- [ ] Datos de test creados en `tests/agents/`
- [ ] Test manual desde CLI exitoso con 3+ inputs diferentes
- [ ] Test automatizado (`test_agents.py`) pasando
- [ ] Manejo de errores y fallbacks implementados
- [ ] Timeout y reintentos configurados
- [ ] Métricas de agente registradas en logging
- [ ] Integración en el módulo procesador correspondiente (`signal_ranker.py`, `analyzer.py`, etc.)
- [ ] Test end-to-end del pipeline completo con el agente integrado
