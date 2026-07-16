"""
PRODAFLT Alert Engine — Data Models
====================================
Pydantic models for metrics, thresholds, alerts, and engine decisions.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class AlertFlag(str, Enum):
    """Traffic-light flag derived from metric thresholds."""
    RED = "RED"       # KILL — performance is critically bad
    GREEN = "GREEN"   # SCALE — performance is excellent
    YELLOW = "YELLOW" # WATCH — performance is borderline
    WHITE = "WHITE"   # INSUFFICIENT DATA — not enough sample size


class AlertType(str, Enum):
    """Alert classification (mirrors DB enum)."""
    ROI_DROP = "roi_drop"
    CPI_SPIKE = "cpi_spike"
    INSTALL_DROP = "install_drop"
    DEPOSIT_DROP = "deposit_drop"
    ANOMALY = "anomaly"


class CampaignStatus(str, Enum):
    """Campaign lifecycle status (mirrors DB enum)."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AlertStatus(str, Enum):
    """Alert lifecycle status (mirrors DB enum)."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CampaignMetrics(BaseModel):
    """Row from campaign_metrics table."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    creative_code: str
    spend: Optional[Decimal] = None
    clicks: Optional[int] = None
    installs: Optional[int] = None
    deposits: Optional[int] = None
    cpc: Optional[Decimal] = None
    cpi: Optional[Decimal] = None
    uepc: Optional[Decimal] = None
    roi: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    status: CampaignStatus = CampaignStatus.ACTIVE
    recorded_at: datetime

    @property
    def has_spend(self) -> bool:
        return self.spend is not None and self.spend > 0

    @property
    def has_clicks(self) -> bool:
        return self.clicks is not None and self.clicks > 0

    @property
    def has_installs(self) -> bool:
        return self.installs is not None and self.installs > 0


class ThresholdConfig(BaseModel):
    """Runtime threshold configuration (loaded from env or DB)."""
    cpc_kill: Decimal = Field(default=Decimal("2.50"))
    cpi_kill: Decimal = Field(default=Decimal("5.00"))
    uepc_kill: Decimal = Field(default=Decimal("8.00"))
    uepc_scale: Decimal = Field(default=Decimal("4.00"))
    roi_kill: Decimal = Field(default=Decimal("-0.50"))

    min_spend_for_alert: Decimal = Field(default=Decimal("20.00"))
    min_clicks_for_alert: int = Field(default=10)
    min_installs_for_alert: int = Field(default=3)

    # Confidence tuning
    high_sample_min_spend: Decimal = Field(default=Decimal("100.00"))
    high_sample_min_clicks: int = Field(default=50)
    high_sample_min_installs: int = Field(default=10)


class AlertDecision(BaseModel):
    """Result of evaluating a single campaign metric row."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: int
    creative_code: str
    flag: AlertFlag
    alert_types: list[AlertType] = Field(default_factory=list)
    confidence: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    decision: str  # Human-readable one-liner, e.g. "KILL: CPI $5.30 exceeds $5.00"
    reason: str    # Detailed explanation
    triggered_metrics: dict = Field(default_factory=dict)


class AlertLogEntry(BaseModel):
    """Row to be inserted into alerts_log table."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: int
    alert_type: AlertType
    flag: str
    triggered_metrics: dict
    confidence: Decimal
    decision: str
    reason: str
    sent_to: Optional[str] = None
    sent_at: Optional[datetime] = None
    status: AlertStatus = AlertStatus.NEW
