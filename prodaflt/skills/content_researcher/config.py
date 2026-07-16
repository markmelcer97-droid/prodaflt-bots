"""
PRODAFLT Content Researcher Pipeline — Configuration
Loads secrets from environment variables; validates required keys.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).with_name(".env")
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


def _env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


# ── Database ──
DATABASE_URL: str = _env("DATABASE_URL", required=True)  # type: ignore[assignment]

# ── Telegram ──
ROUTER_BOT_TOKEN: Optional[str] = _env("ROUTER_BOT_TOKEN")
RESEARCH_BOT_TOKEN: Optional[str] = _env("RESEARCH_BOT_TOKEN")
PARSER_BOT_TOKEN: Optional[str] = _env("PARSER_BOT_TOKEN")

# ── Kimi AI ──
KIMI_API_KEY: Optional[str] = _env("KIMI_API_KEY")
KIMI_BASE_URL: str = _env("KIMI_BASE_URL", "https://api.moonshot.cn/v1")  # type: ignore[assignment]

# ── Scraping ──
INSTAGRAM_SESSION_ID: Optional[str] = _env("INSTAGRAM_SESSION_ID")
TIKTOK_SESSION_ID: Optional[str] = _env("TIKTOK_SESSION_ID")
YOUTUBE_API_KEY: Optional[str] = _env("YOUTUBE_API_KEY")

# ── Paths ──
MEDIA_DOWNLOAD_PATH: Path = Path(_env("MEDIA_DOWNLOAD_PATH", "./downloads"))  # type: ignore[assignment]
FFMPEG_PATH: str = _env("FFMPEG_PATH", "ffmpeg")  # type: ignore[assignment]
WHISPER_MODEL: str = _env("WHISPER_MODEL", "base")  # type: ignore[assignment]

# ── Pipeline tuning ──
DAILY_LINK_LIMIT: int = int(_env("DAILY_LINK_LIMIT", "15"))  # type: ignore[assignment]
SCORE_THRESHOLD: float = float(_env("SCORE_THRESHOLD", "6.0"))  # type: ignore[assignment]
MIN_VIRALITY_SCORE: int = int(_env("MIN_VIRALITY_SCORE", "5"))  # type: ignore[assignment]

# ── Alerts ──
ALERT_WEBHOOK_URL: Optional[str] = _env("ALERT_WEBHOOK_URL")

# Ensure download directory exists
MEDIA_DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
