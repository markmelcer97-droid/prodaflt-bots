"""
PRODAFLT FastAPI — Alerts router
Alert Engine: RED/GREEN/YELLOW/WHITE with confidence levels.
"""

from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, evaluate_alert
from app.models import (
    AlertCreate,
    AlertOut,
    AlertUpdate,
    AlertListResponse,
    AlertEvaluationRequest,
    AlertEvaluationResponse,
    BaseResponse,
)

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.post("/evaluate", response_model=AlertEvaluationResponse)
async def evaluate_campaign_alert(payload: AlertEvaluationRequest):
    """
    Run Alert Engine on a single set of metrics (no DB write).
    Returns flag, decision, confidence, reason.
    """
    result = evaluate_alert(
        spend=float(payload.spend),
        clicks=payload.clicks,
        installs=payload.installs,
        cpi=float(payload.cpi),
        cpc=float(payload.cpc),
        uepc=float(payload.uepc),
    )
    return AlertEvaluationResponse(
        flag=result["flag"],
        decision=result["decision"],
        confidence=result["confidence"],
        reason=result["reason"],
        thresholds={
            "cpi_kill": 5.0,
            "cpc_kill": 2.5,
            "uepc_kill": 8.0,
            "uepc_scale": 4.0,
            "uepc_watch_low": 6.0,
            "uepc_watch_high": 8.0,
            "min_spend": 12.0,
            "min_clicks": 8,
        },
    )


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(payload: AlertCreate, db: AsyncSession = Depends(get_db)):
    """Log an alert (usually called by Data Analyst Bot after evaluation)."""
    stmt = text("""
        INSERT INTO alerts_log (campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, status)
        VALUES (:campaign_id, :alert_type, :flag, :triggered_metrics,
            :confidence, :decision, :reason, :sent_to, 'new')
        RETURNING id, campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, sent_at, status
    """)
    result = await db.execute(stmt, payload.model_dump())
    await db.commit()
    row = result.mappings().first()
    return AlertOut(**dict(row))


@router.get("/active", response_model=AlertListResponse)
async def active_alerts(
    alert_type: Optional[str] = Query(None),
    flag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """Get active (new or acknowledged) alerts."""
    conditions = ["status IN ('new', 'acknowledged')"]
    params: dict = {}
    if alert_type:
        conditions.append("alert_type = :alert_type")
        params["alert_type"] = alert_type
    if flag:
        conditions.append("flag = :flag")
        params["flag"] = flag

    where_clause = " AND ".join(conditions)

    count_stmt = text(f"SELECT COUNT(*) FROM alerts_log WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT id, campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, sent_at, status
        FROM alerts_log
        WHERE {where_clause}
        ORDER BY sent_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = page_size
    params["offset"] = offset
    result = await db.execute(select_stmt, params)
    rows = result.mappings().all()

    return AlertListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=[AlertOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(None, description="new|acknowledged|resolved|dismissed"),
    alert_type: Optional[str] = Query(None),
    flag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List all alerts with filters."""
    conditions = ["1=1"]
    params: dict = {}
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if alert_type:
        conditions.append("alert_type = :alert_type")
        params["alert_type"] = alert_type
    if flag:
        conditions.append("flag = :flag")
        params["flag"] = flag

    where_clause = " AND ".join(conditions)

    count_stmt = text(f"SELECT COUNT(*) FROM alerts_log WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT id, campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, sent_at, status
        FROM alerts_log
        WHERE {where_clause}
        ORDER BY sent_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = page_size
    params["offset"] = offset
    result = await db.execute(select_stmt, params)
    rows = result.mappings().all()

    return AlertListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=[AlertOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single alert."""
    stmt = text("""
        SELECT id, campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, sent_at, status
        FROM alerts_log WHERE id = :alert_id
    """)
    result = await db.execute(stmt, {"alert_id": alert_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut(**dict(row))


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(alert_id: int, payload: AlertUpdate, db: AsyncSession = Depends(get_db)):
    """Update alert status or details (partial)."""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["alert_id"] = alert_id

    stmt = text(f"""
        UPDATE alerts_log SET {set_clause}
        WHERE id = :alert_id
        RETURNING id, campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, sent_at, status
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut(**dict(row))


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark alert as acknowledged."""
    stmt = text("""
        UPDATE alerts_log SET status = 'acknowledged' WHERE id = :alert_id
        RETURNING id, campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, sent_at, status
    """)
    result = await db.execute(stmt, {"alert_id": alert_id})
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut(**dict(row))


@router.post("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark alert as resolved."""
    stmt = text("""
        UPDATE alerts_log SET status = 'resolved' WHERE id = :alert_id
        RETURNING id, campaign_id, alert_type, flag, triggered_metrics,
            confidence, decision, reason, sent_to, sent_at, status
    """)
    result = await db.execute(stmt, {"alert_id": alert_id})
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut(**dict(row))


@router.delete("/{alert_id}", response_model=BaseResponse)
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an alert."""
    stmt = text("DELETE FROM alerts_log WHERE id = :alert_id")
    result = await db.execute(stmt, {"alert_id": alert_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return BaseResponse(success=True, message="Alert deleted")
