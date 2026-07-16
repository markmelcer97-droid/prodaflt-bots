"""
FastAPI mini-service for soul prompt retrieval.

Endpoints:
  GET  /health          → health check
  GET  /agents          → list all agents
  GET  /agents/{key}    → get prompt for agent
  POST /sync            → sync file prompts to DB (admin)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .loader import SoulPromptLoader, list_agents, AGENTS
from .db import SoulPromptDB


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AgentMeta(BaseModel):
    key: str
    name: str
    role: str
    heartbeat: str


class AgentPrompt(BaseModel):
    key: str
    name: str
    role: str
    version: str
    heartbeat: str
    content: str


class SyncResult(BaseModel):
    synced: int
    agents: list[str]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.loader = SoulPromptLoader()
    dsn = os.getenv("DATABASE_URL")
    if dsn and _has_asyncpg():
        app.state.db = SoulPromptDB(dsn)
        await app.state.db.connect()
    else:
        app.state.db = None
    yield
    # Shutdown
    if app.state.db:
        await app.state.db.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PRODAFLT Soul Prompts API",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "component": "soul-prompts-text"}

    @app.get("/agents", response_model=list[AgentMeta])
    async def list_all() -> list[dict]:
        return list_agents()

    @app.get("/agents/{key}", response_model=AgentPrompt)
    async def get_agent(key: str) -> dict:
        if key not in AGENTS:
            raise HTTPException(status_code=404, detail=f"Agent '{key}' not found")
        prompt = app.state.loader.load(key)
        return {
            "key": key,
            "name": prompt.agent_name,
            "role": prompt.role,
            "version": prompt.version,
            "heartbeat": prompt.heartbeat,
            "content": prompt.content,
        }

    @app.post("/sync", response_model=SyncResult)
    async def sync_to_db() -> dict:
        if app.state.db is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        await app.state.db.sync_from_loader(app.state.loader)
        synced = list(AGENTS.keys())
        return {"synced": len(synced), "agents": synced}

    return app


def _has_asyncpg() -> bool:
    try:
        import asyncpg  # noqa: F401
        return True
    except ImportError:
        return False


# Default app instance for uvicorn
app = create_app()
