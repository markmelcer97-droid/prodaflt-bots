"""
PRODAFLT — Application Settings
==============================
Pydantic Settings v2 based configuration manager.
Loads all environment variables with validation, defaults, and type safety.

Usage:
    from config.settings import settings
    db_url = settings.database_url
"""

from __future__ import annotations

import secrets
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    JSON = "json"
    PLAIN = "plain"


class ProjectEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Centralized application settings with env-var binding."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_assignment=True,
    )

    # ================================================================
    # 1. PROJECT METADATA
    # ================================================================
    project_name: str = Field(default="PRODAFLT", alias="PROJECT_NAME")
    project_version: str = Field(default="0.1.0", alias="PROJECT_VERSION")
    project_environment: ProjectEnvironment = Field(
        default=ProjectEnvironment.DEVELOPMENT, alias="PROJECT_ENVIRONMENT"
    )

    @property
    def is_production(self) -> bool:
        return self.project_environment == ProjectEnvironment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.project_environment == ProjectEnvironment.DEVELOPMENT

    # ================================================================
    # 2. DATABASE (Neon PostgreSQL)
    # ================================================================
    database_url: PostgresDsn = Field(
        default="postgresql://user:pass@localhost:5432/prodaflt",
        alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT")

    @property
    def database_url_str(self) -> str:
        return str(self.database_url)

    # ================================================================
    # 3. TELEGRAM BOTS
    # ================================================================
    router_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="ROUTER_BOT_TOKEN"
    )
    researcher_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="RESEARCHER_BOT_TOKEN"
    )
    compliance_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="COMPLIANCE_BOT_TOKEN"
    )
    creative_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="CREATIVE_BOT_TOKEN"
    )
    meta_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="META_BOT_TOKEN"
    )
    data_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="DATA_BOT_TOKEN"
    )
    tech_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="TECH_BOT_TOKEN"
    )
    parser_bot_token: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="PARSER_BOT_TOKEN"
    )

    @field_validator(
        "router_bot_token",
        "researcher_bot_token",
        "compliance_bot_token",
        "creative_bot_token",
        "meta_bot_token",
        "data_bot_token",
        "tech_bot_token",
        "parser_bot_token",
        mode="after",
    )
    @classmethod
    def _validate_bot_token_not_placeholder(
        cls, value: SecretStr
    ) -> SecretStr:
        token = value.get_secret_value()
        if token.startswith("___PASTE") or token == "___PLACEHOLDER___":
            # Allow placeholders in development; raise in production
            return value
        if not token.count(":") == 1 or len(token) < 20:
            raise ValueError("Invalid Telegram bot token format")
        return value

    @property
    def all_bot_tokens(self) -> dict[str, SecretStr]:
        return {
            "router": self.router_bot_token,
            "researcher": self.researcher_bot_token,
            "compliance": self.compliance_bot_token,
            "creative": self.creative_bot_token,
            "meta": self.meta_bot_token,
            "data": self.data_bot_token,
            "tech": self.tech_bot_token,
            "parser": self.parser_bot_token,
        }

    # ================================================================
    # 4. KIMI API
    # ================================================================
    kimi_api_key: SecretStr = Field(
        default=SecretStr("___PLACEHOLDER___"), alias="KIMI_API_KEY"
    )
    kimi_api_base_url: str = Field(
        default="https://api.moonshot.cn/v1", alias="KIMI_API_BASE_URL"
    )
    kimi_model: str = Field(default="moonshot-v1-8k", alias="KIMI_MODEL")
    kimi_request_timeout: int = Field(default=60, alias="KIMI_REQUEST_TIMEOUT")

    # ================================================================
    # 5. FASTAPI SERVICE
    # ================================================================
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")
    api_reload: bool = Field(default=False, alias="API_RELOAD")
    api_debug: bool = Field(default=False, alias="API_DEBUG")
    api_secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
        alias="API_SECRET_KEY",
    )
    api_access_token_expire_minutes: int = Field(
        default=1440, alias="API_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # ================================================================
    # 6. TELEGRAM OAUTH (Web Dashboard)
    # ================================================================
    telegram_bot_username: str = Field(
        default="prodaflt_web_bot", alias="TELEGRAM_BOT_USERNAME"
    )
    telegram_oauth_redirect_url: str = Field(
        default="http://localhost:8000/auth/callback",
        alias="TELEGRAM_OAUTH_REDIRECT_URL",
    )

    # ================================================================
    # 7. REDIS
    # ================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0", alias="REDIS_URL"
    )
    redis_pool_size: int = Field(default=20, alias="REDIS_POOL_SIZE")

    # ================================================================
    # 8. ALERT ENGINE THRESHOLDS
    # ================================================================
    alert_kill_cpi_threshold: float = Field(default=5.0, alias="ALERT_KILL_CPI_THRESHOLD")
    alert_kill_cpc_threshold: float = Field(default=2.5, alias="ALERT_KILL_CPC_THRESHOLD")
    alert_kill_uepc_threshold: float = Field(default=8.0, alias="ALERT_KILL_UEPC_THRESHOLD")
    alert_scale_uepc_threshold: float = Field(default=4.0, alias="ALERT_SCALE_UEPC_THRESHOLD")
    alert_scale_cpi_max: float = Field(default=5.0, alias="ALERT_SCALE_CPI_MAX")
    alert_watch_uepc_min: float = Field(default=6.0, alias="ALERT_WATCH_UEPC_MIN")
    alert_watch_uepc_max: float = Field(default=8.0, alias="ALERT_WATCH_UEPC_MAX")
    alert_confidence_minimum: float = Field(
        default=70.0, alias="ALERT_CONFIDENCE_MINIMUM"
    )

    # ================================================================
    # 9. OCR CONFIGURATION
    # ================================================================
    ocr_engine: Literal["easyocr", "tesseract", "paddleocr"] = Field(
        default="easyocr", alias="OCR_ENGINE"
    )
    ocr_langs: str = Field(default="en,ru", alias="OCR_LANGS")
    ocr_confidence_threshold: float = Field(
        default=0.75, alias="OCR_CONFIDENCE_THRESHOLD"
    )

    # ================================================================
    # 10. EXTERNAL API INTEGRATIONS
    # ================================================================
    keitaro_api_url: str | None = Field(default=None, alias="KEITARO_API_URL")
    keitaro_api_key: SecretStr | None = Field(default=None, alias="KEITARO_API_KEY")

    meta_app_id: str | None = Field(default=None, alias="META_APP_ID")
    meta_app_secret: SecretStr | None = Field(default=None, alias="META_APP_SECRET")
    meta_access_token: SecretStr | None = Field(default=None, alias="META_ACCESS_TOKEN")
    meta_ad_account_id: str | None = Field(default=None, alias="META_AD_ACCOUNT_ID")

    asana_access_token: SecretStr | None = Field(default=None, alias="ASANA_ACCESS_TOKEN")
    asana_workspace_id: str | None = Field(default=None, alias="ASANA_WORKSPACE_ID")

    # ================================================================
    # 11. CONTENT RESEARCH / SCRAPING
    # ================================================================
    proxy_url: str | None = Field(default=None, alias="PROXY_URL")
    scrapy_delay_ms: int = Field(default=1500, alias="SCRAPY_DELAY_MS")
    scrapy_max_retries: int = Field(default=3, alias="SCRAPY_MAX_RETRIES")
    scrapy_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="SCRAPY_USER_AGENT",
    )

    # ================================================================
    # 12. LOGGING
    # ================================================================
    log_level: LogLevel = Field(default=LogLevel.INFO, alias="LOG_LEVEL")
    log_format: LogFormat = Field(default=LogFormat.JSON, alias="LOG_FORMAT")
    log_file_path: Path = Field(default=Path("logs/prodaflt.log"), alias="LOG_FILE_PATH")
    log_max_bytes: int = Field(default=10_485_760, alias="LOG_MAX_BYTES")  # 10 MB
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")

    @field_validator("log_file_path", mode="before")
    @classmethod
    def _ensure_path(cls, value: Any) -> Path:
        if isinstance(value, str):
            return Path(value)
        return value

    # ================================================================
    # 13. PARSER BOT
    # ================================================================
    parser_batch_size: int = Field(default=10, alias="PARSER_BATCH_SIZE")
    parser_batch_timeout_seconds: int = Field(
        default=30, alias="PARSER_BATCH_TIMEOUT_SECONDS"
    )
    parser_duplicate_check_hours: int = Field(
        default=24, alias="PARSER_DUPLICATE_CHECK_HOURS"
    )
    parser_allowed_platforms: str = Field(
        default="instagram,tiktok,youtube,facebook",
        alias="PARSER_ALLOWED_PLATFORMS",
    )

    @property
    def parser_allowed_platforms_list(self) -> list[str]:
        return [p.strip().lower() for p in self.parser_allowed_platforms.split(",")]

    # ================================================================
    # 14. SCHEDULER / HEARTBEAT
    # ================================================================
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")
    morning_report_hour: int = Field(default=7, alias="MORNING_REPORT_HOUR")
    morning_report_minute: int = Field(default=0, alias="MORNING_REPORT_MINUTE")
    daily_brief_hour: int = Field(default=9, alias="DAILY_BRIEF_HOUR")
    daily_brief_minute: int = Field(default=17, alias="DAILY_BRIEF_MINUTE")
    trends_check_hour: int = Field(default=10, alias="TRENDS_CHECK_HOUR")
    trends_check_minute: int = Field(default=0, alias="TRENDS_CHECK_MINUTE")
    compliance_audit_days: str = Field(
        default="Tue,Thu", alias="COMPLIANCE_AUDIT_DAYS"
    )
    compliance_audit_hour: int = Field(default=12, alias="COMPLIANCE_AUDIT_HOUR")
    compliance_audit_minute: int = Field(default=0, alias="COMPLIANCE_AUDIT_MINUTE")
    meta_digest_day: str = Field(default="Mon", alias="META_DIGEST_DAY")
    meta_digest_hour: int = Field(default=10, alias="META_DIGEST_HOUR")
    meta_digest_minute: int = Field(default=0, alias="META_DIGEST_MINUTE")
    infra_audit_day: str = Field(default="Fri", alias="INFRA_AUDIT_DAY")
    infra_audit_hour: int = Field(default=18, alias="INFRA_AUDIT_HOUR")
    infra_audit_minute: int = Field(default=0, alias="INFRA_AUDIT_MINUTE")

    # ================================================================
    # 15. WEB DASHBOARD THEME
    # ================================================================
    dashboard_primary_color: str = Field(default="#D4AF37", alias="DASHBOARD_PRIMARY_COLOR")
    dashboard_bg_color: str = Field(default="#0A1628", alias="DASHBOARD_BG_COLOR")
    dashboard_card_color: str = Field(default="#111D32", alias="DASHBOARD_CARD_COLOR")
    dashboard_success_color: str = Field(default="#4CAF50", alias="DASHBOARD_SUCCESS_COLOR")
    dashboard_danger_color: str = Field(default="#E74C3C", alias="DASHBOARD_DANGER_COLOR")

    # ================================================================
    # DERIVED / COMPUTED PROPERTIES
    # ================================================================

    @property
    def project_root(self) -> Path:
        """Return the absolute project root directory."""
        return Path(__file__).resolve().parent.parent

    @property
    def logs_dir(self) -> Path:
        """Return the logs directory path."""
        path = self.project_root / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def sqlalchemy_echo(self) -> bool:
        """Enable SQL echo only in development."""
        return self.is_development and self.api_debug


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton instance."""
    return Settings()


# Global settings singleton — import this in modules
settings: Settings = get_settings()
