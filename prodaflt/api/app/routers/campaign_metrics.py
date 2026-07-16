"""
PRODAFLT FastAPI — Campaign Metrics router
Upload performance data, query top creatives, derived metrics auto-calculated.
"""

from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models import (
    CampaignMetricsCreate,
    CampaignMetricsOut,
    CampaignMetricsUpdate,
    CampaignMetricsListResponse,
    BaseResponse,
)

router = APIRouter(prefix="/api/metrics", tags=["Campaign Metrics"])


def _derive_metrics(data: dict) -> dict:
    """Auto-calculate CPC, CPI, uEPC, ROI from raw numbers."""
    spend = data.get("spend") or 0
    clicks = data.get("clicks") or 0
    installs = data.get("installs") or 0
    deposits = data.get("deposits") or 0
    revenue = data.get("revenue") or 0

    if clicks and spend:
        data["cpc"] = Decimal(str(spend)) / Decimal(str(clicks))
    if installs and spend:
        data["cpi"] = Decimal(str(spend)) / Decimal(str(installs))
    if installs:
        # uEPC = revenue per install (or spend per install if revenue unknown)
        rev = revenue if revenue else spend
        data["uepc"] = Decimal(str(rev)) / Decimal(str(installs))
    if spend and revenue:
        data["roi"] = (Decimal(str(revenue)) - Decimal(str(spend))) / Decimal(str(spend))

    return data


@router.post("", response_model=CampaignMetricsOut, status_code=status.HTTP_201_CREATED)
async def create_metrics(payload: CampaignMetricsCreate, db: AsyncSession = Depends(get_db)):
    """Upload campaign metrics (from Keitaro, Meta API, or manual input)."""
    data = payload.model_dump()
    data = _derive_metrics(data)

    stmt = text("""
        INSERT INTO campaign_metrics (creative_code, spend, clicks, installs, deposits,
            cpc, cpi, uepc, roi, revenue, status)
        VALUES (:creative_code, :spend, :clicks, :installs, :deposits,
            :cpc, :cpi, :uepc, :roi, :revenue, :status)
        RETURNING id, creative_code, spend, clicks, installs, deposits,
            cpc, cpi, uepc, roi, revenue, status, recorded_at
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    return CampaignMetricsOut(**dict(row))


@router.get("", response_model=CampaignMetricsListResponse)
async def list_metrics(
    creative_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="active|paused|completed|archived"),
    min_roi: Optional[float] = Query(None),
    max_cpi: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List campaign metrics with filters."""
    conditions = ["1=1"]
    params: dict = {}
    if creative_code:
        conditions.append("creative_code = :creative_code")
        params["creative_code"] = creative_code
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if min_roi is not None:
        conditions.append("roi >= :min_roi")
        params["min_roi"] = min_roi
    if max_cpi is not None:
        conditions.append("cpi <= :max_cpi")
        params["max_cpi"] = max_cpi

    where_clause = " AND ".join(conditions)

    count_stmt = text(f"SELECT COUNT(*) FROM campaign_metrics WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT id, creative_code, spend, clicks, installs, deposits,
            cpc, cpi, uepc, roi, revenue, status, recorded_at
        FROM campaign_metrics
        WHERE {where_clause}
        ORDER BY recorded_at DESC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = page_size
    params["offset"] = offset
    result = await db.execute(select_stmt, params)
    rows = result.mappings().all()

    return CampaignMetricsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=[CampaignMetricsOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/top", response_model=CampaignMetricsListResponse)
async def top_creatives(
    by: str = Query("roi", description="Sort by: roi|uepc|revenue|installs"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get top-performing creatives by a chosen metric."""
    allowed = {"roi", "uepc", "revenue", "installs"}
    if by not in allowed:
        raise HTTPException(status_code=400, detail=f"Sort by must be one of {allowed}")

    stmt = text(f"""
        SELECT id, creative_code, spend, clicks, installs, deposits,
            cpc, cpi, uepc, roi, revenue, status, recorded_at
        FROM campaign_metrics
        WHERE {by} IS NOT NULL
        ORDER BY {by} DESC
        LIMIT :limit
    """)
    result = await db.execute(stmt, {"limit": limit})
    rows = result.mappings().all()

    return CampaignMetricsListResponse(
        total=len(rows),
        page=1,
        page_size=limit,
        pages=1,
        items=[CampaignMetricsOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/{metric_id}", response_model=CampaignMetricsOut)
async def get_metric(metric_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single metrics record."""
    stmt = text("""
        SELECT id, creative_code, spend, clicks, installs, deposits,
            cpc, cpi, uepc, roi, revenue, status, recorded_at
        FROM campaign_metrics WHERE id = :metric_id
    """)
    result = await db.execute(stmt, {"metric_id": metric_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Metrics record not found")
    return CampaignMetricsOut(**dict(row))


@router.patch("/{metric_id}", response_model=CampaignMetricsOut)
async def update_metric(
    metric_id: int, payload: CampaignMetricsUpdate, db: AsyncSession = Depends(get_db)
):
    """Update campaign metrics (partial). Re-derives calculated fields."""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Re-derive if raw fields changed
    if any(k in data for k in ("spend", "clicks", "installs", "deposits", "revenue")):
        # Fetch current row to fill gaps
        current = await db.execute(
            text("""
                SELECT creative_code, spend, clicks, installs, deposits, revenue, status
                FROM campaign_metrics WHERE id = :metric_id
            """),
            {"metric_id": metric_id},
        )
        cur = current.mappings().first()
        if not cur:
            raise HTTPException(status_code=404, detail="Metrics record not found")
        merged = dict(cur)
        merged.update(data)
        data = _derive_metrics(merged)

    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys() if k != "metric_id"])
    data["metric_id"] = metric_id

    stmt = text(f"""
        UPDATE campaign_metrics SET {set_clause}
        WHERE id = :metric_id
        RETURNING id, creative_code, spend, clicks, installs, deposits,
            cpc, cpi, uepc, roi, revenue, status, recorded_at
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Metrics record not found")
    return CampaignMetricsOut(**dict(row))


@router.delete("/{metric_id}", response_model=BaseResponse)
async def delete_metric(metric_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a metrics record."""
    stmt = text("DELETE FROM campaign_metrics WHERE id = :metric_id")
    result = await db.execute(stmt, {"metric_id": metric_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Metrics record not found")
    return BaseResponse(success=True, message="Metrics record deleted")
