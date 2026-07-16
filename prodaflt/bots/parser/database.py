"""
PRODAFLT Parser Bot — Database Layer
SQLAlchemy models + async session management for Neon PostgreSQL.
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config import config

logger = logging.getLogger(__name__)

# Convert neon URL to asyncpg format if needed
def _make_async_url(url: str) -> str:
    """Ensure asyncpg-compatible URL."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Engine + session factory
async_engine = create_async_engine(
    _make_async_url(config.DATABASE_URL),
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


# ------------------------------------------------------------------
# Models (mirror migration 001_prodaflt_tables.sql)
# ------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    username = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(100))
    role = Column(String(50), default="user")
    team_role = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default="now()")


class Link(Base):
    __tablename__ = "links"

    link_id = Column(Integer, primary_key=True)
    url = Column(String(2048), nullable=False)
    platform = Column(String(100))
    title = Column(String(500))
    description = Column(Text)
    duration = Column(Integer)
    status = Column(String(50), default="new")
    added_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    added_at = Column(DateTime, default="now()")
    preview_url = Column(String(2048))
    metadata_ = Column("metadata", JSONB)


# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session (context manager)."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str,
    first_name: Optional[str] = None,
) -> User:
    """Fetch user by telegram_id or create new record."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        if user.username != username:
            user.username = username
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name or username,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    logger.info("Created new user: %s (id=%s)", username, user.id)
    return user


async def insert_links_batch(
    session: AsyncSession,
    link_data: List[Dict],
) -> int:
    """
    Batch-insert links, skipping duplicates by URL.
    Returns count of inserted rows.
    """
    if not link_data:
        return 0

    inserted = 0
    for item in link_data:
        url = item.get("url")
        if not url:
            continue

        result = await session.execute(select(Link).where(Link.url == url))
        existing = result.scalar_one_or_none()
        if existing:
            logger.debug("Skipping duplicate URL: %s", url)
            continue

        link = Link(
            url=url,
            platform=item.get("platform"),
            title=item.get("title"),
            description=item.get("description"),
            duration=item.get("duration"),
            status="new",
            added_by=item.get("added_by"),
            preview_url=item.get("preview_url"),
            metadata_=item.get("metadata"),
        )
        session.add(link)
        inserted += 1

    await session.flush()
    logger.info("Batch inserted %d new links", inserted)
    return inserted


async def get_links_stats(session: AsyncSession) -> Dict:
    """Return quick stats for /stats command."""
    total = await session.scalar(select(func.count()).select_from(Link))
    new_count = await session.scalar(
        select(func.count()).where(Link.status == "new")
    )
    analyzed = await session.scalar(
        select(func.count()).where(Link.status == "analyzed")
    )
    rejected = await session.scalar(
        select(func.count()).where(Link.status == "rejected")
    )

    since = datetime.utcnow() - timedelta(hours=24)
    last_24h = await session.scalar(
        select(func.count()).where(Link.added_at >= since)
    )

    return {
        "total": total or 0,
        "new": new_count or 0,
        "analyzed": analyzed or 0,
        "rejected": rejected or 0,
        "last_24h": last_24h or 0,
    }
