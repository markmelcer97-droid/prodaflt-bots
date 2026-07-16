"""
PRODAFLT Alert Engine — Database Layer
=======================================
SQLAlchemy ORM models and session management for Neon PostgreSQL.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from decimal import Decimal
from typing import Generator, List, Optional

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    Numeric,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Enum as SAEnum,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB

from config import get_settings

logger = logging.getLogger(__name__)
Base = declarative_base()
settings = get_settings()

# ---------------------------------------------------------------------------
# ORM Models (mirror the migration schema)
# ---------------------------------------------------------------------------

class UserORM(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    username = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(100))
    role = Column(SAEnum("admin", "user", "viewer", name="user_role"), nullable=False, default="user")
    team_role = Column(String(100))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=text("NOW()"))


class LinkORM(Base):
    __tablename__ = "links"
    link_id = Column(Integer, primary_key=True)
    url = Column(String(2048), nullable=False)
    platform = Column(String(100))
    title = Column(String(500))
    description = Column(String)
    duration = Column(Integer)
    status = Column(SAEnum("pending", "processing", "analyzed", "failed", "archived", name="link_status"), nullable=False, default="pending")
    added_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    added_at = Column(DateTime, nullable=False, default=text("NOW()"))
    preview_url = Column(String(2048))
    metadata = Column(JSONB)


class ContentAnalysisORM(Base):
    __tablename__ = "content_analysis"
    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("links.link_id", ondelete="CASCADE"), nullable=False)
    pattern = Column(String(255))
    researcher_comment = Column(String)
    compliance_status = Column(SAEnum("pending", "compliant", "non_compliant", "flagged", name="compliance_status"), nullable=False, default="pending")
    compliance_comment = Column(String)
    creative_potential = Column(Integer)
    assigned_code = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=text("NOW()"))


class TzSpecORM(Base):
    __tablename__ = "tz_specs"
    id = Column(Integer, primary_key=True)
    code_content = Column(String(255), unique=True, nullable=False)
    title = Column(String(500))
    description = Column(String)
    script = Column(JSONB)
    visual_refs = Column(JSONB)
    target_audience = Column(String(255))
    platform = Column(String(100))
    status = Column(SAEnum("draft", "in_review", "approved", "rejected", "archived", name="tz_spec_status"), nullable=False, default="draft")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    asana_task_id = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=text("NOW()"))
    updated_at = Column(DateTime, nullable=False, default=text("NOW()"))


class PatternORM(Base):
    __tablename__ = "patterns"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String)
    examples = Column(JSONB)
    frequency = Column(Integer)
    week_of = Column(DateTime)
    metrics = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=text("NOW()"))


class CampaignMetricsORM(Base):
    __tablename__ = "campaign_metrics"
    id = Column(Integer, primary_key=True)
    creative_code = Column(String(100), nullable=False)
    spend = Column(Numeric(12, 2))
    clicks = Column(Integer)
    installs = Column(Integer)
    deposits = Column(Integer)
    cpc = Column(Numeric(10, 4))
    cpi = Column(Numeric(10, 4))
    uepc = Column(Numeric(10, 4))
    roi = Column(Numeric(10, 4))
    revenue = Column(Numeric(12, 2))
    status = Column(SAEnum("active", "paused", "completed", "archived", name="campaign_status"), nullable=False, default="active")
    recorded_at = Column(DateTime, nullable=False, default=text("NOW()"))


class AlertsLogORM(Base):
    __tablename__ = "alerts_log"
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaign_metrics.id", ondelete="CASCADE"))
    alert_type = Column(SAEnum("roi_drop", "cpi_spike", "install_drop", "deposit_drop", "anomaly", name="alert_type"), nullable=False)
    flag = Column(String(100))
    triggered_metrics = Column(JSONB)
    confidence = Column(Numeric(5, 2))
    decision = Column(String(255))
    reason = Column(String)
    sent_to = Column(String(255))
    sent_at = Column(DateTime)
    status = Column(SAEnum("new", "acknowledged", "resolved", "dismissed", name="alert_status"), nullable=False, default="new")


# ---------------------------------------------------------------------------
# Engine & Session
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
        )
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = _get_session_local()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def fetch_active_campaigns(session: Session) -> List[CampaignMetricsORM]:
    """Return all campaigns with status = 'active'."""
    return session.query(CampaignMetricsORM).filter(
        CampaignMetricsORM.status == "active"
    ).all()


def fetch_campaign_by_id(session: Session, campaign_id: int) -> Optional[CampaignMetricsORM]:
    return session.query(CampaignMetricsORM).filter(
        CampaignMetricsORM.id == campaign_id
    ).first()


def insert_alert_log(session: Session, entry: AlertsLogORM) -> int:
    """Insert an alert log row and return its ID."""
    session.add(entry)
    session.flush()
    return entry.id


def check_recent_alert_exists(
    session: Session,
    campaign_id: int,
    flag: str,
    within_minutes: int = 30,
) -> bool:
    """Return True if an identical alert was already fired recently."""
    sql = text("""
        SELECT 1 FROM alerts_log
        WHERE campaign_id = :campaign_id
          AND flag = :flag
          AND sent_at > NOW() - INTERVAL ':within_minutes minutes'
        LIMIT 1
    """)
    result = session.execute(sql, {
        "campaign_id": campaign_id,
        "flag": flag,
        "within_minutes": within_minutes,
    }).first()
    return result is not None
