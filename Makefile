# ============================================================
# PRODAFLT — Makefile
# ============================================================
# Common commands for development, testing, deployment.
# Usage: make <target>
# ============================================================

.PHONY: help install install-dev lint format test migrate migrate-revision \
        run-api run-bot run-worker run-scheduler docker-build docker-up \
        docker-down docker-logs seed db-shell health secrets

# ---- Defaults ----
PYTHON := python3
PIP := pip3
VENV := .venv
ENV_FILE := .env

# ============================================================
# HELP
# ============================================================
help: ## Show this help message
	@echo "╔═══════════════════════════════════════════════════════════╗"
	@echo "║           PRODAFLT — Available Commands                   ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================
# INSTALLATION
# ============================================================
install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	$(PIP) install -r requirements-dev.txt

venv: ## Create Python virtual environment
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created in $(VENV)/"
	@echo "Activate: source $(VENV)/bin/activate"

# ============================================================
# CODE QUALITY
# ============================================================
lint: ## Run ruff linter + mypy type checker
	ruff check config/ api/ bots/ tasks/ tests/
	mypy config/ api/ bots/ tasks/

format: ## Auto-format code with black + ruff
	black config/ api/ bots/ tasks/ tests/
	ruff check --fix config/ api/ bots/ tasks/ tests/

# ============================================================
# TESTING
# ============================================================
test: ## Run pytest with coverage
	pytest tests/ -v --cov=config --cov=api --cov-report=term-missing --cov-report=html

test-fast: ## Run tests in parallel (fastest)
	pytest tests/ -v -n auto --tb=short

# ============================================================
# DATABASE
# ============================================================
migrate: ## Run Alembic migrations (upgrade to latest)
	alembic upgrade head

migrate-revision: ## Create new Alembic revision (prompt for message)
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-rollback: ## Rollback one migration
	alembic downgrade -1

migrate-history: ## Show Alembic migration history
	alembic history --verbose

db-shell: ## Open psql shell to Neon database
	psql "$$(grep DATABASE_URL $(ENV_FILE) | cut -d '=' -f2-)"

seed: ## Seed database with initial data
	python scripts/seed_database.py

# ============================================================
# LOCAL DEVELOPMENT
# ============================================================
run-api: ## Start FastAPI development server
	uvicorn api.main:app \
		--host 0.0.0.0 \
		--port 8000 \
		--reload \
		--log-level info

run-bot: ## Start Parser Bot (default bot)
	BOT_NAME=parser python -m bots.parser

run-worker: ## Start Celery worker
	celery -A tasks.celery_app worker \
		--loglevel=INFO \
		--concurrency=4 \
		-Q default,parser,analysis,alerts

run-scheduler: ## Start Celery beat scheduler
	celery -A tasks.celery_app beat \
		--loglevel=INFO \
		--scheduler redbeat.RedBeatScheduler

# ============================================================
# DOCKER
# ============================================================
docker-build: ## Build Docker image
	docker build -t prodaflt:latest .

docker-up: ## Start all services with docker-compose
	docker-compose up -d --build

docker-down: ## Stop all docker-compose services
	docker-compose down

docker-down-volumes: ## Stop services and remove volumes (DATA LOSS)
	docker-compose down -v

docker-logs: ## Tail logs from all docker-compose services
	docker-compose logs -f --tail=100

docker-shell: ## Open bash shell inside API container
	docker-compose exec api /bin/bash

# ============================================================
# UTILITIES
# ============================================================
health: ## Run health check against running API
	curl -s http://localhost:8000/health | python -m json.tool || \
	echo "API not running on localhost:8000"

secrets: ## Generate a secure secret key for API_SECRET_KEY
	@echo "API_SECRET_KEY=$$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

clean: ## Remove Python cache, build artifacts, logs
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
