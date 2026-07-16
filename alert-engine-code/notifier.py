"""
PRODAFLT Alert Engine — Telegram Notifier
==========================================
Sends formatted alert messages to Telegram admin chat.
Supports HTML formatting, emoji flags, and threaded replies.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

import telegram
from telegram.constants import ParseMode

from config import get_settings
from models import AlertDecision, AlertFlag

logger = logging.getLogger(__name__)
settings = get_settings()

# Emoji mapping for flags
FLAG_EMOJI = {
    AlertFlag.RED: "🚨",
    AlertFlag.GREEN: "✅",
    AlertFlag.YELLOW: "⚠️",
    AlertFlag.WHITE: "⚪",
}

FLAG_ACTION = {
    AlertFlag.RED: "<b>ACTION:</b> KILL / PAUSE immediately",
    AlertFlag.GREEN: "<b>ACTION:</b> SCALE — increase budget",
    AlertFlag.YELLOW: "<b>ACTION:</b> WATCH — monitor closely",
    AlertFlag.WHITE: "<b>ACTION:</b> NONE — normal range",
}


def _build_message(d: AlertDecision) -> str:
    """Build an HTML-formatted Telegram alert message."""
    emoji = FLAG_EMOJI.get(d.flag, "🔔")
    action = FLAG_ACTION.get(d.flag, "Review manually")

    lines = [
        f"{emoji} <b>PRODAFLT ALERT — {d.flag.value}</b> {emoji}",
        "",
        f"<b>Creative Code:</b> <code>{d.creative_code}</code>",
        f"<b>Campaign ID:</b> {d.campaign_id}",
        f"<b>Confidence:</b> {d.confidence}%",
        "",
        f"<b>Decision:</b> {d.decision}",
        f"<b>Reason:</b> {d.reason}",
        "",
        action,
    ]

    if d.triggered_metrics:
        lines.append("")
        lines.append("<b>Triggered Metrics:</b>")
        for k, v in d.triggered_metrics.items():
            lines.append(f"  • {k.upper()}: {v}")

    return "\n".join(lines)


class TelegramNotifier:
    """Wrapper around python-telegram-bot for alert delivery."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_admin_chat_id
        self._bot: Optional[telegram.Bot] = None

    def _get_bot(self) -> telegram.Bot:
        if self._bot is None:
            if not self.token or self.token == "___PASTE_BOT_TOKEN_HERE___":
                raise RuntimeError(
                    "Telegram bot token is not configured. "
                    "Set TELEGRAM_BOT_TOKEN in .env"
                )
            self._bot = telegram.Bot(token=self.token)
        return self._bot

    async def send_alert(self, decision: AlertDecision) -> Optional[int]:
        """
        Send a single alert decision to Telegram.

        Returns:
            Message ID on success, None on skipped (no chat_id).
        """
        if not self.chat_id or self.chat_id == "___PASTE_ADMIN_CHAT_ID_HERE___":
            logger.warning("TELEGRAM_ADMIN_CHAT_ID not set — alert logged but not sent")
            return None

        text = _build_message(decision)
        bot = self._get_bot()

        try:
            msg = await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            logger.info("Alert sent: %s %s (msg_id=%s)", decision.flag.value, decision.creative_code, msg.message_id)
            return msg.message_id
        except telegram.error.TelegramError as exc:
            logger.error("Failed to send Telegram alert: %s", exc)
            return None

    async def send_batch(self, decisions: list[AlertDecision]) -> list[int]:
        """Send multiple alerts and return list of message IDs."""
        sent_ids: list[int] = []
        for d in decisions:
            msg_id = await self.send_alert(d)
            if msg_id:
                sent_ids.append(msg_id)
        return sent_ids
