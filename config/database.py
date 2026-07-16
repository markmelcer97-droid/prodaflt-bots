"""
PRODAFLT — Database Configuration
=================================
SQLAlchemy 2.0 async + sync engine setup with connection pooling,
session management, and declarative base for all ORM models.

Usage:
    from config.database import AsyncSessionLocal, get_db
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import settings


# ------------------------------------------------------------------
# SQLAlchemy 2.0 Declarative Base
# ------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all ORM models."""

    def __repr__(self) -> str:
        cols = [f"{c.key}={getattr(self, c.key)!r}" for c in self.__table__.columns]
        return f"<{self.__class__.__name__}({', '.join(cols)})>"


# ------------------------------------------------------------------
# SYNC ENGINE (for migrations, admin scripts, alembic)
# ------------------------------------------------------------------
# Neon supports both sync and async drivers.
# For sync operations (Alembic, ad-hoc scripts) use psycopg2.
_sync_engine = create_engine(
    settings.database_url_str,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_pre_ping=True,  # verify connection before using from pool
    echo=settings.sqlalchemy_echo,
    future=True,
)

# Sync session factory
SessionLocal = sessionmaker(
    bind=_sync_engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


# ------------------------------------------------------------------
# ASYNC ENGINE (for FastAPI, bot handlers, all runtime I/O)
# ------------------------------------------------------------------
# Convert postgresql:// → postgresql+asyncpg:// for async driver
_async_database_url = settings.database_url_str.replace(
    "postgresql://", "postgresql+asyncpg://"
)

_async_engine = create_async_engine(
    _async_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_pre_ping=True,
    echo=settings.sqlalchemy_echo,
    future=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ------------------------------------------------------------------
# DEPENDENCY INJECTION HELPERS
# ------------------------------------------------------------------

def get_sync_db():
    """Synchronous DB session generator (for scripts, CLI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async DB session generator (for FastAPI dependencies)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for DB sessions outside of FastAPI deps."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ------------------------------------------------------------------
# LIFECYCLE MANAGEMENT
# ------------------------------------------------------------------

async def close_db_connections() -> None:
    """Dispose of all engine connections — call on shutdown."""
    await _async_engine.dispose()
    _sync_engine.dispose()


async def init_db() -> None:
    """
    Create all tables defined by ORM models.
    **Use only in development / testing.**
    In production, run Alembic migrations instead.
    """
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
