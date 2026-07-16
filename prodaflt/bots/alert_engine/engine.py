"""
PRODAFLT Alert Engine — Core Evaluation Logic
==============================================
Evaluates campaign metrics against configurable thresholds and produces
RED / GREEN / YELLOW / WHITE decisions with confidence levels.

Business rules (from SCALE + v3 hybrid):
    RED    (KILL)   → CPI ≥ $5  OR  CPC ≥ $2.5  OR  uEPC ≥ $8  OR  ROI ≤ -50%
    GREEN  (SCALE)  → uEPC < $4  AND  CPI ≤ $5  AND  ROI > 0
    YELLOW (WATCH)  → uEPC between 4 and 8  (borderline performance)
    WHITE  (SKIP)   → Not enough data (min_spend / min_clicks / min_installs)

Confidence levels:
    100% → Large sample, all signals agree
    95%  → Strong signal, minor data concerns
    85%  → Moderate signal, limited sample
    70%  → Weak signal, high uncertainty
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from models import (
    CampaignMetrics,
    AlertFlag,
    AlertType,
    AlertDecision,
    ThresholdConfig,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence scoring helpers
# ---------------------------------------------------------------------------

def _sample_size_score(m: CampaignMetrics, cfg: ThresholdConfig) -> Decimal:
    """Return 0-1 score based on how much data we have."""
    scores: List[Decimal] = []

    if m.spend is not None and cfg.high_sample_min_spend > 0:
        scores.append(min(Decimal("1"), m.spend / cfg.high_sample_min_spend))
    if m.clicks is not None and cfg.high_sample_min_clicks > 0:
        scores.append(min(Decimal("1"), Decimal(m.clicks) / Decimal(cfg.high_sample_min_clicks)))
    if m.installs is not None and cfg.high_sample_min_installs > 0:
        scores.append(min(Decimal("1"), Decimal(m.installs) / Decimal(cfg.high_sample_min_installs)))

    if not scores:
        return Decimal("0")
    return sum(scores) / Decimal(len(scores))


def _compute_confidence(
    m: CampaignMetrics,
    cfg: ThresholdConfig,
    severity_hits: int,
) -> Decimal:
    """
    Compute confidence percentage (70, 85, 95, 100).
    Base on sample size + severity agreement.
    """
    sample = _sample_size_score(m, cfg)

    # Base from sample size
    if sample >= Decimal("1.0"):
        base = Decimal("100")
    elif sample >= Decimal("0.7"):
        base = Decimal("95")
    elif sample >= Decimal("0.4"):
        base = Decimal("85")
    else:
        base = Decimal("70")

    # Adjust down if multiple conflicting signals (rare, but possible)
    if severity_hits == 0:
        base -= Decimal("15")

    # Clamp
    base = max(Decimal("70"), min(Decimal("100"), base))
    return base.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------

def evaluate_campaign(
    m: CampaignMetrics,
    cfg: Optional[ThresholdConfig] = None,
) -> AlertDecision:
    """
    Evaluate a single campaign metrics row and return an AlertDecision.

    Args:
        m: CampaignMetrics instance.
        cfg: ThresholdConfig override (defaults to env-loaded values).

    Returns:
        AlertDecision with flag, confidence, and human-readable reason.
    """
    if cfg is None:
        from config import get_settings
        s = get_settings()
        cfg = ThresholdConfig(
            cpc_kill=s.threshold_cpc_kill,
            cpi_kill=s.threshold_cpi_kill,
            uepc_kill=s.threshold_uepc_kill,
            uepc_scale=s.threshold_uepc_scale,
            roi_kill=s.threshold_roi_kill,
            min_spend_for_alert=s.min_spend_for_alert_usd,
            min_clicks_for_alert=s.min_clicks_for_alert,
            min_installs_for_alert=s.min_installs_for_alert,
            high_sample_min_spend=s.confidence_high_sample_min_spend,
            high_sample_min_clicks=s.confidence_high_sample_min_clicks,
            high_sample_min_installs=s.confidence_high_sample_min_installs,
        )

    # ---- 1. INSUFFICIENT DATA check --------------------------------------
    insufficient_reasons: List[str] = []

    if m.spend is None or m.spend < cfg.min_spend_for_alert:
        insufficient_reasons.append(
            f"spend ${m.spend} < ${cfg.min_spend_for_alert}"
        )
    if m.clicks is None or m.clicks < cfg.min_clicks_for_alert:
        insufficient_reasons.append(
            f"clicks {m.clicks} < {cfg.min_clicks_for_alert}"
        )
    if m.installs is None or m.installs < cfg.min_installs_for_alert:
        insufficient_reasons.append(
            f"installs {m.installs} < {cfg.min_installs_for_alert}"
        )

    if insufficient_reasons:
        return AlertDecision(
            campaign_id=m.id,
            creative_code=m.creative_code,
            flag=AlertFlag.WHITE,
            alert_types=[AlertType.ANOMALY],
            confidence=Decimal("70"),
            decision="INSUFFICIENT DATA — evaluation skipped",
            reason="; ".join(insufficient_reasons),
            triggered_metrics={
                "spend": str(m.spend) if m.spend else None,
                "clicks": m.clicks,
                "installs": m.installs,
            },
        )

    # ---- 2. RED (KILL) checks ---------------------------------------------
    red_hits: List[str] = []
    red_types: List[AlertType] = []
    triggered: dict = {}

    if m.cpi is not None and m.cpi >= cfg.cpi_kill:
        red_hits.append(f"CPI ${m.cpi} ≥ ${cfg.cpi_kill}")
        red_types.append(AlertType.CPI_SPIKE)
        triggered["cpi"] = str(m.cpi)

    if m.cpc is not None and m.cpc >= cfg.cpc_kill:
        red_hits.append(f"CPC ${m.cpc} ≥ ${cfg.cpc_kill}")
        red_types.append(AlertType.CPI_SPIKE)  # Re-use; could be new type
        triggered["cpc"] = str(m.cpc)

    if m.uepc is not None and m.uepc >= cfg.uepc_kill:
        red_hits.append(f"uEPC ${m.uepc} ≥ ${cfg.uepc_kill}")
        red_types.append(AlertType.ROI_DROP)
        triggered["uepc"] = str(m.uepc)

    if m.roi is not None and m.roi <= cfg.roi_kill:
        red_hits.append(f"ROI {m.roi}% ≤ {cfg.roi_kill}%")
        red_types.append(AlertType.ROI_DROP)
        triggered["roi"] = str(m.roi)

    if red_hits:
        confidence = _compute_confidence(m, cfg, severity_hits=len(red_hits))
        return AlertDecision(
            campaign_id=m.id,
            creative_code=m.creative_code,
            flag=AlertFlag.RED,
            alert_types=list(dict.fromkeys(red_types)),  # dedupe
            confidence=confidence,
            decision=f"KILL — {', '.join(red_hits)}",
            reason=(
                f"Campaign {m.creative_code} breached critical threshold(s). "
                f"Immediate review recommended. Sample: spend=${m.spend}, "
                f"clicks={m.clicks}, installs={m.installs}."
            ),
            triggered_metrics=triggered,
        )

    # ---- 3. GREEN (SCALE) checks ------------------------------------------
    green_ok: List[str] = []
    green_triggered: dict = {}

    if m.uepc is not None and m.uepc < cfg.uepc_scale:
        green_ok.append(f"uEPC ${m.uepc} < ${cfg.uepc_scale}")
        green_triggered["uepc"] = str(m.uepc)

    if m.cpi is not None and m.cpi <= cfg.cpi_kill:
        green_ok.append(f"CPI ${m.cpi} ≤ ${cfg.cpi_kill}")
        green_triggered["cpi"] = str(m.cpi)

    if m.roi is not None and m.roi > Decimal("0"):
        green_ok.append(f"ROI {m.roi}% > 0%")
        green_triggered["roi"] = str(m.roi)

    # Require ALL scale conditions (uEPC + CPI + positive ROI)
    if len(green_ok) >= 3:
        confidence = _compute_confidence(m, cfg, severity_hits=3)
        return AlertDecision(
            campaign_id=m.id,
            creative_code=m.creative_code,
            flag=AlertFlag.GREEN,
            alert_types=[AlertType.ANOMALY],  # Positive anomaly
            confidence=confidence,
            decision=f"SCALE — {', '.join(green_ok)}",
            reason=(
                f"Campaign {m.creative_code} shows strong performance. "
                f"Consider increasing budget. Sample: spend=${m.spend}, "
                f"clicks={m.clicks}, installs={m.installs}."
            ),
            triggered_metrics=green_triggered,
        )

    # ---- 4. YELLOW (WATCH) checks -----------------------------------------
    yellow_hits: List[str] = []
    yellow_triggered: dict = {}

    if m.uepc is not None and cfg.uepc_scale <= m.uepc < cfg.uepc_kill:
        yellow_hits.append(f"uEPC ${m.uepc} between ${cfg.uepc_scale} and ${cfg.uepc_kill}")
        yellow_triggered["uepc"] = str(m.uepc)

    if m.cpi is not None and Decimal("3.50") <= m.cpi < cfg.cpi_kill:
        yellow_hits.append(f"CPI ${m.cpi} approaching ${cfg.cpi_kill}")
        yellow_triggered["cpi"] = str(m.cpi)

    if yellow_hits:
        confidence = _compute_confidence(m, cfg, severity_hits=len(yellow_hits))
        return AlertDecision(
            campaign_id=m.id,
            creative_code=m.creative_code,
            flag=AlertFlag.YELLOW,
            alert_types=[AlertType.ANOMALY],
            confidence=confidence,
            decision=f"WATCH — {', '.join(yellow_hits)}",
            reason=(
                f"Campaign {m.creative_code} is in borderline territory. "
                f"Monitor closely before scaling. Sample: spend=${m.spend}, "
                f"clicks={m.clicks}, installs={m.installs}."
            ),
            triggered_metrics=yellow_triggered,
        )

    # ---- 5. Default (WHITE) -----------------------------------------------
    return AlertDecision(
        campaign_id=m.id,
        creative_code=m.creative_code,
        flag=AlertFlag.WHITE,
        alert_types=[AlertType.ANOMALY],
        confidence=Decimal("70"),
        decision="NO ACTION — metrics within normal range",
        reason=(
            f"Campaign {m.creative_code} has no significant signals. "
            f"Spend=${m.spend}, clicks={m.clicks}, installs={m.installs}."
        ),
        triggered_metrics={
            "cpi": str(m.cpi) if m.cpi else None,
            "cpc": str(m.cpc) if m.cpc else None,
            "uepc": str(m.uepc) if m.uepc else None,
            "roi": str(m.roi) if m.roi else None,
        },
    )


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def evaluate_all(
    campaigns: List[CampaignMetrics],
    cfg: Optional[ThresholdConfig] = None,
) -> List[AlertDecision]:
    """Evaluate a list of campaigns and return non-WHITE decisions."""
    results: List[AlertDecision] = []
    for c in campaigns:
        decision = evaluate_campaign(c, cfg)
        if decision.flag != AlertFlag.WHITE:
            results.append(decision)
        else:
            logger.debug("Campaign %s WHITE — no alert", c.creative_code)
    return results
