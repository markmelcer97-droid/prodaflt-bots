#!/bin/bash
# ============================================================
# PRODAFLT — Docker Entrypoint
# ============================================================
# Handles migrations, health checks, and service startup modes.
# Usage:
#   docker-entrypoint.sh api      → start FastAPI server
#   docker-entrypoint.sh bot      → start Telegram bot
#   docker-entrypoint.sh worker   → start Celery worker
#   docker-entrypoint.sh scheduler → start APScheduler
#   docker-entrypoint.sh migrate  → run Alembic migrations
#   docker-entrypoint.sh health   → run health check
# ============================================================

set -e

MODE="${1:-api}"

case "$MODE" in
    api)
        echo "[PRODAFLT] Starting FastAPI server on ${API_HOST:-0.0.0.0}:${API_PORT:-8000}"
        exec uvicorn api.main:app \
            --host "${API_HOST:-0.0.0.0}" \
            --port "${API_PORT:-8000}" \
            --workers "${API_WORKERS:-4}" \
            --proxy-headers \
            --access-log
        ;;

    bot)
        echo "[PRODAFLT] Starting Telegram bot: ${BOT_NAME:-parser}"
        exec python -m bots.${BOT_NAME:-parser}
        ;;

    worker)
        echo "[PRODAFLT] Starting Celery worker"
        exec celery -A tasks.celery_app worker \
            --loglevel="${LOG_LEVEL:-INFO}" \
            --concurrency=4 \
            -Q default,parser,analysis,alerts
        ;;

    scheduler)
        echo "[PRODAFLT] Starting Celery beat scheduler"
        exec celery -A tasks.celery_app beat \
            --loglevel="${LOG_LEVEL:-INFO}" \
            --scheduler redbeat.RedBeatScheduler
        ;;

    migrate)
        echo "[PRODAFLT] Running Alembic migrations"
        exec alembic upgrade head
        ;;

    health)
        echo "[PRODAFLT] Health check"
        python -c "
import asyncio, sys
from config.database import init_db, close_db_connections

async def check():
    try:
        await init_db()
        await close_db_connections()
        print('DB connection: OK')
        sys.exit(0)
    except Exception as e:
        print(f'DB connection FAILED: {e}')
        sys.exit(1)

asyncio.run(check())
"
        ;;

    *)
        echo "[PRODAFLT] Unknown mode: $MODE"
        echo "Valid modes: api | bot | worker | scheduler | migrate | health"
        exit 1
        ;;
esac
