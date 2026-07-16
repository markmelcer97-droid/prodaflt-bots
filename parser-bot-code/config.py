"""
PRODAFLT Parser Bot — Configuration
Loads environment variables with validation.
"""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Config:
    """Centralized configuration."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Telegram
    PARSER_BOT_TOKEN: str = os.getenv("PARSER_BOT_TOKEN", "")
    TARGET_GROUP_ID: Optional[str] = os.getenv("TARGET_GROUP_ID")

    # Admins (comma-separated telegram IDs)
    ADMIN_IDS: List[int] = [
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]

    # Batch settings
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    BATCH_TIMEOUT_SECONDS: int = int(os.getenv("BATCH_TIMEOUT_SECONDS", "30"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Optional Sentry
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")

    @classmethod
    def validate(cls) -> None:
        """Ensure critical config is present."""
        missing = []
        if not cls.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not cls.PARSER_BOT_TOKEN:
            missing.append("PARSER_BOT_TOKEN")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Copy .env.example to .env and fill values."
            )


# Expose singleton
config = Config()
