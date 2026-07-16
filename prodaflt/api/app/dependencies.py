"""
PRODAFLT FastAPI — Shared dependencies and utilities
"""

import os
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


# ---------------------------------------------------------------------------
# Pagination defaults
# ---------------------------------------------------------------------------
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


# ---------------------------------------------------------------------------
# Business thresholds (loaded from env, with SCALE defaults)
# ---------------------------------------------------------------------------
class Thresholds:
    CPI_KILL = float(os.getenv("THRESHOLD_CPI_KILL", "5.0"))
    CPC_KILL = float(os.getenv("THRESHOLD_CPC_KILL", "2.5"))
    UEPC_KILL = float(os.getenv("THRESHOLD_UEPC_KILL", "8.0"))
    UEPC_SCALE = float(os.getenv("THRESHOLD_UEPC_SCALE", "4.0"))
    UEPC_WATCH_LOW = float(os.getenv("THRESHOLD_UEPC_WATCH_LOW", "6.0"))
    UEPC_WATCH_HIGH = float(os.getenv("THRESHOLD_UEPC_WATCH_HIGH", "8.0"))
    MIN_SPEND_ALERT = float(os.getenv("THRESHOLD_MIN_SPEND_ALERT", "12.0"))
    MIN_CLICKS_ALERT = int(os.getenv("THRESHOLD_MIN_CLICKS_ALERT", "8"))


# ---------------------------------------------------------------------------
# Alert Engine — pure function, no DB needed
# ---------------------------------------------------------------------------

def evaluate_alert(
    spend: float,
    clicks: int,
    installs: int,
    cpi: float,
    cpc: float,
    uepc: float,
) -> dict:
    """
    SCALE Alert Engine logic:
      RED    (KILL)         : CPI >= 5 OR CPC >= 2.5 OR uEPC >= 8
      GREEN  (SCALE)        : uEPC < 4 AND CPI <= 5
      YELLOW (WATCH)        : uEPC >= 6 AND uEPC < 8
      WHITE  (INSUFFICIENT) : Not enough data
    """
    t = Thresholds

    # Not enough data yet
    if spend < t.MIN_SPEND_ALERT or clicks < t.MIN_CLICKS_ALERT:
        return {
            "flag": "WHITE",
            "decision": "INSUFFICIENT",
            "confidence": 100,
            "reason": (
                f"Not enough data: spend=${spend:.2f} (min ${t.MIN_SPEND_ALERT}), "
                f"clicks={clicks} (min {t.MIN_CLICKS_ALERT})"
            ),
        }

    # RED — kill conditions
    if cpi >= t.CPI_KILL:
        return {
            "flag": "RED",
            "decision": "KILL",
            "confidence": 100,
            "reason": f"CPI ${cpi:.2f} >= kill threshold ${t.CPI_KILL}",
        }
    if cpc >= t.CPC_KILL:
        return {
            "flag": "RED",
            "decision": "KILL",
            "confidence": 100,
            "reason": f"CPC ${cpc:.2f} >= kill threshold ${t.CPC_KILL}",
        }
    if uepc >= t.UEPC_KILL:
        return {
            "flag": "RED",
            "decision": "KILL",
            "confidence": 100,
            "reason": f"uEPC ${uepc:.2f} >= kill threshold ${t.UEPC_KILL}",
        }

    # GREEN — scale conditions
    if uepc < t.UEPC_SCALE and cpi <= t.CPI_KILL:
        return {
            "flag": "GREEN",
            "decision": "SCALE",
            "confidence": 95,
            "reason": f"uEPC ${uepc:.2f} < scale threshold ${t.UEPC_SCALE} and CPI ${cpi:.2f} <= ${t.CPI_KILL}",
        }

    # YELLOW — watch conditions
    if t.UEPC_WATCH_LOW <= uepc < t.UEPC_WATCH_HIGH:
        return {
            "flag": "YELLOW",
            "decision": "WATCH",
            "confidence": 85,
            "reason": f"uEPC ${uepc:.2f} in watch zone [{t.UEPC_WATCH_LOW}, {t.UEPC_WATCH_HIGH})",
        }

    # Default fallback
    return {
        "flag": "WHITE",
        "decision": "INSUFFICIENT",
        "confidence": 70,
        "reason": "Metrics do not match any alert rule. Manual review recommended.",
    }
