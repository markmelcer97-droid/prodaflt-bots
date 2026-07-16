"""
PRODAFLT FastAPI — Stats / Dashboard router
Aggregated metrics for the React dashboard and morning reports.
"""

from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DashboardStats, BaseResponse

router = APIRouter(prefix="/api/stats", tags=["Stats & Dashboard"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Aggregate stats for the React dashboard:
    - Total links, TZ specs, campaigns, active alerts
    - Approved vs pending links
    - Top creative codes by ROI
    - Recent alerts
    """
    # Total counts
    total_links = (await db.execute(text("SELECT COUNT(*) FROM links"))).scalar() or 0
    total_tz = (await db.execute(text("SELECT COUNT(*) FROM tz_specs"))).scalar() or 0
    total_campaigns = (await db.execute(text("SELECT COUNT(*) FROM campaign_metrics"))).scalar() or 0
    active_alerts = (
        await db.execute(
            text("SELECT COUNT(*) FROM alerts_log WHERE status IN ('new', 'acknowledged')")
        )
    ).scalar() or 0
    approved_links = (
        await db.execute(text("SELECT COUNT(*) FROM links WHERE status = 'analyzed'"))
    ).scalar() or 0
    pending_links = (
        await db.execute(text("SELECT COUNT(*) FROM links WHERE status = 'pending'"))
    ).scalar() or 0

    # Top 5 creatives by ROI
    top_creative_rows = (
        await db.execute(
            text("""
                SELECT creative_code, roi, uepc, cpi, status
                FROM campaign_metrics
                WHERE roi IS NOT NULL
                ORDER BY roi DESC
                LIMIT 5
            """)
        )
    ).mappings().all()
    top_creative_codes = [dict(r) for r in top_creative_rows]

    # Recent 5 alerts
    recent_alert_rows = (
        await db.execute(
            text("""
                SELECT id, alert_type, flag, confidence, decision, sent_at, status
                FROM alerts_log
                ORDER BY sent_at DESC NULLS LAST
                LIMIT 5
            """)
        )
    ).mappings().all()
    recent_alerts = [dict(r) for r in recent_alert_rows]

    return DashboardStats(
        total_links=total_links,
        total_tz_specs=total_tz,
        total_campaigns=total_campaigns,
        active_alerts=active_alerts,
        approved_links=approved_links,
        pending_links=pending_links,
        top_creative_codes=top_creative_codes,
        recent_alerts=recent_alerts,
    )


@router.get("/links/daily")
async def daily_link_stats(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Links added per day for the last N days (for activity chart)."""
    stmt = text("""
        SELECT DATE(added_at) AS day, COUNT(*) AS count
        FROM links
        WHERE added_at >= CURRENT_DATE - INTERVAL ':days days'
        GROUP BY DATE(added_at)
        ORDER BY day
    """)
    result = await db.execute(stmt, {"days": days})
    rows = result.mappings().all()
    return {"days": days, "data": [dict(r) for r in rows]}


@router.get("/team/activity")
async def team_activity(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Top contributors by links added in the last N days."""
    stmt = text("""
        SELECT u.username, u.team_role, COUNT(l.link_id) AS links_added
        FROM users u
        LEFT JOIN links l ON l.added_by = u.id
            AND l.added_at >= CURRENT_DATE - INTERVAL ':days days'
        WHERE u.is_active = true
        GROUP BY u.id, u.username, u.team_role
        ORDER BY links_added DESC
        LIMIT 10
    """)
    result = await db.execute(stmt, {"days": days})
    rows = result.mappings().all()
    return {"days": days, "top_users": [dict(r) for r in rows]}


@router.get("/pipeline")
async def pipeline_stats(db: AsyncSession = Depends(get_db)):
    """
    End-to-end pipeline status:
    pending → processing → analyzed → TZ created → metrics uploaded.
    """
    link_statuses = (
        await db.execute(
            text("SELECT status, COUNT(*) FROM links GROUP BY status")
        )
    ).mappings().all()
    tz_statuses = (
        await db.execute(
            text("SELECT status, COUNT(*) FROM tz_specs GROUP BY status")
        )
    ).mappings().all()
    campaign_statuses = (
        await db.execute(
            text("SELECT status, COUNT(*) FROM campaign_metrics GROUP BY status")
        )
    ).mappings().all()

    return {
        "links": {r["status"]: r["count"] for r in link_statuses},
        "tz_specs": {r["status"]: r["count"] for r in tz_statuses},
        "campaigns": {r["status"]: r["count"] for r in campaign_statuses},
    }


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Service + database health check."""
    try:
        result = await db.execute(text("SELECT 1"))
        db_ok = result.scalar() == 1
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
    }
