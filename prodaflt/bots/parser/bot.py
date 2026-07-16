"""
PRODAFLT Parser Bot — Main Entry Point
Telegram bot that collects links from group chats,
buffers them, and flushes to PostgreSQL in batches.
"""

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import config
from database import get_db, get_or_create_user, get_links_stats, insert_links_batch
from link_parser import extract_urls, enrich_link_data

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("parser_bot")

# ------------------------------------------------------------------
# Sentry (optional)
# ------------------------------------------------------------------

try:
    import sentry_sdk
    if config.SENTRY_DSN:
        sentry_sdk.init(dsn=config.SENTRY_DSN)
        logger.info("Sentry initialized")
except ImportError:
    pass

# ------------------------------------------------------------------
# Batch buffer
# ------------------------------------------------------------------

@dataclass
class LinkBufferItem:
    url_data: Dict
    user_tg_id: int
    username: str
    first_name: Optional[str]
    received_at: datetime = field(default_factory=datetime.utcnow)


class BatchBuffer:
    """
    Thread-safe async buffer for batching link inserts.
    Flushes when batch_size reached OR timeout expires.
    """

    def __init__(self, size: int, timeout_sec: int):
        self.size = size
        self.timeout = timeout_sec
        self._queue: asyncio.Queue[LinkBufferItem] = asyncio.Queue()
        self._flush_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._http_session: Optional[aiohttp.ClientSession] = None

    async def start(self, app: Application) -> None:
        """Start background flush worker."""
        self._http_session = aiohttp.ClientSession()
        self._task = asyncio.create_task(self._worker())
        logger.info(
            "BatchBuffer started (size=%d, timeout=%ds)", self.size, self.timeout
        )

    async def stop(self) -> None:
        """Graceful shutdown: flush remaining and close session."""
        if self._task:
            self._flush_event.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._force_flush()
        if self._http_session:
            await self._http_session.close()
        logger.info("BatchBuffer stopped")

    async def put(self, item: LinkBufferItem) -> None:
        """Add item to buffer."""
        await self._queue.put(item)
        logger.debug("Buffered link from @%s", item.username)

    async def _worker(self) -> None:
        """Background loop: flush on size or timeout."""
        while True:
            try:
                await asyncio.wait_for(
                    self._flush_event.wait(), timeout=self.timeout
                )
                self._flush_event.clear()
            except asyncio.TimeoutError:
                pass

            await self._force_flush()

    async def _force_flush(self) -> None:
        """Drain queue and write to DB."""
        items: List[LinkBufferItem] = []
        while not self._queue.empty() and len(items) < self.size:
            try:
                items.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if not items:
            return

        logger.info("Flushing %d links to database...", len(items))

        session = self._http_session
        close_temp_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_temp_session = True

        try:
            records = []
            for item in items:
                async with get_db() as db:
                    user = await get_or_create_user(
                        db,
                        telegram_id=item.user_tg_id,
                        username=item.username,
                        first_name=item.first_name,
                    )
                    user_id = user.id

                enriched = await enrich_link_data(session, item.url_data["url"])
                enriched["added_by"] = user_id
                records.append(enriched)

            if not records:
                return

            async with get_db() as db:
                inserted = await insert_links_batch(db, records)

            logger.info("Flush complete: %d/%d inserted (rest were dupes)",
                        inserted, len(records))
        finally:
            if close_temp_session:
                await session.close()


# Global buffer instance
buffer = BatchBuffer(size=config.BATCH_SIZE, timeout_sec=config.BATCH_TIMEOUT_SECONDS)

# ------------------------------------------------------------------
# Handlers
# ------------------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — welcome message."""
    await update.effective_message.reply_text(
        "🤖 *PRODAFLT Parser Bot*\n\n"
        "Drop links in this chat and I'll collect them into the database.\n"
        "Commands:\n"
        "• /stats — link statistics\n"
        "• /flush — force batch flush (admin only)",
        parse_mode="Markdown",
    )


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stats — show link counts."""
    async with get_db() as db:
        stats = await get_links_stats(db)

    text = (
        f"📊 *Link Statistics*\n\n"
        f"Total: `{stats['total']}`\n"
        f"New: `{stats['new']}`\n"
        f"Analyzed: `{stats['analyzed']}`\n"
        f"Rejected: `{stats['rejected']}`\n"
        f"Last 24h: `{stats['last_24h']}`"
    )
        f"📊 *Link Statistics*\n\n"
        f"Total: `{stats['total']}`\n"
        f"Pending: `{stats['pending']}`\n"
        f"Analyzed: `{stats['analyzed']}`\n"
        f"Failed: `{stats['failed']}`\n"
        f"Last 24h: `{stats['last_24h']}`"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


async def flush_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/flush — admin-only force flush."""
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.effective_message.reply_text("⛔ Admin only.")
        return

    await update.effective_message.reply_text("🔄 Forcing flush...")
    await buffer._force_flush()
    await update.effective_message.reply_text("✅ Flush complete.")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle any text message containing URLs.
    Works in groups and private chats.
    """
    if not update.effective_message or not update.effective_message.text:
        return

    text = update.effective_message.text
    user = update.effective_user

    urls = extract_urls(text)
    if not urls:
        return  # ignore messages without links

    logger.info("Got %d URL(s) from @%s", len(urls), user.username or user.id)

    for url in urls:
        item = LinkBufferItem(
            url_data={"url": url},
            user_tg_id=user.id,
            username=user.username or f"user_{user.id}",
            first_name=user.first_name,
        )
        await buffer.put(item)

    try:
        await update.effective_message.set_reaction("👀")
    except Exception:
        pass


# ------------------------------------------------------------------
# Lifecycle hooks
# ------------------------------------------------------------------

async def post_init(app: Application) -> None:
    await buffer.start(app)


async def post_shutdown(app: Application) -> None:
    await buffer.stop()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    config.validate()

    app = (
        ApplicationBuilder()
        .token(config.PARSER_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("flush", flush_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    logger.info("Parser Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
