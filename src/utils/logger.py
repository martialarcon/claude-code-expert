"""
AI Architect v2 - Structured Logging

Provides JSON structured logging with component-aware formatting.
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Any

import structlog
from structlog.types import Processor

from .config import get_config


def add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add ISO timestamp to log entry."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_component(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Ensure component field exists."""
    if "component" not in event_dict:
        event_dict["component"] = "unknown"
    return event_dict


def get_log_level() -> str:
    """Get log level from configuration."""
    config = get_config()
    return config.logging.level.upper()


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    Call this once at application startup.
    """
    config = get_config()
    log_level = get_log_level()
    use_json = config.logging.format == "json"

    # Shared processors for all loggers
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        add_component,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if use_json:
        # JSON output
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Human-readable console output
        shared_processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(component: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger bound to a specific component.

    Args:
        component: Component name (e.g., "collector.github", "analyzer")

    Returns:
        Bound logger instance

    Example:
        >>> log = get_logger("collector.github")
        >>> log.info("items_collected", count=10, duration_seconds=5.2)
    """
    return structlog.get_logger().bind(component=component)


# Convenience function for creating component loggers
def logger_for(module_name: str) -> structlog.stdlib.BoundLogger:
    """
    Create a logger for a module.

    Usage:
        log = logger_for(__name__)  # e.g., "src.collectors.github"
        log.info("starting_collection", source="github")
    """
    # Extract component from module path
    # e.g., "src.collectors.github_repos" -> "collector.github_repos"
    parts = module_name.split(".")
    if len(parts) >= 2:
        component_type = parts[1].rstrip("s")  # "collectors" -> "collector"
        component_name = parts[2] if len(parts) > 2 else parts[1]
        component = f"{component_type}.{component_name}"
    else:
        component = module_name

    return get_logger(component)
