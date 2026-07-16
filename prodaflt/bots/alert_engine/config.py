"""
PRODAFLT Alert Engine — Configuration
======================================
Loads settings from environment variables with sensible defaults.
"""
from __future__ import annotations

import os
from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://localhost/prodaflt"

    # Telegram
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    # Engine loop interval (seconds)
    alert_engine_interval_seconds: int = 300

    # Minimum data thresholds before we evaluate alerts
    min_spend_for_alert_usd: Decimal = Decimal("20.00")
    min_clicks_for_alert: int = 10
    min_installs_for_alert: int = 3

    # Kill / Scale thresholds
    threshold_cpc_kill: Decimal = Decimal("2.50")
    threshold_cpi_kill: Decimal = Decimal("5.00")
    threshold_uepc_kill: Decimal = Decimal("8.00")
    threshold_uepc_scale: Decimal = Decimal("4.00")
    threshold_roi_kill: Decimal = Decimal("-0.50")

    # Confidence tuning
    confidence_high_sample_min_spend: Decimal = Decimal("100.00")
    confidence_high_sample_min_clicks: int = 50
    confidence_high_sample_min_installs: int = 10

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
