# PRODAFLT — FastAPI Endpoints

REST API for the gambling creative production system. Built with FastAPI + async SQLAlchemy + Neon PostgreSQL.

## Quick Start

```bash
# 1. Copy env template and fill in real values
cp .env.example .env

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture

```
app/
├── database.py          # Async SQLAlchemy engine + session
├── models.py            # Pydantic request/response schemas
├── dependencies.py      # Shared deps + Alert Engine logic
├── main.py              # FastAPI app factory
└── routers/
    ├── users.py           # CRUD for team members
    ├── links.py           # Content pipeline entry
    ├── content_analysis.py # Researcher + Compliance results
    ├── tz_specs.py        # Creative briefs (frame-by-frame TZ)
    ├── patterns.py        # Viral pattern registry
    ├── campaign_metrics.py # Performance data + derived metrics
    ├── alerts.py          # Alert Engine (RED/GREEN/YELLOW/WHITE)
    └── stats.py           # Dashboard aggregations + health
```

## API Endpoints

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/users` | Create team member |
| GET    | `/api/users` | List with filters |
| GET    | `/api/users/{id}` | Get user |
| PATCH  | `/api/users/{id}` | Update user |
| DELETE | `/api/users/{id}` | Deactivate user |

### Links
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/links` | Add link (Parser Bot) |
| GET    | `/api/links` | List + filter |
| GET    | `/api/links/{id}` | Get link |
| PATCH  | `/api/links/{id}` | Update status |
| DELETE | `/api/links/{id}` | Delete link |
| POST   | `/api/links/{id}/analyze` | Trigger analysis |

### Content Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/content-analysis` | Submit analysis |
| GET    | `/api/content-analysis` | List records |
| GET    | `/api/content-analysis/{id}` | Get record |
| PATCH  | `/api/content-analysis/{id}` | Update |
| DELETE | `/api/content-analysis/{id}` | Delete |

### TZ Specs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/tz` | Create brief |
| GET    | `/api/tz` | List briefs |
| GET    | `/api/tz/{id}` | Get brief |
| PATCH  | `/api/tz/{id}` | Update brief |
| DELETE | `/api/tz/{id}` | Delete brief |
| POST   | `/api/tz/{id}/approve` | Approve |
| POST   | `/api/tz/{id}/reject` | Reject |

### Patterns
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/patterns` | Register pattern |
| GET    | `/api/patterns` | List patterns |
| GET    | `/api/patterns/{id}` | Get pattern |
| PATCH  | `/api/patterns/{id}` | Update |
| DELETE | `/api/patterns/{id}` | Delete |

### Campaign Metrics
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/metrics` | Upload metrics |
| GET    | `/api/metrics` | List metrics |
| GET    | `/api/metrics/top` | Top creatives |
| GET    | `/api/metrics/{id}` | Get record |
| PATCH  | `/api/metrics/{id}` | Update |
| DELETE | `/api/metrics/{id}` | Delete |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/alerts/evaluate` | Run Alert Engine (no DB write) |
| POST   | `/api/alerts` | Log alert |
| GET    | `/api/alerts/active` | Active alerts |
| GET    | `/api/alerts` | All alerts |
| GET    | `/api/alerts/{id}` | Get alert |
| PATCH  | `/api/alerts/{id}` | Update |
| POST   | `/api/alerts/{id}/acknowledge` | Acknowledge |
| POST   | `/api/alerts/{id}/resolve` | Resolve |
| DELETE | `/api/alerts/{id}` | Delete |

### Stats / Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/stats/dashboard` | Aggregated KPIs |
| GET    | `/api/stats/links/daily` | Daily link volume |
| GET    | `/api/stats/team/activity` | Top contributors |
| GET    | `/api/stats/pipeline` | Pipeline status |
| GET    | `/api/stats/health` | Health check |

## Alert Engine Thresholds

| Flag | Condition | Decision |
|------|-----------|----------|
| **RED** | CPI ≥ $5 OR CPC ≥ $2.5 OR uEPC ≥ $8 | KILL |
| **GREEN** | uEPC < $4 AND CPI ≤ $5 | SCALE |
| **YELLOW** | uEPC ∈ [$6, $8) | WATCH |
| **WHITE** | Spend < $12 or Clicks < 8 | INSUFFICIENT |

Thresholds are loaded from environment variables (see `.env.example`).

## Environment Variables

All sensitive values use `___PASTE_HERE___` placeholders in `.env.example`. **Never commit real tokens.**

Key vars:
- `DATABASE_URL` — Neon PostgreSQL async connection
- `DATABASE_URL_SYNC` — Sync driver for migrations
- `BOT_TOKEN_*` — 8 Telegram bot tokens
- `THRESHOLD_*` — Alert Engine business rules
- `API_SECRET_KEY` — JWT / API signing
- `API_ALLOWED_ORIGINS` — CORS whitelist

## Integration Points

| Consumer | Endpoint Used | Purpose |
|----------|--------------|---------|
| Parser Bot | `POST /api/links` | Batch-write links from group chat |
| Researcher | `GET /api/links?status=pending` | Pick up unanalyzed links |
| Researcher | `POST /api/content-analysis` | Write analysis results |
| Compliance | `PATCH /api/content-analysis/{id}` | Update compliance_status |
| Creative | `POST /api/tz` | Create frame-by-frame briefs |
| Data Analyst | `POST /api/metrics` | Upload Keitaro / Meta metrics |
| Data Analyst | `POST /api/alerts/evaluate` | Run alert rules |
| Data Analyst | `POST /api/alerts` | Log triggered alerts |
| Web Dashboard | `GET /api/stats/dashboard` | Render KPI cards |
| Web Dashboard | `GET /api/alerts/active` | Show alert banners |

## Running Tests (placeholder)

```bash
pytest tests/ -v
```

## Deployment

```bash
# Docker (recommended)
docker build -t prodaflt-api .
docker run -p 8000:8000 --env-file .env prodaflt-api

# Railway (one-click)
railway up
```
