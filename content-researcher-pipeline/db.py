"""
PRODAFLT Content Researcher Pipeline — Database Layer
SQLAlchemy async engine + models mapped to the existing Neon schema.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import config


# ---------------------------------------------------------------------------
# Engine & session
# ---------------------------------------------------------------------------

# Convert psycopg2 URL to asyncpg URL if needed
_DB_URL = config.DATABASE_URL
if _DB_URL.startswith("postgresql://") and "asyncpg" not in _DB_URL:
    _DB_URL = _DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async_engine = create_async_engine(_DB_URL, pool_pre_ping=True, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

# Sync engine for migrations / admin scripts
sync_engine = create_engine(config.DATABASE_URL.replace("+asyncpg", ""))


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Enum helpers
# ---------------------------------------------------------------------------

class LinkStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    analyzed = "analyzed"
    failed = "failed"
    archived = "archived"


class ComplianceStatus(str, Enum):
    pending = "pending"
    compliant = "compliant"
    non_compliant = "non_compliant"
    flagged = "flagged"


class TZSpecStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    archived = "archived"


class CampaignStatus(str, Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class AlertType(str, Enum):
    roi_drop = "roi_drop"
    cpi_spike = "cpi_spike"
    install_drop = "install_drop"
    deposit_drop = "deposit_drop"
    anomaly = "anomaly"


class AlertStatus(str, Enum):
    new = "new"
    acknowledged = "acknowledged"
    resolved = "resolved"
    dismissed = "dismissed"


class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    team_role: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Link(Base):
    __tablename__ = "links"

    link_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048))
    platform: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    duration: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[LinkStatus] = mapped_column(
        Enum(LinkStatus, name="link_status"), default=LinkStatus.pending
    )
    added_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    preview_url: Mapped[Optional[str]] = mapped_column(String(2048))
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    analyses: Mapped[List["ContentAnalysis"]] = relationship(
        back_populates="link", cascade="all, delete-orphan"
    )


class ContentAnalysis(Base):
    __tablename__ = "content_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("links.link_id", ondelete="CASCADE"))
    pattern: Mapped[Optional[str]] = mapped_column(String(255))
    researcher_comment: Mapped[Optional[str]] = mapped_column(Text)
    compliance_status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliance_status"), default=ComplianceStatus.pending
    )
    compliance_comment: Mapped[Optional[str]] = mapped_column(Text)
    creative_potential: Mapped[Optional[int]] = mapped_column(Integer)
    assigned_code: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Scoring fields (added by pipeline)
    virality_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    adaptation_potential: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    final_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    content_format: Mapped[Optional[str]] = mapped_column(String(100))
    hook_text: Mapped[Optional[str]] = mapped_column(Text)
    cta_text: Mapped[Optional[str]] = mapped_column(Text)
    visual_tags: Mapped[Optional[list]] = mapped_column(JSONB)
    audio_transcript: Mapped[Optional[str]] = mapped_column(Text)
    frame_timestamps: Mapped[Optional[list]] = mapped_column(JSONB)

    link: Mapped["Link"] = relationship(back_populates="analyses")


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    examples: Mapped[Optional[list]] = mapped_column(JSONB)
    frequency: Mapped[Optional[int]] = mapped_column(Integer)
    week_of: Mapped[Optional[datetime]] = mapped_column(Date)
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TZSpec(Base):
    __tablename__ = "tz_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_content: Mapped[str] = mapped_column(String(255), unique=True)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    script: Mapped[Optional[dict]] = mapped_column(JSONB)
    visual_refs: Mapped[Optional[list]] = mapped_column(JSONB)
    target_audience: Mapped[Optional[str]] = mapped_column(String(255))
    platform: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[TZSpecStatus] = mapped_column(
        Enum(TZSpecStatus, name="tz_spec_status"), default=TZSpecStatus.draft
    )
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    asana_task_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CampaignMetric(Base):
    __tablename__ = "campaign_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creative_code: Mapped[str] = mapped_column(String(100))
    spend: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    clicks: Mapped[Optional[int]] = mapped_column(Integer)
    installs: Mapped[Optional[int]] = mapped_column(Integer)
    deposits: Mapped[Optional[int]] = mapped_column(Integer)
    cpc: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    cpi: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    uepc: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    roi: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    revenue: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"), default=CampaignStatus.active
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertLog(Base):
    __tablename__ = "alerts_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaign_metrics.id", ondelete="CASCADE"))
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType, name="alert_type"))
    flag: Mapped[Optional[str]] = mapped_column(String(100))
    triggered_metrics: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    decision: Mapped[Optional[str]] = mapped_column(String(255))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    sent_to: Mapped[Optional[str]] = mapped_column(String(255))
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"), default=AlertStatus.new
    )


# ---------------------------------------------------------------------------
# Helper query builders
# ---------------------------------------------------------------------------

async def fetch_pending_links(session: AsyncSession, limit: int = 15) -> List[Link]:
    """Return links with status='pending', newest first."""
    result = await session.execute(
        select(Link)
        .where(Link.status == LinkStatus.pending)
        .order_by(Link.added_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def fetch_top_scored(
    session: AsyncSession, min_score: float, limit: int = 15
) -> List[ContentAnalysis]:
    """Return analyses with final_score >= threshold."""
    result = await session.execute(
        select(ContentAnalysis)
        .where(ContentAnalysis.final_score >= min_score)
        .order_by(ContentAnalysis.final_score.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def upsert_pattern(session: AsyncSession, name: str, description: str, examples: list) -> Pattern:
    """Upsert a pattern by name."""
    result = await session.execute(select(Pattern).where(Pattern.name == name))
    pattern = result.scalar_one_or_none()
    if pattern:
        pattern.description = description
        pattern.examples = examples
        pattern.frequency = (pattern.frequency or 0) + 1
    else:
        pattern = Pattern(name=name, description=description, examples=examples, frequency=1)
        session.add(pattern)
    await session.flush()
    return pattern
