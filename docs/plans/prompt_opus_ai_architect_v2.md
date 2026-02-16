# PROMPT — AI Architect v2: Documento de Planificación Técnica Completa

---

## ROL

Eres un arquitecto de sistemas de inteligencia técnica con experiencia en:
- Diseño de pipelines de recopilación y procesamiento de información a escala
- Sistemas de agentes con Claude Code y Claude API
- Despliegue de servicios en hardware embebido (ARM, Jetson)
- Ingeniería de prompts para modelos de lenguaje de alta capacidad

Tu tarea es producir un documento de planificación técnica completo, revisado y ejecutable para el proyecto AI Architect v2. El documento debe poder ser entregado a un ingeniero de software senior y servir como referencia completa durante toda la implementación, sin necesidad de consultar fuentes externas.

---

## OBJETIVO

Genera un documento de planificación técnica (Opción B: planificación + especificación técnica) para AI Architect v2. El sistema es un radar de inteligencia técnica automatizado que recopila, clasifica, analiza y sintetiza señal del ecosistema de Claude Code y AI-assisted development.

**Implementación desde cero.** No hay dependencia de ninguna versión anterior.

**Hardware de destino:** NVIDIA Jetson Orin Nano
- CPU: 6-core ARM Cortex-A78AE
- GPU: 1024-core NVIDIA Ampere
- RAM: 8GB LPDDR5 compartida CPU/GPU
- Almacenamiento: microSD o NVMe M.2
- SO: JetPack 6.x (Ubuntu 22.04 base)
- Restricción crítica: arquitectura ARM64, no x86. Todas las dependencias deben ser compatibles con ARM64.

---

## CONTEXTO DEL PROYECTO

A continuación se provee toda la documentación existente del proyecto. Úsala como base conceptual, pero no como especificación técnica definitiva. Identifica y corrige errores, inconsistencias y gaps.

### DOCUMENTO 1 — Diseño v1 (referencia de intenciones originales)

2026-02-14-ai-architect-design.md]

### DOCUMENTO 2 — Marco Estratégico v2

AI_Architect_v2_Marco_Estrategico.md]

### DOCUMENTO 3 — Marco de Fuentes v2

AI_Architect_Fuentes_v2.docx]

### DOCUMENTO 4 — Fuentes: enlaces oficiales


AI_Architect_v2_Fuentes_Informacion.pdf]


---

## RESTRICCIONES HARD

Las siguientes decisiones están tomadas. No las cuestiones. Úsalas como constraints de diseño:

1. **Coste total de APIs: cero.** Solo APIs gratuitas o acceso público sin autenticación de pago.
2. **Twitter/X:** Solo soluciones de acceso gratuito. Evalúa Nitter (instancia pública o self-hosted), scraping directo con rate limiting conservador, o RSS via nitter. Documenta limitaciones explícitas de cada opción y elige la más robusta para el caso de uso.
3. **Transcripción de podcasts:** Whisper local. Modelo recomendado: `whisper-base` o `whisper-small` para equilibrar precisión y consumo de RAM en Jetson. Usar `faster-whisper` (optimizado para CPU/CUDA) en lugar de la implementación original de OpenAI.
4. **Claude:** Vía Claude Code CLI montando la sesión del host (`~/.claude`), igual que en v1. No usar Anthropic API directamente (implica coste por token), usar subscripción.
5. **Base de datos vectorial:** ChromaDB. Validar compatibilidad ARM64 antes de cualquier alternativa.
6. **Lenguaje:** Python 3.11+.
7. **Contenerización:** Docker con soporte ARM64 (imágenes multi-arch o específicas para Jetson/L4T donde sea necesario).
8. **Scheduler:** Cron del host, no dentro del contenedor.
9. **Notificaciones:** ntfy.sh (gratuito, sin autenticación requerida).
10. **Almacenamiento de outputs:** Markdown local. Sin base de datos relacional adicional.

---

## GAPS A RESOLVER OBLIGATORIAMENTE

El documento debe resolver con decisiones concretas —no con "depende" o "a determinar"— los siguientes gaps identificados en la documentación existente:

### GAP 1 — Arquitectura técnica de v2
Define la estructura de carpetas y módulos completa del proyecto. Especifica qué módulos son nuevos respecto a v1 y cuáles son reemplazos. El Marco Estratégico menciona 6 nuevos componentes (SignalRanker, NoveltyDetector, ImpactClassifier, MaturityClassifier, CompetitiveMatrixBuilder, ArchitecturePatternBuilder) pero no define su posición en el pipeline ni sus interfaces. Hazlo.

### GAP 2 — Data models completos
Define los schemas Python (dataclasses o Pydantic) de todas las entidades del sistema:
- `RawItem` (output de cada collector)
- `RankedSignal` (output de SignalRanker)
- `Analysis` (output del Analyzer individual)
- `NoveltyResult` (output de NoveltyDetector)
- `ImpactClassification` (output de ImpactClassifier)
- `MaturityAssessment` (output de MaturityClassifier)
- `CompetitiveEntry` (output de CompetitiveMatrixBuilder)
- `ArchitecturePattern` (output de ArchitecturePatternBuilder)
- `DailySynthesis` (output del Synthesizer diario)
- `WeeklySynthesis` (output del Synthesizer semanal)

Cada campo debe tener tipo, descripción y valores posibles si es enum.

### GAP 3 — Prompts completos para todos los procesadores
Define los prompts de sistema y de usuario para cada componente que invoca a Claude:
- Analyzer individual (análisis por item)
- SignalRanker
- NoveltyDetector
- ImpactClassifier
- MaturityClassifier
- CompetitiveMatrixBuilder
- ArchitecturePatternBuilder
- Synthesizer diario
- Synthesizer semanal
- Synthesizer mensual

Para cada prompt especifica: modelo recomendado (Sonnet vs Opus), output esperado (formato JSON si aplica), y longitud máxima del contexto de entrada.

### GAP 4 — Formatos de output completos
Define el formato Markdown exacto de:
- Digest diario (señales críticas, cambios, anomalías)
- Digest semanal (patrones emergentes, cambios de madurez, evolución competitiva)
- Digest mensual (cambios estructurales, consolidación, riesgos)
- Página de topic (por tag)
- Index general
- Competitive matrix (formato tabular y narrativo)
- Architecture patterns (formato de catálogo)

### GAP 5 — Schema ChromaDB v2
Define las colecciones ChromaDB necesarias, el schema de metadata de cada una, y las queries principales que el sistema ejecutará. Considera que v2 tiene dimensiones nuevas (maturity, impact_dimension, signal_type, novelty_score, source_tier) que deben ser consultables.

### GAP 6 — Thresholds y configuración de señal
Define valores concretos (no rangos) para:
- Crecimiento "rápido" en GitHub: X estrellas en Y días
- Crecimiento "rápido" en PyPI/npm: X% de incremento semanal o X descargas adicionales
- "Repo emergente": antigüedad máxima en días
- Umbral de novelty score para considerar un item verdaderamente nuevo
- Score mínimo de relevancia para incluir en digest diario
- Score mínimo de relevancia para incluir en highlights históricos

### GAP 7 — Solución Twitter/X
Evalúa las opciones disponibles sin coste (Nitter RSS, Nitter scraping, snscrape, twint u otras alternativas activas en 2025-2026). Elige una. Documenta sus limitaciones reales y cómo el sistema las maneja (fallback, retry, skip). Si ninguna es fiable, recomienda excluir Twitter de la implementación inicial y documenta en qué fase se revisaría.

### GAP 8 — Compatibilidad ARM64 / Jetson
Para cada dependencia principal, verifica y documenta:
- Si existe imagen Docker oficial ARM64
- Si hay implicaciones de compilación desde fuente
- Si hay alternativas más ligeras para el hardware target
Presta especial atención a: ChromaDB, faster-whisper, PyTorch (para Whisper), librerías de scraping, y cualquier dependencia con extensiones C nativas.

---

## ESTRUCTURA DEL DOCUMENTO A GENERAR

Produce el documento con exactamente esta estructura. Cada sección debe estar completamente desarrollada:

---

### 1. Resumen ejecutivo
Descripción del sistema en 3-4 párrafos. Qué hace, qué no hace y cuáles son las decisiones de diseño más importantes.

### 2. Arquitectura general

#### 2.1 Visión del sistema
Diagrama conceptual en ASCII del pipeline completo de v2, desde fuentes hasta outputs.

#### 2.2 Estructura de carpetas
Árbol completo del proyecto con descripción de cada módulo.

#### 2.3 Componentes y responsabilidades
Descripción funcional de cada componente: qué recibe, qué produce, qué decisiones toma.

#### 2.4 Pipeline de procesamiento
Flujo de datos paso a paso, con tipos de datos en cada transición.

### 3. Fuentes de información

#### 3.1 Tabla maestra de fuentes
Para cada fuente: nombre, categoría, velocidad de señal, tier de prioridad, dificultad de implementación, API/método de acceso, y decisiones tomadas sobre filtros.

#### 3.2 Especificación de cada collector
Para cada uno de los collectors implementados en v2:
- Fuente y URL/endpoint
- Método de acceso (API, RSS, scraping, SDK)
- Parámetros de configuración con valores por defecto
- Filtros y thresholds (valores concretos)
- Schema del `RawItem` que produce
- Manejo de errores y fallbacks
- Limitaciones conocidas

Los collectors a especificar son:
1. GitHub (repos consolidados + repos emergentes + Issues/PRs críticos)
2. ArXiv (sin filtro de citas, con autores conocidos)
3. Blogs y newsletters (RSS, incluyendo Simon Willison)
4. Reddit / Hacker News (con lógica de filtrado revisada)
5. Documentación oficial Anthropic (con detección de cambios)
6. Stack Overflow (preguntas por tags con patrones)
7. PyPI / npm (monitoring de crecimiento de paquetes)
8. Podcasts (descarga + transcripción con faster-whisper)
9. Twitter/X (decisión tomada en GAP 7, con sus limitaciones)
10. Job postings (HN Who's Hiring como mínimo viable)

### 4. Procesamiento con IA

#### 4.1 Cliente Claude (claude_client.py)
Implementación via CLI con manejo de timeouts, reintentos, y parsing de output.

#### 4.2 Signal Ranker
Prompt completo, schema de input/output, lógica de puntuación.

#### 4.3 Novelty Detector
Prompt completo, consulta al vector store para comparación histórica, schema de output.

#### 4.4 Impact Classifier
Prompt completo, taxonomía de dimensiones (API, Infraestructura, Orquestación, Seguridad, Performance, Evaluación, Tooling, Governance, Benchmark), schema de output.

#### 4.5 Maturity Classifier
Prompt completo, escala de madurez (Experimental → Emerging → Production-viable → Consolidated → Declining), criterios de clasificación, schema de output.

#### 4.6 Analyzer individual
Prompt completo, schema de output `Analysis`, decisión de modelo.

#### 4.7 Competitive Matrix Builder
Prompt completo, estructura de la matriz (ecosistemas a comparar, dimensiones), schema de output, frecuencia de actualización.

#### 4.8 Architecture Pattern Builder
Prompt completo, formato del catálogo de patrones, criterios para declarar un patrón emergente, schema de output.

#### 4.9 Synthesizer diario
Prompt completo con contexto de ChromaDB, schema de `DailySynthesis`, decisión de modelo.

#### 4.10 Synthesizer semanal
Prompt completo, inputs requeridos (N días de análisis + vector store), schema de `WeeklySynthesis`.

#### 4.11 Synthesizer mensual
Prompt completo, inputs, schema de `MonthlySynthesis`.

### 5. Almacenamiento

#### 5.1 ChromaDB — Colecciones y schemas
Definición completa de cada colección, campos de metadata, tipos, y valores posibles.

#### 5.2 Queries principales
Las 10-15 queries más importantes que el sistema ejecutará, con pseudocódigo o código Python de ChromaDB client.

#### 5.3 Estructura de archivos Markdown
Árbol completo del directorio `output/` con descripción de cada archivo y su ciclo de vida.

#### 5.4 Formatos de archivo
Formato Markdown exacto (con frontmatter YAML si aplica) de cada tipo de output.

### 6. Orquestación

#### 6.1 Flujo principal diario (pseudocódigo ejecutable)
Función `run_daily()` con manejo de errores, logging, y métricas.

#### 6.2 Flujo semanal y mensual
Cómo se triggerea, qué inputs consume, qué outputs produce.

#### 6.3 Estrategia de manejo de errores
Por tipo de fallo: collector, analyzer, sintetizador, almacenamiento. Qué se registra, qué se omite, qué para la ejecución.

#### 6.4 Logging
Niveles, formato, rotación, y qué se loguea en cada componente.

#### 6.5 Scheduler (cron)
Entradas exactas del crontab para ejecución diaria, semanal y mensual.

### 7. Infraestructura y despliegue

#### 7.1 Compatibilidad ARM64 / Jetson Orin Nano
Tabla de dependencias con estado de compatibilidad, versión recomendada, y notas de instalación.

#### 7.2 Dockerfile
Especificación completa (base image para JetPack 6.x, dependencias del sistema, instalación de faster-whisper con soporte CUDA, Claude CLI, dependencias Python).

#### 7.3 docker-compose.yml
Servicios, volúmenes, variables de entorno, dependencias entre servicios.

#### 7.4 requirements.txt
Listado completo con versiones fijadas y anotación de dependencias ARM64-críticas.

#### 7.5 Consideraciones de rendimiento en Jetson
RAM disponible para ChromaDB, Whisper y Claude CLI simultáneos. Estrategia de gestión de memoria. Estimación de tiempo de ejecución del pipeline completo.

### 8. Configuración

#### 8.1 config.yaml completo
Todos los parámetros configurables con valores por defecto justificados.

#### 8.2 .env
Variables de entorno requeridas con descripción y cómo obtener cada una.

### 9. APIs externas

Tabla completa: API, uso, coste, autenticación, límites, y notas de acceso.

### 10. Fases de implementación

#### Fase 1 — Fundación (semana 1-2)
Lista priorizada de componentes a implementar, criterios de validación, y entregable mínimo funcional.

#### Fase 2 — Señal primaria (semana 3-4)
Componentes adicionales, dependencias entre fases, y criterios de paso a fase 3.

#### Fase 3 — Señal avanzada (mes 2)
Componentes restantes, refinamiento de filtros, y estado de sistema completo.

Para cada fase: qué funciona al final de ella, qué no funciona todavía, y cómo validar que la fase está completa.

### 11. Decisiones de diseño documentadas

Lista de las 10-15 decisiones más importantes tomadas durante el diseño, con:
- La decisión tomada
- Las alternativas consideradas
- El motivo de la elección
- Las consecuencias conocidas

### 12. Riesgos y mitigaciones

Para cada riesgo identificado: probabilidad (alta/media/baja), impacto (alto/medio/bajo), y mitigación concreta.

### 13. Consideraciones futuras

Lo que queda fuera de scope de v2 pero que el diseño actual no debe imposibilitar.

---

## INSTRUCCIONES DE FORMATO Y CALIDAD

- **Extensión:** Sin límite. Prioriza completitud sobre brevedad. Cada sección debe ser autosuficiente.
- **Código:** No incluyas código ni pseudocódigo.
- **Prompts:** Los prompts de Claude deben estar completos, no esquematizados. Deben poder copiarse y usarse directamente.
- **Decisiones:** Cuando hay múltiples opciones, toma una y justifícala. No presentes opciones sin decidir salvo que el gap explícitamente lo requiera.
- **Errores en documentación existente:** Si encuentras inconsistencias, errores técnicos o decisiones que no tienen sentido en el contexto de ARM64/Jetson, corrígelos y documenta el cambio con una nota.
- **Modelos de Claude:** El documento v1 menciona `claude-opus-4-6-20250528` como modelo de síntesis. Verifica si este string de modelo es válido o si debe corregirse. Usa los strings correctos de la API en toda la documentación.
- **Tono:** Técnico y directo. El lector es un ingeniero de software senior. No expliques conceptos básicos.

---

## OUTPUT ESPERADO

Un único documento Markdown, estructurado según el índice anterior, que cumpla simultáneamente las siguientes condiciones:

1. Un ingeniero que lo lea puede implementar el sistema completo sin consultar ninguna otra fuente.
2. Todos los prompts de Claude están listos para usar.
3. Todos los schemas de datos están completamente definidos.
4. Todos los formatos de output están especificados con ejemplos.
5. Todos los gaps listados tienen resolución concreta.
6. La compatibilidad con Jetson Orin Nano está verificada para cada componente.
7. Los thresholds y parámetros tienen valores concretos, no rangos.

---

*Genera el documento completo. No resumas secciones. No uses placeholders como "[desarrollar más adelante]". Si una sección requiere más espacio, úsalo.*
