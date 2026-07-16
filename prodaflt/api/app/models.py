"""
PRODAFLT FastAPI — Pydantic schemas / request+response models
Mirrors the PostgreSQL schema from migration 001_prodaflt_tables.sql
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# SHARED
# =============================================================================

class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


class PaginatedResponse(BaseResponse):
    total: int = 0
    page: int = 1
    page_size: int = 50
    pages: int = 1


# =============================================================================
# USERS
# =============================================================================

class UserBase(BaseModel):
    telegram_id: Optional[int] = None
    username: str = Field(..., max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    role: str = Field("user", pattern="^(admin|user|viewer)$")
    team_role: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    telegram_id: Optional[int] = None
    username: Optional[str] = Field(None, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user|viewer)$")
    team_role: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# =============================================================================
# LINKS
# =============================================================================

class LinkBase(BaseModel):
    url: str = Field(..., max_length=2048)
    platform: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    duration: Optional[int] = None
    status: str = Field("pending", pattern="^(pending|processing|analyzed|failed|archived)$")
    preview_url: Optional[str] = Field(None, max_length=2048)
    metadata: Optional[dict[str, Any]] = None


class LinkCreate(LinkBase):
    added_by: Optional[int] = None


class LinkUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=2048)
    platform: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    duration: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(pending|processing|analyzed|failed|archived)$")
    preview_url: Optional[str] = Field(None, max_length=2048)
    metadata: Optional[dict[str, Any]] = None


class LinkOut(LinkBase):
    model_config = ConfigDict(from_attributes=True)
    link_id: int
    added_by: Optional[int] = None
    added_at: datetime


class LinkListResponse(PaginatedResponse):
    items: list[LinkOut] = []


# =============================================================================
# CONTENT ANALYSIS
# =============================================================================

class ContentAnalysisBase(BaseModel):
    link_id: int
    pattern: Optional[str] = Field(None, max_length=255)
    researcher_comment: Optional[str] = None
    compliance_status: str = Field("pending", pattern="^(pending|compliant|non_compliant|flagged)$")
    compliance_comment: Optional[str] = None
    creative_potential: Optional[int] = Field(None, ge=1, le=10)
    assigned_code: Optional[str] = Field(None, max_length=100)


class ContentAnalysisCreate(ContentAnalysisBase):
    pass


class ContentAnalysisUpdate(BaseModel):
    pattern: Optional[str] = Field(None, max_length=255)
    researcher_comment: Optional[str] = None
    compliance_status: Optional[str] = Field(None, pattern="^(pending|compliant|non_compliant|flagged)$")
    compliance_comment: Optional[str] = None
    creative_potential: Optional[int] = Field(None, ge=1, le=10)
    assigned_code: Optional[str] = Field(None, max_length=100)


class ContentAnalysisOut(ContentAnalysisBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# =============================================================================
# TZ SPECS (Creative Briefs)
# =============================================================================

class TzSpecBase(BaseModel):
    code_content: str = Field(..., max_length=255)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    script: Optional[dict[str, Any]] = None
    visual_refs: Optional[dict[str, Any]] = None
    target_audience: Optional[str] = Field(None, max_length=255)
    platform: Optional[str] = Field(None, max_length=100)
    status: str = Field("draft", pattern="^(draft|in_review|approved|rejected|archived)$")
    asana_task_id: Optional[str] = Field(None, max_length=100)


class TzSpecCreate(TzSpecBase):
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None


class TzSpecUpdate(BaseModel):
    code_content: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    script: Optional[dict[str, Any]] = None
    visual_refs: Optional[dict[str, Any]] = None
    target_audience: Optional[str] = Field(None, max_length=255)
    platform: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, pattern="^(draft|in_review|approved|rejected|archived)$")
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    asana_task_id: Optional[str] = Field(None, max_length=100)


class TzSpecOut(TzSpecBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# PATTERNS
# =============================================================================

class PatternBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    examples: Optional[dict[str, Any]] = None
    frequency: Optional[int] = None
    week_of: Optional[date] = None
    metrics: Optional[dict[str, Any]] = None


class PatternCreate(PatternBase):
    pass


class PatternUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    examples: Optional[dict[str, Any]] = None
    frequency: Optional[int] = None
    week_of: Optional[date] = None
    metrics: Optional[dict[str, Any]] = None


class PatternOut(PatternBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# =============================================================================
# CAMPAIGN METRICS
# =============================================================================

class CampaignMetricsBase(BaseModel):
    creative_code: str = Field(..., max_length=100)
    spend: Optional[Decimal] = Field(None, ge=0)
    clicks: Optional[int] = Field(None, ge=0)
    installs: Optional[int] = Field(None, ge=0)
    deposits: Optional[int] = Field(None, ge=0)
    cpc: Optional[Decimal] = None
    cpi: Optional[Decimal] = None
    uepc: Optional[Decimal] = None
    roi: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    status: str = Field("active", pattern="^(active|paused|completed|archived)$")


class CampaignMetricsCreate(CampaignMetricsBase):
    pass


class CampaignMetricsUpdate(BaseModel):
    creative_code: Optional[str] = Field(None, max_length=100)
    spend: Optional[Decimal] = Field(None, ge=0)
    clicks: Optional[int] = Field(None, ge=0)
    installs: Optional[int] = Field(None, ge=0)
    deposits: Optional[int] = Field(None, ge=0)
    cpc: Optional[Decimal] = None
    cpi: Optional[Decimal] = None
    uepc: Optional[Decimal] = None
    roi: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|completed|archived)$")


class CampaignMetricsOut(CampaignMetricsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recorded_at: datetime


class CampaignMetricsListResponse(PaginatedResponse):
    items: list[CampaignMetricsOut] = []


# =============================================================================
# ALERTS LOG
# =============================================================================

class AlertBase(BaseModel):
    campaign_id: Optional[int] = None
    alert_type: str = Field(..., pattern="^(roi_drop|cpi_spike|install_drop|deposit_drop|anomaly)$")
    flag: Optional[str] = Field(None, max_length=100)
    triggered_metrics: Optional[dict[str, Any]] = None
    confidence: Optional[Decimal] = Field(None, ge=0, le=100)
    decision: Optional[str] = Field(None, max_length=255)
    reason: Optional[str] = None
    sent_to: Optional[str] = Field(None, max_length=255)


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    campaign_id: Optional[int] = None
    alert_type: Optional[str] = Field(None, pattern="^(roi_drop|cpi_spike|install_drop|deposit_drop|anomaly)$")
    flag: Optional[str] = Field(None, max_length=100)
    triggered_metrics: Optional[dict[str, Any]] = None
    confidence: Optional[Decimal] = Field(None, ge=0, le=100)
    decision: Optional[str] = Field(None, max_length=255)
    reason: Optional[str] = None
    sent_to: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, pattern="^(new|acknowledged|resolved|dismissed)$")


class AlertOut(AlertBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sent_at: Optional[datetime] = None
    status: str


class AlertListResponse(PaginatedResponse):
    items: list[AlertOut] = []


# =============================================================================
# STATS / AGGREGATIONS
# =============================================================================

class DashboardStats(BaseModel):
    total_links: int
    total_tz_specs: int
    total_campaigns: int
    active_alerts: int
    approved_links: int
    pending_links: int
    top_creative_codes: list[dict[str, Any]]
    recent_alerts: list[dict[str, Any]]


class AlertEvaluationRequest(BaseModel):
    creative_code: str
    spend: Decimal
    clicks: int
    installs: int
    deposits: int
    cpc: Decimal
    cpi: Decimal
    uepc: Decimal
    revenue: Optional[Decimal] = None


class AlertEvaluationResponse(BaseModel):
    flag: str  # RED | GREEN | YELLOW | WHITE
    decision: str  # KILL | SCALE | WATCH | INSUFFICIENT
    confidence: int  # 100 | 95 | 85 | 70
    reason: str
    thresholds: dict[str, Any]
