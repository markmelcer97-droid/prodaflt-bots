"""
PRODAFLT FastAPI — Patterns router
Viral content patterns discovered by Researcher, with scoring and frequency.
"""

from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models import (
    PatternCreate,
    PatternOut,
    PatternUpdate,
    BaseResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/patterns", tags=["Patterns"])


@router.post("", response_model=PatternOut, status_code=status.HTTP_201_CREATED)
async def create_pattern(payload: PatternCreate, db: AsyncSession = Depends(get_db)):
    """Register a new content pattern (called by Researcher skill)."""
    stmt = text("""
        INSERT INTO patterns (name, description, examples, frequency, week_of, metrics)
        VALUES (:name, :description, :examples, :frequency, :week_of, :metrics)
        RETURNING id, name, description, examples, frequency, week_of, metrics, created_at
    """)
    result = await db.execute(stmt, payload.model_dump())
    await db.commit()
    row = result.mappings().first()
    return PatternOut(**dict(row))


@router.get("", response_model=PaginatedResponse)
async def list_patterns(
    name: Optional[str] = Query(None),
    week_of: Optional[date] = Query(None),
    min_frequency: Optional[int] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List discovered patterns with filters."""
    conditions = ["1=1"]
    params: dict = {}
    if name:
        conditions.append("name ILIKE :name")
        params["name"] = f"%{name}%"
    if week_of:
        conditions.append("week_of = :week_of")
        params["week_of"] = week_of
    if min_frequency is not None:
        conditions.append("frequency >= :min_frequency")
        params["min_frequency"] = min_frequency

    where_clause = " AND ".join(conditions)

    count_stmt = text(f"SELECT COUNT(*) FROM patterns WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT id, name, description, examples, frequency, week_of, metrics, created_at
        FROM patterns
        WHERE {where_clause}
        ORDER BY frequency DESC NULLS LAST, created_at DESC
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
        items=[PatternOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/{pattern_id}", response_model=PatternOut)
async def get_pattern(pattern_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single pattern."""
    stmt = text("""
        SELECT id, name, description, examples, frequency, week_of, metrics, created_at
        FROM patterns WHERE id = :pattern_id
    """)
    result = await db.execute(stmt, {"pattern_id": pattern_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return PatternOut(**dict(row))


@router.patch("/{pattern_id}", response_model=PatternOut)
async def update_pattern(
    pattern_id: int, payload: PatternUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a pattern (partial)."""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["pattern_id"] = pattern_id

    stmt = text(f"""
        UPDATE patterns SET {set_clause}
        WHERE id = :pattern_id
        RETURNING id, name, description, examples, frequency, week_of, metrics, created_at
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return PatternOut(**dict(row))


@router.delete("/{pattern_id}", response_model=BaseResponse)
async def delete_pattern(pattern_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a pattern."""
    stmt = text("DELETE FROM patterns WHERE id = :pattern_id")
    result = await db.execute(stmt, {"pattern_id": pattern_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return BaseResponse(success=True, message="Pattern deleted")
