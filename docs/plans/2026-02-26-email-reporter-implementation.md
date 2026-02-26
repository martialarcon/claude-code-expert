# Email Reporter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Sistema de notificaciones por email que envía reportes diarios extensos con síntesis y análisis detallados del ecosistema Claude Code, extraídos de ChromaDB y traducidos al español.

**Architecture:** Módulo Python dedicado (`email_reporter.py`) que consulta ChromaDB, traduce contenido con Claude, genera HTML con Jinja2, y envía via Gmail SMTP. Integrado en el pipeline existente con modo automático y manual.

**Tech Stack:** Python 3.10+, ChromaDB, Jinja2, Gmail SMTP, Claude API (traducción)

---

## Task 1: Agregar Jinja2 a dependencias

**Files:**
- Modify: `requirements.txt:32`

**Step 1: Agregar Jinja2**

Añadir después de `python-slugify`:

```txt
# Templating
jinja2>=3.1
```

**Step 2: Instalar dependencia**

Run: `pip install jinja2>=3.1`
Expected: Successfully installed jinja2-3.x.x

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add jinja2 for email templates"
```

---

## Task 2: Crear modelo de configuración Email

**Files:**
- Modify: `src/utils/config.py:127-137`

**Step 1: Agregar EmailConfig y actualizar NotificationsConfig**

Reemplazar las clases `NtfyConfig` y `NotificationsConfig` (líneas 127-137) con:

```python
class NtfyConfig(BaseModel):
    """ntfy.sh notification configuration."""
    enabled: bool = True
    topic: str = "ai-architect"
    url: str = "https://ntfy.sh"


class EmailConfig(BaseModel):
    """Email notification configuration (Gmail SMTP)."""
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""  # From SMTP_USER env var
    smtp_password: str = ""  # From SMTP_PASSWORD env var
    use_tls: bool = True
    from_address: str = ""  # Defaults to smtp_user
    from_name: str = "AI Architect v2"
    recipients: list[str] = []
    auto_send: bool = True
    send_on_modes: list[str] = ["daily"]


class NotificationsConfig(BaseModel):
    """Notifications configuration."""
    ntfy: NtfyConfig = NtfyConfig()
    email: EmailConfig = EmailConfig()
```

**Step 2: Agregar SMTP credentials a Settings**

Agregar a la clase `Settings` (después de línea 164):

```python
    smtp_user: str = ""
    smtp_password: str = ""
```

**Step 3: Commit**

```bash
git add src/utils/config.py
git commit -m "feat: add email configuration model for SMTP"
```

---

## Task 3: Crear estructura de directorios

**Files:**
- Create: `src/notifications/__init__.py`
- Create: `src/notifications/templates/` (directorio)

**Step 1: Crear directorio y __init__.py**

```bash
mkdir -p src/notifications/templates
```

Crear `src/notifications/__init__.py`:

```python
"""
AI Architect v2 - Notifications Module

Email and push notification systems.
"""

from .email_reporter import EmailReporter

__all__ = ["EmailReporter"]
```

**Step 2: Commit**

```bash
git add src/notifications/
git commit -m "feat: create notifications module structure"
```

---

## Task 4: Crear EmailReporter class (parte 1 - data models)

**Files:**
- Create: `src/notifications/email_reporter.py`

**Step 1: Crear archivo con dataclasses y función fetch_content**

```python
"""
AI Architect v2 - Email Reporter

Generates and sends HTML email reports from ChromaDB data.
Content is translated to Spanish before sending.
"""

import os
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..processors.claude_client import ClaudeClient, ClaudeModel
from ..storage.vector_store import VectorStore
from ..utils.config import get_config, get_settings
from ..utils.logger import get_logger

log = get_logger("notifications.email_reporter")


@dataclass
class AnalyzedItem:
    """An item with its analysis for email rendering."""
    title: str
    source: str
    signal_score: int
    summary: str
    key_insights: list[str] = field(default_factory=list)
    technical_details: str | None = None
    relevance_to_claude: str | None = None
    actionability: str | None = None
    url: str | None = None


@dataclass
class EmailContent:
    """Content for the daily email report."""
    date: str
    relevance_score: int
    summary: str
    highlights: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    items: list[AnalyzedItem] = field(default_factory=list)


class EmailReporter:
    """
    Generates and sends HTML email reports from ChromaDB data.

    - Fetches synthesis and analysis from ChromaDB
    - Translates content to Spanish using Claude
    - Renders HTML using Jinja2 templates
    - Sends via Gmail SMTP
    """

    def __init__(
        self,
        template_dir: Path | str | None = None,
        persist_directory: Path | str | None = None,
    ):
        """
        Initialize email reporter.

        Args:
            template_dir: Directory containing Jinja2 templates
            persist_directory: ChromaDB persist directory
        """
        self.config = get_config()
        self.settings = get_settings()
        self.email_config = self.config.notifications.email

        # Template setup
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        self.template_dir = Path(template_dir)

        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Vector store for data fetching
        self.vector_store = VectorStore(persist_directory=persist_directory)

        # Claude client for translation
        self.claude = ClaudeClient(model=ClaudeModel.SONNET)

        log.info(
            "email_reporter_initialized",
            template_dir=str(self.template_dir),
            enabled=self.email_config.enabled,
        )

    def fetch_content(self, days: int = 1) -> EmailContent | None:
        """
        Fetch synthesis and analysis from ChromaDB.

        Args:
            days: Number of days to look back (default: 1 for today)

        Returns:
            EmailContent or None if no data found
        """
        log.info("fetching_content", days=days)

        # Calculate date range
        target_date = datetime.now() - timedelta(days=days)
        date_str = target_date.strftime("%Y-%m-%d")

        try:
            # Fetch synthesis
            synthesis_results = self.vector_store.search(
                query=f"daily synthesis {date_str}",
                collection="synthesis",
                n_results=1,
            )

            if not synthesis_results.get("documents", [[]])[0]:
                log.warning("no_synthesis_found", date=date_str)
                return None

            synthesis_doc = synthesis_results["documents"][0][0]
            synthesis_meta = synthesis_results["metadatas"][0][0]

            # Fetch analysis items
            analysis_results = self.vector_store.search(
                query=f"analysis {date_str}",
                collection="analysis",
                n_results=10,
            )

            # Parse items
            items: list[AnalyzedItem] = []
            docs = analysis_results.get("documents", [[]])[0]
            metas = analysis_results.get("metadatas", [[]])[0]

            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                items.append(self._parse_analysis_item(doc, meta))

            # Build content
            content = EmailContent(
                date=date_str,
                relevance_score=synthesis_meta.get("relevance_score", 5),
                summary=synthesis_meta.get("summary", synthesis_doc[:500]),
                highlights=synthesis_meta.get("highlights", []).split("\n") if isinstance(synthesis_meta.get("highlights"), str) else synthesis_meta.get("highlights", []),
                patterns=synthesis_meta.get("patterns", []).split("\n") if isinstance(synthesis_meta.get("patterns"), str) else synthesis_meta.get("patterns", []),
                items=items,
            )

            log.info("content_fetched", items_count=len(items))
            return content

        except Exception as e:
            log.error("fetch_content_failed", error=str(e)[:200])
            return None

    def _parse_analysis_item(self, doc: str, meta: dict[str, Any]) -> AnalyzedItem:
        """Parse analysis document into AnalyzedItem."""
        return AnalyzedItem(
            title=meta.get("title", "Unknown"),
            source=meta.get("source", "unknown"),
            signal_score=meta.get("signal_score", 5),
            summary=meta.get("summary", doc[:300]),
            key_insights=meta.get("key_insights", []),
            technical_details=meta.get("technical_details"),
            relevance_to_claude=meta.get("relevance_to_claude"),
            actionability=meta.get("actionability"),
            url=meta.get("url"),
        )

    # Continue in next task...
```

**Step 2: Commit**

```bash
git add src/notifications/email_reporter.py
git commit -m "feat: add EmailReporter data models and fetch_content"
```

---

## Task 5: Implementar traducción al español

**Files:**
- Modify: `src/notifications/email_reporter.py` (agregar métodos)

**Step 1: Agregar método translate_to_spanish**

Añadir a la clase `EmailReporter`, después de `_parse_analysis_item`:

```python
    def translate_to_spanish(self, content: EmailContent) -> EmailContent:
        """
        Translate email content to Spanish using Claude.

        Args:
            content: Original content in English

        Returns:
            New EmailContent with translated fields
        """
        log.info("translating_to_spanish")

        # Translate summary
        translated_summary = self._translate_text(content.summary, "resumen ejecutivo")

        # Translate highlights
        translated_highlights = []
        for highlight in content.highlights:
            translated_highlights.append(
                self._translate_text(highlight, "punto destacado")
            )

        # Translate patterns
        translated_patterns = []
        for pattern in content.patterns:
            translated_patterns.append(
                self._translate_text(pattern, "patrón detectado")
            )

        # Translate items
        translated_items = []
        for item in content.items:
            translated_items.append(self._translate_item(item))

        return EmailContent(
            date=content.date,
            relevance_score=content.relevance_score,
            summary=translated_summary,
            highlights=translated_highlights,
            patterns=translated_patterns,
            items=translated_items,
        )

    def _translate_text(self, text: str, context: str = "") -> str:
        """Translate a single text to Spanish."""
        if not text:
            return text

        prompt = f"""Traduce el siguiente texto al español. Mantén el tono técnico y profesional.
Contexto: {context}

Texto a traducir:
{text}

Responde SOLO con la traducción en español, sin explicaciones adicionales."""

        try:
            response = self.claude.complete(prompt, max_tokens=1000)
            return response.content.strip()
        except Exception as e:
            log.warning("translation_failed", context=context, error=str(e)[:100])
            return text  # Return original on failure

    def _translate_item(self, item: AnalyzedItem) -> AnalyzedItem:
        """Translate an AnalyzedItem to Spanish."""
        translated_summary = self._translate_text(item.summary, "resumen de item")

        translated_insights = []
        for insight in item.key_insights:
            translated_insights.append(
                self._translate_text(insight, "insight clave")
            )

        return AnalyzedItem(
            title=item.title,  # Keep original title
            source=item.source,
            signal_score=item.signal_score,
            summary=translated_summary,
            key_insights=translated_insights,
            technical_details=item.technical_details,
            relevance_to_claude=item.relevance_to_claude,
            actionability=item.actionability,
            url=item.url,
        )
```

**Step 2: Commit**

```bash
git add src/notifications/email_reporter.py
git commit -m "feat: add Spanish translation for email content"
```

---

## Task 6: Implementar renderizado HTML

**Files:**
- Modify: `src/notifications/email_reporter.py` (agregar método)
- Create: `src/notifications/templates/daily_report.html`

**Step 1: Agregar método render_html**

Añadir a la clase `EmailReporter`, después de `_translate_item`:

```python
    def render_html(self, content: EmailContent) -> str:
        """
        Render email content as HTML.

        Args:
            content: EmailContent to render

        Returns:
            HTML string
        """
        template = self.env.get_template("daily_report.html")

        html = template.render(
            date=content.date,
            relevance_score=content.relevance_score,
            summary=content.summary,
            highlights=content.highlights,
            patterns=content.patterns,
            items=content.items,
            items_count=len(content.items),
        )

        log.info("html_rendered", length=len(html))
        return html
```

**Step 2: Crear template HTML**

Crear `src/notifications/templates/daily_report.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Architect - Resumen Diario</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f0f1a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h1 style="color: #ffffff; margin: 0 0 8px 0; font-size: 24px;">
                📊 AI Architect - Resumen Diario
            </h1>
            <p style="color: #a0a0a0; margin: 0; font-size: 14px;">
                {{ date }} | Relevancia: {{ relevance_score }}/10
            </p>
            <div style="margin-top: 12px; background: #2a2a4a; border-radius: 6px; height: 8px; overflow: hidden;">
                <div style="background: #4a9eff; height: 100%; width: {{ relevance_score * 10 }}%;"></div>
            </div>
        </div>

        <!-- Resumen Ejecutivo -->
        <div style="background: #1a1a2e; border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h2 style="color: #4a9eff; margin: 0 0 16px 0; font-size: 18px;">
                📋 Resumen Ejecutivo
            </h2>
            <p style="color: #e0e0e0; margin: 0; line-height: 1.6; font-size: 15px;">
                {{ summary }}
            </p>
        </div>

        <!-- Destacados -->
        {% if highlights %}
        <div style="background: #1a1a2e; border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h2 style="color: #ffd700; margin: 0 0 16px 0; font-size: 18px;">
                ⭐ Destacados
            </h2>
            <ul style="color: #e0e0e0; margin: 0; padding-left: 20px; line-height: 1.8;">
                {% for highlight in highlights %}
                <li style="margin-bottom: 8px;">{{ highlight }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        <!-- Patrones -->
        {% if patterns %}
        <div style="background: #1a1a2e; border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h2 style="color: #00d4aa; margin: 0 0 16px 0; font-size: 18px;">
                🔍 Patrones Detectados
            </h2>
            <ul style="color: #e0e0e0; margin: 0; padding-left: 20px; line-height: 1.8;">
                {% for pattern in patterns %}
                <li style="margin-bottom: 8px;">{{ pattern }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        <!-- Análisis Detallados -->
        {% if items %}
        <div style="background: #1a1a2e; border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h2 style="color: #ff6b6b; margin: 0 0 16px 0; font-size: 18px;">
                📝 Análisis Detallados ({{ items_count }} items)
            </h2>

            {% for item in items %}
            <div style="background: #252540; border-radius: 8px; padding: 16px; margin-bottom: 16px; {% if loop.last %}margin-bottom: 0;{% endif %}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <h3 style="color: #ffffff; margin: 0; font-size: 15px; flex: 1;">
                        📌 {{ item.title }}
                    </h3>
                    <span style="background: #4a9eff; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px;">
                        {{ item.signal_score }}/10
                    </span>
                </div>

                <p style="color: #808080; margin: 0 0 12px 0; font-size: 12px;">
                    Fuente: {{ item.source }}
                    {% if item.actionability %} | Accionabilidad: {{ item.actionability }}{% endif %}
                </p>

                <p style="color: #c0c0c0; margin: 0 0 12px 0; line-height: 1.5; font-size: 14px;">
                    {{ item.summary }}
                </p>

                {% if item.key_insights %}
                <div style="margin-top: 12px;">
                    <p style="color: #4a9eff; margin: 0 0 8px 0; font-size: 13px; font-weight: bold;">
                        Insights Clave:
                    </p>
                    <ul style="color: #a0a0a0; margin: 0; padding-left: 16px; font-size: 13px;">
                        {% for insight in item.key_insights %}
                        <li style="margin-bottom: 4px;">{{ insight }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                {% if item.url %}
                <a href="{{ item.url }}" style="color: #4a9eff; font-size: 13px; text-decoration: none; display: inline-block; margin-top: 12px;">
                    Ver fuente 🔗
                </a>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Footer -->
        <div style="text-align: center; padding: 20px 0;">
            <p style="color: #606060; margin: 0; font-size: 12px;">
                🤖 Generado por AI Architect v2 | Jetson Orin Nano
            </p>
        </div>

    </div>
</body>
</html>
```

**Step 3: Commit**

```bash
git add src/notifications/email_reporter.py src/notifications/templates/daily_report.html
git commit -m "feat: add HTML rendering with Jinja2 template"
```

---

## Task 7: Implementar envío SMTP

**Files:**
- Modify: `src/notifications/email_reporter.py` (agregar métodos)

**Step 1: Agregar métodos send_email y preview**

Añadir a la clase `EmailReporter`, después de `render_html`:

```python
    def send_email(
        self,
        html_content: str,
        recipients: list[str] | None = None,
        subject: str | None = None,
    ) -> bool:
        """
        Send HTML email via SMTP.

        Args:
            html_content: HTML content to send
            recipients: Override recipients (optional)
            subject: Override subject line (optional)

        Returns:
            True if sent successfully
        """
        if not self.email_config.enabled:
            log.info("email_disabled")
            return False

        # Get credentials
        smtp_user = self.settings.smtp_user or os.environ.get("SMTP_USER", "")
        smtp_password = self.settings.smtp_password or os.environ.get("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_password:
            log.error("smtp_credentials_missing")
            return False

        # Get recipients
        to_addresses = recipients or self.email_config.recipients
        if not to_addresses:
            log.error("no_recipients_configured")
            return False

        # Build message
        from_addr = self.email_config.from_address or smtp_user
        from_name = self.email_config.from_name

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{from_name} <{from_addr}>"
        msg["To"] = ", ".join(to_addresses)
        msg["Subject"] = subject or f"AI Architect - Resumen Diario {datetime.now().strftime('%d/%m/%Y')}"

        # Attach HTML
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # Send
        try:
            with smtplib.SMTP(
                self.email_config.smtp_host,
                self.email_config.smtp_port,
            ) as server:
                if self.email_config.use_tls:
                    server.starttls()

                server.login(smtp_user, smtp_password)
                server.sendmail(from_addr, to_addresses, msg.as_string())

            log.info(
                "email_sent",
                recipients=to_addresses,
                subject=msg["Subject"],
            )
            return True

        except smtplib.SMTPException as e:
            log.error("smtp_error", error=str(e)[:200])
            return False
        except Exception as e:
            log.error("email_send_failed", error=str(e)[:200])
            return False

    def preview(self, content: EmailContent, output_dir: Path | str = "output/email_preview") -> Path:
        """
        Generate HTML preview without sending.

        Args:
            content: EmailContent to render
            output_dir: Directory for preview file

        Returns:
            Path to generated HTML file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        html = self.render_html(content)
        filename = f"preview_{content.date.replace('-', '')}.html"
        file_path = output_path / filename

        file_path.write_text(html, encoding="utf-8")

        log.info("preview_generated", path=str(file_path))
        return file_path

    def send_daily_report(
        self,
        days: int = 1,
        recipients: list[str] | None = None,
        preview_only: bool = False,
    ) -> bool:
        """
        Full workflow: fetch, translate, render, and send daily report.

        Args:
            days: Days to look back
            recipients: Override recipients
            preview_only: If True, only generate preview

        Returns:
            True if successful
        """
        # Fetch
        content = self.fetch_content(days=days)
        if not content:
            log.warning("no_content_to_send")
            return False

        # Translate
        translated = self.translate_to_spanish(content)

        # Render
        html = self.render_html(translated)

        # Preview or send
        if preview_only:
            path = self.preview(translated)
            print(f"Preview saved to: {path}")
            return True

        return self.send_email(html, recipients=recipients)
```

**Step 2: Commit**

```bash
git add src/notifications/email_reporter.py
git commit -m "feat: add SMTP sending and preview functionality"
```

---

## Task 8: Integrar con main.py

**Files:**
- Modify: `main.py:36-38` (imports)
- Modify: `main.py:306-341` (notification methods)

**Step 1: Agregar import**

Añadir después de línea 37:

```python
from src.notifications.email_reporter import EmailReporter
```

**Step 2: Agregar argumentos CLI**

En la función `main()`, después de línea 372 (parser.add_argument verbose):

```python
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send email report",
    )
    parser.add_argument(
        "--email-preview",
        action="store_true",
        help="Generate email preview without sending",
    )
    parser.add_argument(
        "--email-to",
        type=str,
        help="Override email recipient",
    )
```

**Step 3: Agregar método de email a AIArchitect**

En la clase `AIArchitect`, después de `_notify_complete` (línea 341):

```python
    def _send_email_report(self, preview_only: bool = False, recipients: list[str] | None = None) -> None:
        """Send email report if enabled."""
        email_config = self.config.notifications.email

        if not email_config.enabled:
            log.debug("email_notifications_disabled")
            return

        if self.mode not in email_config.send_on_modes:
            log.debug("mode_not_in_send_on_modes", mode=self.mode)
            return

        try:
            reporter = EmailReporter()
            success = reporter.send_daily_report(
                days=1,
                recipients=recipients,
                preview_only=preview_only,
            )
            if success:
                log.info("email_report_sent", preview=preview_only)
            else:
                log.warning("email_report_failed")
        except Exception as e:
            log.error("email_report_error", error=str(e)[:200])
```

**Step 4: Llamar a email en el pipeline**

En el método `run()`, después de `self._notify_complete(synthesis)` (línea 143):

```python
            # Phase 7: Email Report (if enabled)
            self._send_email_report()
```

**Step 5: Manejar CLI de email al final de main()**

Después de `success = architect.run()` (línea 391):

```python
    # Handle email CLI options
    if args.email or args.email_preview:
        recipients = [args.email_to] if args.email_to else None
        architect._send_email_report(
            preview_only=args.email_preview,
            recipients=recipients,
        )
```

**Step 6: Commit**

```bash
git add main.py
git commit -m "feat: integrate email reporter with main pipeline"
```

---

## Task 9: Actualizar config.yaml

**Files:**
- Modify: `config.yaml`

**Step 1: Agregar sección de email**

En `config.yaml`, dentro de `notifications:`:

```yaml
notifications:
  ntfy:
    enabled: true
    topic: "ai-architect"
    url: "https://ntfy.sh"

  # Email notifications via Gmail SMTP
  email:
    enabled: false  # Set to true after configuring SMTP credentials
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_user: "${SMTP_USER}"
    smtp_password: "${SMTP_PASSWORD}"
    use_tls: true
    from_address: "${SMTP_USER}"
    from_name: "AI Architect v2"
    recipients:
      - "tu@email.com"  # Replace with your email
    auto_send: true
    send_on_modes:
      - "daily"
```

**Step 2: Commit**

```bash
git add config.yaml
git commit -m "feat: add email configuration to config.yaml"
```

---

## Task 10: Agregar variables de entorno ejemplo

**Files:**
- Modify: `.env.example` (si existe) o crear

**Step 1: Agregar SMTP a .env.example**

```bash
# Gmail SMTP for email notifications
SMTP_USER=tuemail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # App Password (16 chars, no spaces)
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add SMTP variables to .env.example"
```

---

## Task 11: Commit final y verificación

**Step 1: Verificar imports**

Run: `python -c "from src.notifications.email_reporter import EmailReporter; print('OK')"`
Expected: OK

**Step 2: Verificar template**

Run: `python -c "from jinja2 import Environment, FileSystemLoader; e = Environment(loader=FileSystemLoader('src/notifications/templates')); t = e.get_template('daily_report.html'); print('OK')"`
Expected: OK

**Step 3: Verificar sintaxis**

Run: `python -m py_compile main.py src/notifications/email_reporter.py src/utils/config.py`
Expected: No output (success)

**Step 4: Commit final**

```bash
git add -A
git status
git commit -m "feat: complete email reporter system for daily reports

- EmailReporter class with ChromaDB data fetching
- Spanish translation via Claude API
- HTML rendering with Jinja2 template
- Gmail SMTP integration
- CLI options: --email, --email-preview, --email-to
- Auto-send on daily mode (configurable)
- Preview mode for testing

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Usage

After implementation:

```bash
# Generate preview (no email sent)
python main.py --mode daily --email-preview

# Send email report manually
python main.py --mode daily --email

# Send to specific recipient
python main.py --mode daily --email --email-to colega@empresa.com

# Auto-send is enabled when:
# - config.yaml: notifications.email.enabled = true
# - .env: SMTP_USER and SMTP_PASSWORD are set
# - Running in a mode listed in send_on_modes
```
