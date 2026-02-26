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
