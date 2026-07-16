"""
PRODAFLT FastAPI — Content Analysis router
Researcher writes analysis results; Compliance updates moderation status.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models import (
    ContentAnalysisCreate,
    ContentAnalysisOut,
    ContentAnalysisUpdate,
    BaseResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/content-analysis", tags=["Content Analysis"])


@router.post("", response_model=ContentAnalysisOut, status_code=status.HTTP_201_CREATED)
async def create_analysis(payload: ContentAnalysisCreate, db: AsyncSession = Depends(get_db)):
    """Submit researcher analysis for a link."""
    stmt = text("""
        INSERT INTO content_analysis (link_id, pattern, researcher_comment, compliance_status,
            compliance_comment, creative_potential, assigned_code)
        VALUES (:link_id, :pattern, :researcher_comment, :compliance_status,
            :compliance_comment, :creative_potential, :assigned_code)
        RETURNING id, link_id, pattern, researcher_comment, compliance_status,
            compliance_comment, creative_potential, assigned_code, created_at
    """)
    result = await db.execute(stmt, payload.model_dump())
    await db.commit()
    row = result.mappings().first()

    # Auto-update link status to analyzed
    await db.execute(
        text("UPDATE links SET status = 'analyzed' WHERE link_id = :link_id"),
        {"link_id": payload.link_id},
    )
    await db.commit()

    return ContentAnalysisOut(**dict(row))


@router.get("", response_model=PaginatedResponse)
async def list_analysis(
    link_id: Optional[int] = Query(None),
    compliance_status: Optional[str] = Query(None, description="pending|compliant|non_compliant|flagged"),
    assigned_code: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List content analysis records with filters."""
    conditions = ["1=1"]
    params: dict = {}
    if link_id:
        conditions.append("link_id = :link_id")
        params["link_id"] = link_id
    if compliance_status:
        conditions.append("compliance_status = :compliance_status")
        params["compliance_status"] = compliance_status
    if assigned_code:
        conditions.append("assigned_code = :assigned_code")
        params["assigned_code"] = assigned_code

    where_clause = " AND ".join(conditions)

    count_stmt = text(f"SELECT COUNT(*) FROM content_analysis WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT id, link_id, pattern, researcher_comment, compliance_status,
            compliance_comment, creative_potential, assigned_code, created_at
        FROM content_analysis
        WHERE {where_clause}
        ORDER BY created_at DESC
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
        items=[ContentAnalysisOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/{analysis_id}", response_model=ContentAnalysisOut)
async def get_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single analysis record."""
    stmt = text("""
        SELECT id, link_id, pattern, researcher_comment, compliance_status,
            compliance_comment, creative_potential, assigned_code, created_at
        FROM content_analysis WHERE id = :analysis_id
    """)
    result = await db.execute(stmt, {"analysis_id": analysis_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis record not found")
    return ContentAnalysisOut(**dict(row))


@router.patch("/{analysis_id}", response_model=ContentAnalysisOut)
async def update_analysis(
    analysis_id: int, payload: ContentAnalysisUpdate, db: AsyncSession = Depends(get_db)
):
    """Update analysis — used by Compliance to set status, or Researcher to refine."""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["analysis_id"] = analysis_id

    stmt = text(f"""
        UPDATE content_analysis SET {set_clause}
        WHERE id = :analysis_id
        RETURNING id, link_id, pattern, researcher_comment, compliance_status,
            compliance_comment, creative_potential, assigned_code, created_at
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis record not found")
    return ContentAnalysisOut(**dict(row))


@router.delete("/{analysis_id}", response_model=BaseResponse)
async def delete_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an analysis record."""
    stmt = text("DELETE FROM content_analysis WHERE id = :analysis_id")
    result = await db.execute(stmt, {"analysis_id": analysis_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Analysis record not found")
    return BaseResponse(success=True, message="Analysis record deleted")
