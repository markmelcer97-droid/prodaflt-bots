"""
PRODAFLT FastAPI — TZ Specs router
Creative briefs: frame-by-frame scripts, visual refs, status pipeline.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models import (
    TzSpecCreate,
    TzSpecOut,
    TzSpecUpdate,
    BaseResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/tz", tags=["TZ Specs"])


@router.post("", response_model=TzSpecOut, status_code=status.HTTP_201_CREATED)
async def create_tz(payload: TzSpecCreate, db: AsyncSession = Depends(get_db)):
    """Create a new creative brief (TZ)."""
    stmt = text("""
        INSERT INTO tz_specs (code_content, title, description, script, visual_refs,
            target_audience, platform, status, created_by, assigned_to, asana_task_id)
        VALUES (:code_content, :title, :description, :script, :visual_refs,
            :target_audience, :platform, :status, :created_by, :assigned_to, :asana_task_id)
        RETURNING id, code_content, title, description, script, visual_refs,
            target_audience, platform, status, created_by, assigned_to, asana_task_id,
            created_at, updated_at
    """)
    result = await db.execute(stmt, payload.model_dump())
    await db.commit()
    row = result.mappings().first()
    return TzSpecOut(**dict(row))


@router.get("", response_model=PaginatedResponse)
async def list_tz_specs(
    status: Optional[str] = Query(None, description="draft|in_review|approved|rejected|archived"),
    platform: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    code_content: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List creative briefs with filters."""
    conditions = ["1=1"]
    params: dict = {}
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if platform:
        conditions.append("platform = :platform")
        params["platform"] = platform
    if assigned_to:
        conditions.append("assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to
    if code_content:
        conditions.append("code_content ILIKE :code_content")
        params["code_content"] = f"%{code_content}%"

    where_clause = " AND ".join(conditions)

    count_stmt = text(f"SELECT COUNT(*) FROM tz_specs WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT id, code_content, title, description, script, visual_refs,
            target_audience, platform, status, created_by, assigned_to, asana_task_id,
            created_at, updated_at
        FROM tz_specs
        WHERE {where_clause}
        ORDER BY updated_at DESC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = page_size
    params["offset"] = offset
    result = await db.execute(select_stmt, params)
    rows = result.mappings().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=[TzSpecOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/{tz_id}", response_model=TzSpecOut)
async def get_tz(tz_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single creative brief."""
    stmt = text("""
        SELECT id, code_content, title, description, script, visual_refs,
            target_audience, platform, status, created_by, assigned_to, asana_task_id,
            created_at, updated_at
        FROM tz_specs WHERE id = :tz_id
    """)
    result = await db.execute(stmt, {"tz_id": tz_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="TZ spec not found")
    return TzSpecOut(**dict(row))


@router.patch("/{tz_id}", response_model=TzSpecOut)
async def update_tz(tz_id: int, payload: TzSpecUpdate, db: AsyncSession = Depends(get_db)):
    """Update a creative brief (partial)."""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Always bump updated_at
    data["updated_at"] = datetime.utcnow()
    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["tz_id"] = tz_id

    stmt = text(f"""
        UPDATE tz_specs SET {set_clause}
        WHERE id = :tz_id
        RETURNING id, code_content, title, description, script, visual_refs,
            target_audience, platform, status, created_by, assigned_to, asana_task_id,
            created_at, updated_at
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="TZ spec not found")
    return TzSpecOut(**dict(row))


@router.delete("/{tz_id}", response_model=BaseResponse)
async def delete_tz(tz_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a creative brief."""
    stmt = text("DELETE FROM tz_specs WHERE id = :tz_id")
    result = await db.execute(stmt, {"tz_id": tz_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="TZ spec not found")
    return BaseResponse(success=True, message="TZ spec deleted")


@router.post("/{tz_id}/approve", response_model=TzSpecOut)
async def approve_tz(tz_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a creative brief (status → approved)."""
    stmt = text("""
        UPDATE tz_specs SET status = 'approved', updated_at = NOW()
        WHERE id = :tz_id
        RETURNING id, code_content, title, description, script, visual_refs,
            target_audience, platform, status, created_by, assigned_to, asana_task_id,
            created_at, updated_at
    """)
    result = await db.execute(stmt, {"tz_id": tz_id})
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="TZ spec not found")
    return TzSpecOut(**dict(row))


@router.post("/{tz_id}/reject", response_model=TzSpecOut)
async def reject_tz(tz_id: int, db: AsyncSession = Depends(get_db)):
    """Reject a creative brief (status → rejected)."""
    stmt = text("""
        UPDATE tz_specs SET status = 'rejected', updated_at = NOW()
        WHERE id = :tz_id
        RETURNING id, code_content, title, description, script, visual_refs,
            target_audience, platform, status, created_by, assigned_to, asana_task_id,
            created_at, updated_at
    """)
    result = await db.execute(stmt, {"tz_id": tz_id})
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="TZ spec not found")
    return TzSpecOut(**dict(row))
