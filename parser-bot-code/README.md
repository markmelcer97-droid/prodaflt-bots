# PRODAFLT Parser Bot

Telegram bot that collects gambling creative reference links from group chats, buffers them, and writes to Neon PostgreSQL in batches.

## Features

- **Group chat link collection** — Team drops URLs naturally, bot captures silently
- **Smart batching** — Flushes every 10 messages or 30 seconds (configurable)
- **Platform detection** — Auto-detects Instagram, TikTok, YouTube, Facebook, Twitter, etc.
- **Deduplication** — Skips duplicate URLs before DB insert
- **User auto-registration** — Creates `users` record on first interaction
- **Admin commands** — `/stats`, `/flush`
- **Production ready** — Async SQLAlchemy, connection pooling, Sentry support

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment template and fill values
cp .env.example .env
# Edit .env with real tokens (never commit .env!)

# 3. Run
python bot.py
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Neon PostgreSQL connection string | `postgresql+asyncpg://...` |
| `PARSER_BOT_TOKEN` | Token from @BotFather | `123456:ABC-DEF...` |
| `TARGET_GROUP_ID` | Group chat ID (optional, for logging) | `-1001234567890` |
| `ADMIN_IDS` | Comma-separated Telegram user IDs for admin commands | `12345678,87654321` |
| `BATCH_SIZE` | Max items before flush | `10` |
| `BATCH_TIMEOUT_SECONDS` | Max seconds before flush | `30` |

## Database Schema

Uses existing PRODAFLT tables (`users`, `links`). See `../migrations/001_prodaflt_tables.sql`.

## Docker

```bash
docker build -t prodaflt-parser .
docker run --env-file .env prodaflt-parser
```

## Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/start` | Anyone | Welcome + help |
| `/stats` | Anyone | Link counts (total, pending, analyzed, 24h) |
| `/flush` | Admin only | Force immediate batch flush |

## Architecture Notes

- **BatchBuffer** uses `asyncio.Queue` + background worker for non-blocking ingestion
- **Link enrichment** (title fetch) is best-effort and skipped for social platforms to avoid blocks
- **Graceful shutdown** flushes remaining buffer before exit

## License

Internal — PRODAFLT team only.
