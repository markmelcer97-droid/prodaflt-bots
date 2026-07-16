"""
PRODAFLT — Logging Configuration
================================
Structured logging with JSON/plain output, rotation, and filtering.
Production: JSON → centralized log aggregation (Loki, Datadog, etc.)
Development: plain colored text → stdout

Usage:
    from config.logging_config import get_logger
    logger = get_logger("prodaFLT.parser")
    logger.info("Link parsed", extra={"link_id": 42, "platform": "tiktok"})
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import settings


# ------------------------------------------------------------------
# JSON Formatter (structured logs for production)
# ------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Merge any `extra={...}` fields passed to the logger
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
            }:
                log_obj[key] = value

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str, ensure_ascii=False)


# ------------------------------------------------------------------
# Plain Formatter (human-readable for development)
# ------------------------------------------------------------------
class ColoredFormatter(logging.Formatter):
    """Colored plain-text formatter for terminal output."""

    COLORS = {
        "DEBUG": "\033[36m",      # cyan
        "INFO": "\033[32m",       # green
        "WARNING": "\033[33m",    # yellow
        "ERROR": "\033[31m",      # red
        "CRITICAL": "\033[35m",   # magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


# ------------------------------------------------------------------
# Configure Root Logger
# ------------------------------------------------------------------
def configure_logging() -> None:
    """Set up handlers, formatters, and levels for the root logger."""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.value)

    # Remove existing handlers to avoid duplicates on re-configuration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # ---- Console handler (always present) ----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level.value)

    if settings.log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        fmt = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(module)s:%(lineno)d | %(message)s"
        )
        console_handler.setFormatter(ColoredFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger.addHandler(console_handler)

    # ---- File handler (rotating) ----
    log_dir = settings.logs_dir
    log_file = log_dir / settings.log_file_path.name

    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(settings.log_level.value)
    # File always gets JSON for structured ingestion
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # Silence overly chatty third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)


# ------------------------------------------------------------------
# Convenience Getter
# ------------------------------------------------------------------
_logger_cache: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Return a named logger; configure logging on first call."""
    if not _logger_cache:
        configure_logging()
    if name not in _logger_cache:
        _logger_cache[name] = logging.getLogger(name)
    return _logger_cache[name]
