"""
PRODAFLT FastAPI — Database layer
Async SQLAlchemy with connection pooling for Neon PostgreSQL.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# Read DATABASE_URL from environment; fallback to placeholder (will fail loudly)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://neondb_owner:___PASTE_PASSWORD_HERE___@ep-bitter-waterfall-ajf1xpzc-pooler.c-3.us-east-2.aws.neon.tech/neondb?ssl=require",
)

# Neon serverless works best with NullPool to avoid stale connections
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=os.getenv("APP_ENV", "development") == "development",
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Declarative base for models (if we add ORM models later)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
