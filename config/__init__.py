"""
PRODAFLT — Configuration Package
=================================
Centralized configuration, database, and logging for the
PRODAFLT gambling creative production system.

Modules:
    settings       — Pydantic-based env-var configuration
    database       — SQLAlchemy 2.0 engines + session factories
    logging_config — Structured JSON / colored plain logging
"""

from config.database import (
    AsyncSessionLocal,
    Base,
    SessionLocal,
    close_db_connections,
    get_db,
    get_db_context,
    get_sync_db,
    init_db,
)
from config.logging_config import configure_logging, get_logger
from config.settings import Settings, get_settings, settings

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "settings",
    # Database
    "Base",
    "AsyncSessionLocal",
    "SessionLocal",
    "get_db",
    "get_sync_db",
    "get_db_context",
    "close_db_connections",
    "init_db",
    # Logging
    "configure_logging",
    "get_logger",
]
