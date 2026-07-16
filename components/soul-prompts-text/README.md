# PRODAFLT — Soul Prompts Text Component

## Overview

`soul-prompts-text` is the **identity layer** of the PRODAFLT gambling creative production system. It stores, versions, and serves the "soul prompts" (system prompts) for all 7 AI agents.

## Agents

| Agent Key | Name | Role | HEARTBEAT |
|-----------|------|------|-----------|
| `router` | Router | Dispatcher | daily 09:17 |
| `researcher` | Researcher | Content Researcher | daily 10:00 |
| `compliance` | Compliance | Compliance Officer | Tue,Thu 12:00 |
| `creative` | Creative | Creative Producer | Mon 09:00 |
| `meta_master` | Meta Master | Meta Ads Expert | Mon 10:00 |
| `data_analyst` | Data Analyst | Data Analyst | daily 07:00,18:00 |
| `tech_lead` | Tech Lead | Tech Lead | Fri 18:00 |

## Directory Layout

```
soul-prompts-text/
├── prompts/                    # Markdown soul prompts (one per agent)
│   ├── router_soul.md
│   ├── researcher_soul.md
│   ├── compliance_soul.md
│   ├── creative_soul.md
│   ├── meta_master_soul.md
│   ├── data_analyst_soul.md
│   └── tech_lead_soul.md
├── src/
│   ├── __init__.py
│   ├── loader.py               # File-based prompt loader
│   ├── db.py                   # Async PostgreSQL sync
│   └── api.py                  # FastAPI service
├── tests/
│   └── test_loader.py
├── .env.example                # Placeholder config (NEVER put real tokens)
├── requirements.txt
└── README.md                   # This file
```

## Quick Start

### 1. Install Dependencies

```bash
cd components/soul-prompts-text
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with real values (tokens from @BotFather, DB password, etc.)
```

### 3. Run Tests

```bash
pytest tests/
```

### 4. Run API Server

```bash
uvicorn src.api:app --reload --port 8000
```

Endpoints:
- `GET  /health` — health check
- `GET  /agents` — list all agents
- `GET  /agents/{key}` — get prompt content
- `POST /sync` — sync file prompts to DB

### 5. Use in Code

```python
from src.loader import SoulPromptLoader, get_prompt

# Load all prompts
loader = SoulPromptLoader()
router = loader.load("router")
print(router.content)

# Render for Kimi Claw ingestion
claw_text = loader.render_for_claw("creative", extra_context="New offer: CasinoX")

# Or use singleton helper
prompt = get_prompt("data_analyst")
```

## Database Sync

To persist prompts in PostgreSQL (for versioning and remote access):

```python
import asyncio
from src.loader import SoulPromptLoader
from src.db import SoulPromptDB

async def main():
    loader = SoulPromptLoader()
    db = SoulPromptDB()  # reads DATABASE_URL from env
    await db.connect()
    await db.sync_from_loader(loader)
    await db.close()

asyncio.run(main())
```

## Prompt Structure

Each `.md` file follows this structure:

```markdown
# ============================================================
# PRODAFLT — Soul Prompt: [Agent Name]
# Role: [Role]
# Version: [SemVer]
# ============================================================

## IDENTITY
Who the agent is, team context, system context.

## CORE RULES
1. Rule one
2. Rule two
3. HEARTBEAT schedule

## [DOMAIN SECTIONS]
Workflows, formats, thresholds specific to the agent.

## DATABASE INTEGRATION
SQL examples, table references.

## HEARTBEAT: [NAME] ([Schedule])
Template for scheduled report.

## STYLE
Communication style guidelines.
```

## Versioning

- Prompt versions are extracted from the `Version:` header in each `.md` file.
- The DB `agents` table tracks `soul_version` and `updated_at`.
- To update a prompt: edit the `.md` file, bump the version, run `POST /sync`.

## Security

- **NEVER** commit `.env` or real tokens to git.
- `.env.example` contains placeholders only.
- All secrets must come from environment variables or a secrets manager.
