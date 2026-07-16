"""
PRODAFLT — Project Config Files Component
=========================================

This directory contains the foundational configuration layer for the
PRODAFLT gambling creative production system.

Components
----------

| File / Dir            | Purpose                                              |
|-----------------------|------------------------------------------------------|
| `.env.example`        | Template for all environment variables (NO secrets)  |
| `config/settings.py`  | Pydantic Settings — typed, validated, cached         |
| `config/database.py`  | SQLAlchemy 2.0 sync + async engines & sessions       |
| `config/logging_config.py` | Structured JSON / colored console logging       |
| `config/__init__.py`  | Package exports for clean imports                    |
| `models/__init__.py`  | SQLAlchemy ORM models for all PRODAFLT tables        |
| `requirements.txt`    | Production Python dependencies                       |
| `requirements-dev.txt`| Development + lint + test dependencies               |
| `pyproject.toml`      | Project metadata + tool configs (black, ruff, mypy)  |
| `Dockerfile`          | Multi-stage production build                         |
| `docker-compose.yml`  | Local dev stack (API + Postgres + Redis + Workers)   |
| `docker-entrypoint.sh`| Container entrypoint (api | bot | worker | migrate)  |
| `Makefile`            | Common commands: install, test, run, docker, migrate |
| `.gitignore`          | Excludes .env, __pycache__, logs, etc.               |
| `scripts/health_check.py` | Standalone dependency health verification        |
| `scripts/seed_database.py`| Seeds patterns + users for development           |

Quick Start
-----------

1. Copy environment template and fill in real values::

       cp .env.example .env
       # Edit .env with your tokens, URLs, and keys

2. Install dependencies::

       make install-dev

3. Run health check::

       python scripts/health_check.py

4. Start the API locally::

       make run-api

5. Or use Docker Compose::

       make docker-up

Environment Variables
---------------------

All sensitive values use placeholders::

    ROUTER_BOT_TOKEN=___PASTE_ROUTER_BOT_TOKEN_HERE___
    KIMI_API_KEY=___PASTE_KIMI_API_KEY_HERE___
    DATABASE_URL=___PASTE_DATABASE_URL_HERE___

**NEVER commit `.env` to version control.** `.gitignore` blocks it.

Database
--------

- **Engine:** Neon Serverless PostgreSQL
- **ORM:** SQLAlchemy 2.0 with asyncpg
- **Migrations:** Alembic (run via `make migrate`)
- **Models:** See `models/__init__.py` — 7 tables with FKs and relationships

Logging
-------

- **Production:** JSON logs → file rotation → log aggregation
- **Development:** Colored plain text → stdout
- **Level:** Controlled by `LOG_LEVEL` env var
- **Location:** `logs/prodaflt.log` (created automatically)

Security Notes
--------------

- Bot tokens live ONLY in `.env` (never in code)
- `pydantic.SecretStr` masks values in logs and traces
- Docker runs as non-root user (`prodaflt`)
- `.gitignore` blocks `.env`, `*.pem`, `secrets/`

Makefile Targets
----------------

| Target           | Action                                |
|------------------|---------------------------------------|
| `make install`   | Install production deps               |
| `make install-dev` | Install dev deps                    |
| `make test`      | Run pytest with coverage              |
| `make lint`      | Run ruff + mypy                       |
| `make format`    | Auto-format with black + ruff         |
| `make migrate`   | Run Alembic migrations                |
| `make run-api`   | Start FastAPI dev server              |
| `make run-bot`   | Start Parser Bot                      |
| `make docker-up` | Start full Docker stack               |
| `make health`    | Check running API health              |
| `make secrets`   | Generate a secure API_SECRET_KEY      |

Architecture Context
--------------------

This config layer is **Phase 0 (Foundation)** of the PRODAFLT build:

    Phase 0 → Config + DB + Router + Parser   ← YOU ARE HERE
    Phase 1 → Domain Agents (6 Claw bots)
    Phase 2 → FastAPI + Skills
    Phase 3 → Automation + HEARTBEAT
    Phase 4 → Web Dashboard (React)
    Phase 5 → External Integrations (Keitaro, Meta, Asana)
    Phase 6 → Testing + Go-Live

For the full architecture, see `prodaflt_unified_architecture.md`.
"""
