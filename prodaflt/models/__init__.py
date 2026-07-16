"""
PRODAFLT — ORM Models
=====================
SQLAlchemy 2.0 declarative models mapping to the PRODAFLT database schema.
All models correspond to tables created by migrations/001_prodaflt_tables.sql
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


# ================================================================
# 1. USERS
# ================================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, nullable=True
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user"
    )  # admin | user | viewer
    team_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    links: Mapped[list["Link"]] = relationship("Link", back_populates="added_by_user")
    tz_specs_created: Mapped[list["TZSpec"]] = relationship(
        "TZSpec", foreign_keys="TZSpec.created_by", back_populates="creator"
    )
    tz_specs_assigned: Mapped[list["TZSpec"]] = relationship(
        "TZSpec", foreign_keys="TZSpec.assigned_to", back_populates="assignee"
    )


# ================================================================
# 2. LINKS
# ================================================================
class Link(Base):
    __tablename__ = "links"

    link_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | processing | analyzed | failed | archived
    added_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    preview_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    added_by_user: Mapped["User | None"] = relationship("User", back_populates="links")
    content_analyses: Mapped[list["ContentAnalysis"]] = relationship(
        "ContentAnalysis", back_populates="link", cascade="all, delete-orphan"
    )


# ================================================================
# 3. CONTENT ANALYSIS
# ================================================================
class ContentAnalysis(Base):
    __tablename__ = "content_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    link_id: Mapped[int] = mapped_column(
        ForeignKey("links.link_id", ondelete="CASCADE"), nullable=False
    )
    pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    researcher_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | compliant | non_compliant | flagged
    compliance_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    creative_potential: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 1-10
    assigned_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    link: Mapped["Link"] = relationship("Link", back_populates="content_analyses")


# ================================================================
# 4. TZ SPECS (Creative Briefs / ТЗ)
# ================================================================
class TZSpec(Base):
    __tablename__ = "tz_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_content: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    script: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    visual_refs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft | in_review | approved | rejected | archived
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    asana_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    creator: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by], back_populates="tz_specs_created"
    )
    assignee: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_to], back_populates="tz_specs_assigned"
    )


# ================================================================
# 5. PATTERNS
# ================================================================
class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    frequency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week_of: Mapped[Date | None] = mapped_column(Date, nullable=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


# ================================================================
# 6. CAMPAIGN METRICS
# ================================================================
class CampaignMetric(Base):
    __tablename__ = "campaign_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creative_code: Mapped[str] = mapped_column(String(100), nullable=False)
    spend: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deposits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpc: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    cpi: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    uepc: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    roi: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active | paused | completed | archived
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    alerts: Mapped[list["AlertLog"]] = relationship(
        "AlertLog", back_populates="campaign", cascade="all, delete-orphan"
    )


# ================================================================
# 7. ALERTS LOG
# ================================================================
class AlertLog(Base):
    __tablename__ = "alerts_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaign_metrics.id", ondelete="CASCADE"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # roi_drop | cpi_spike | install_drop | deposit_drop | anomaly
    flag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    triggered_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # 0-100
    decision: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new"
    )  # new | acknowledged | resolved | dismissed

    # Relationships
    campaign: Mapped["CampaignMetric | None"] = relationship(
        "CampaignMetric", back_populates="alerts"
    )
