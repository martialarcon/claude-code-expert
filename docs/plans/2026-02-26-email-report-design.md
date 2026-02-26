# Diseño: Sistema de Email para Reportes Diarios

**Fecha:** 2026-02-26
**Estado:** Aprobado
**Autor:** Claude + Usuario

---

## Resumen

Sistema de notificaciones por email que envía reportes diarios extensos con síntesis y análisis detallados del ecosistema Claude Code y desarrollo asistido por IA. El contenido se extrae de ChromaDB y se traduce automáticamente al español.

---

## Requisitos

| Aspecto | Decisión |
|---------|----------|
| Propósito | Personal + Equipo |
| Contenido | Síntesis + Análisis detallados |
| Frecuencia | Automático + Manual (CLI) |
| Servicio | Gmail SMTP |
| Formato | HTML responsive |
| Idioma | Español (traducción automática) |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL REPORTER SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │  ChromaDB    │────▶│  Email       │────▶│   Gmail      │     │
│  │  (items +    │     │  Generator   │     │   SMTP       │     │
│  │   analysis)  │     │  (HTML)      │     │              │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│         │                    │                    │              │
│         │                    ▼                    ▼              │
│         │            ┌──────────────┐     ┌──────────────┐      │
│         │            │  Template    │     │  Recipients  │      │
│         │            │  (Jinja2)    │     │  (config)    │      │
│         │            └──────────────┘     └──────────────┘      │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   MODO DE EJECUCIÓN                        │   │
│  ├─────────────────────┬────────────────────────────────────┤   │
│  │  Manual             │  Automático                         │   │
│  │  (CLI command)      │  (integrado en main.py)             │   │
│  └─────────────────────┴────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Componentes

### 1. Email Reporter (`src/notifications/email_reporter.py`)

| Función | Descripción |
|---------|-------------|
| `EmailReporter` | Clase principal |
| `fetch_content()` | Consulta ChromaDB (síntesis + análisis) |
| `translate_to_spanish()` | Traduce contenido usando Claude |
| `render_html()` | Genera HTML desde template Jinja2 |
| `send_email()` | Envía via SMTP |
| `preview()` | Guarda HTML local sin enviar |

### 2. Template HTML (`src/notifications/templates/daily_report.html`)

Template Jinja2 con:
- Diseño responsive (max-width 600px)
- Tema oscuro compatible
- Secciones: Resumen, Destacados, Patrones, Análisis detallados
- Links a fuentes originales

### 3. Configuración (`config.yaml`)

```yaml
notifications:
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_user: "${SMTP_USER}"
    smtp_password: "${SMTP_PASSWORD}"
    use_tls: true
    from_address: "${SMTP_USER}"
    from_name: "AI Architect v2"
    recipients:
      - "tu@email.com"
    auto_send: true
    send_on_modes:
      - "daily"
```

### 4. Variables de Entorno (`.env`)

```bash
SMTP_USER=tuemail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # App Password de Gmail (16 caracteres)
```

---

## Flujo de Datos

```
1. Consulta ChromaDB
   ├── Colección 'synthesis': Buscar por fecha del día
   │   └── Fallback: últimos 7 días si no hay del día
   └── Colección 'analysis': Items del período, ordenados por signal_score

2. Traducción al español
   └── Usar Claude client existente para traducir:
       ├── Síntesis
       ├── Highlights
       ├── Patrones
       └── Insights de cada análisis

3. Renderizado HTML
   └── Template Jinja2 con datos traducidos

4. Envío SMTP
   └── Gmail SMTP con TLS
```

---

## Estructura de Datos

```python
@dataclass
class EmailContent:
    # Desde synthesis
    date: str
    relevance_score: int
    summary: str
    highlights: list[str]
    patterns: list[str]

    # Desde analysis (top items)
    items: list[AnalyzedItem]

@dataclass
class AnalyzedItem:
    title: str
    source: str
    signal_score: int
    summary: str
    key_insights: list[str]
    technical_details: str | None
    relevance_to_claude: str
    actionability: str
    url: str
```

---

## CLI

```bash
# Envío manual
python main.py --mode daily --email

# Solo generar HTML sin enviar (preview)
python main.py --mode daily --email --preview

# Enviar a destinatarios específicos
python main.py --mode daily --email --to colega@empresa.com
```

---

## Archivos Nuevos

```
src/
├── notifications/
│   ├── __init__.py
│   ├── email_reporter.py        # Lógica principal
│   └── templates/
│       └── daily_report.html    # Template Jinja2
```

---

## Dependencias

```txt
# Ya existentes
chromadb
anthropic
jinja2  # Para templates (agregar si no existe)
```

---

## Ventajas sobre el Reporte .md

| Aspecto | Reporte .md | Email desde ChromaDB |
|---------|-------------|----------------------|
| Contenido | Síntesis resumida | Datos crudos + análisis |
| Items | Solo highlights filtrados | TODOS los items analizados |
| Análisis | Resumido en 2-3 oraciones | Análisis profundos completos |
| Distribución | Manual | Automática |

---

## Notas de Implementación

1. **App Password de Gmail:** Requiere generar contraseña de aplicación en `myaccount.google.com/apppasswords`
2. **Traducción:** Usar el Claude client existente (`src/processors/claude_client.py`)
3. **Integración:** Añadir llamada a email_reporter en `main.py` después de la fase de síntesis
4. **Preview:** Guardar HTML en `output/email_preview/` para revisión antes de envío
