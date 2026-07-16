"""
Database integration for soul prompt versioning.

Stores prompts in PostgreSQL so agents can query their current soul version
and so updates are tracked historically.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

# Optional dependency — component works file-only if DB unavailable
try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None  # type: ignore


DEFAULT_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:___PASSWORD___@ep-bitter-waterfall-ajf1xpzc-pooler.c-3.us-east-2.aws.neon.tech/neondb?channel_binding=require&sslmode=require",
)


class SoulPromptDB:
    """
    Async PostgreSQL interface for soul prompt versioning.

    Expected table (created via migration):
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            agent_key VARCHAR(50) UNIQUE NOT NULL,
            agent_name VARCHAR(100) NOT NULL,
            role VARCHAR(100),
            soul_version VARCHAR(20),
            soul_content TEXT,
            heartbeat VARCHAR(100),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """

    def __init__(self, dsn: Optional[str] = None) -> None:
        if asyncpg is None:
            raise RuntimeError("asyncpg is required for DB mode. Install: pip install asyncpg")
        self.dsn = dsn or DEFAULT_DSN
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def transaction(self):
        if self._pool is None:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    # ---------------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------------

    async def upsert(
        self,
        agent_key: str,
        agent_name: str,
        role: str,
        soul_version: str,
        soul_content: str,
        heartbeat: str,
    ) -> None:
        """Insert or update an agent's soul prompt."""
        sql = """
        INSERT INTO agents (agent_key, agent_name, role, soul_version, soul_content, heartbeat, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (agent_key)
        DO UPDATE SET
            agent_name = EXCLUDED.agent_name,
            role = EXCLUDED.role,
            soul_version = EXCLUDED.soul_version,
            soul_content = EXCLUDED.soul_content,
            heartbeat = EXCLUDED.heartbeat,
            updated_at = NOW();
        """
        async with self.transaction() as conn:
            await conn.execute(sql, agent_key, agent_name, role, soul_version, soul_content, heartbeat)

    async def get(self, agent_key: str) -> Optional[dict]:
        """Fetch current soul for an agent."""
        sql = "SELECT * FROM agents WHERE agent_key = $1"
        async with self.transaction() as conn:
            row = await conn.fetchrow(sql, agent_key)
            return dict(row) if row else None

    async def list_all(self) -> list[dict]:
        """List all agents with their soul versions."""
        sql = "SELECT agent_key, agent_name, role, soul_version, heartbeat, updated_at FROM agents ORDER BY agent_key"
        async with self.transaction() as conn:
            rows = await conn.fetch(sql)
            return [dict(r) for r in rows]

    async def sync_from_loader(self, loader) -> None:
        """
        Bulk-sync all file-based prompts into DB.
        Accepts a SoulPromptLoader instance.
        """
        prompts = loader.load_all()
        for agent_key, prompt in prompts.items():
            await self.upsert(
                agent_key=agent_key,
                agent_name=prompt.agent_name,
                role=prompt.role,
                soul_version=prompt.version,
                soul_content=prompt.content,
                heartbeat=prompt.heartbeat,
            )

    # ---------------------------------------------------------------------
    # Migration helper
    # ---------------------------------------------------------------------

    @staticmethod
    def migration_sql() -> str:
        """Return SQL to create the agents table."""
        return """
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            agent_key VARCHAR(50) UNIQUE NOT NULL,
            agent_name VARCHAR(100) NOT NULL,
            role VARCHAR(100),
            soul_version VARCHAR(20),
            soul_content TEXT,
            heartbeat VARCHAR(100),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_agents_key ON agents(agent_key);
        CREATE INDEX IF NOT EXISTS idx_agents_version ON agents(soul_version);
        """
