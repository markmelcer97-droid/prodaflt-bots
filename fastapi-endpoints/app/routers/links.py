"""
PRODAFLT FastAPI — Links router
Content pipeline entry: Parser Bot writes here, Researcher reads from here.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models import (
    LinkCreate,
    LinkOut,
    LinkUpdate,
    LinkListResponse,
    BaseResponse,
)

router = APIRouter(prefix="/api/links", tags=["Links"])


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(payload: LinkCreate, db: AsyncSession = Depends(get_db)):
    """Add a new content link (usually called by Parser Bot)."""
    stmt = text("""
        INSERT INTO links (url, platform, title, description, duration, status, added_by, preview_url, metadata)
        VALUES (:url, :platform, :title, :description, :duration, :status, :added_by, :preview_url, :metadata)
        RETURNING link_id, url, platform, title, description, duration, status, added_by, added_at, preview_url, metadata
    """)
    result = await db.execute(stmt, payload.model_dump())
    await db.commit()
    row = result.mappings().first()
    return LinkOut(**dict(row))


@router.get("", response_model=LinkListResponse)
async def list_links(
    status: Optional[str] = Query(None, description="Filter by status: pending|processing|analyzed|failed|archived"),
    platform: Optional[str] = Query(None),
    added_by: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="Search in URL or title"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List content links with filters and pagination."""
    conditions = ["1=1"]
    params: dict = {}
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if platform:
        conditions.append("platform = :platform")
        params["platform"] = platform
    if added_by:
        conditions.append("added_by = :added_by")
        params["added_by"] = added_by
    if search:
        conditions.append("(url ILIKE :search OR title ILIKE :search)")
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(conditions)

    count_stmt = text(f"SELECT COUNT(*) FROM links WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT link_id, url, platform, title, description, duration, status, added_by, added_at, preview_url, metadata
        FROM links
        WHERE {where_clause}
        ORDER BY added_at DESC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = page_size
    params["offset"] = offset
    result = await db.execute(select_stmt, params)
    rows = result.mappings().all()

    return LinkListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=[LinkOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/{link_id}", response_model=LinkOut)
async def get_link(link_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single link with its details."""
    stmt = text("""
        SELECT link_id, url, platform, title, description, duration, status, added_by, added_at, preview_url, metadata
        FROM links WHERE link_id = :link_id
    """)
    result = await db.execute(stmt, {"link_id": link_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")
    return LinkOut(**dict(row))


@router.patch("/{link_id}", response_model=LinkOut)
async def update_link(link_id: int, payload: LinkUpdate, db: AsyncSession = Depends(get_db)):
    """Update link status or metadata (partial update)."""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["link_id"] = link_id

    stmt = text(f"""
        UPDATE links SET {set_clause}
        WHERE link_id = :link_id
        RETURNING link_id, url, platform, title, description, duration, status, added_by, added_at, preview_url, metadata
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")
    return LinkOut(**dict(row))


@router.delete("/{link_id}", response_model=BaseResponse)
async def delete_link(link_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a link (cascades to content_analysis via FK)."""
    stmt = text("DELETE FROM links WHERE link_id = :link_id")
    result = await db.execute(stmt, {"link_id": link_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    return BaseResponse(success=True, message="Link deleted")


@router.post("/{link_id}/analyze", response_model=BaseResponse)
async def trigger_link_analysis(link_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a link as processing — signals Researcher to pick it up."""
    stmt = text("""
        UPDATE links SET status = 'processing' WHERE link_id = :link_id
        RETURNING link_id
    """)
    result = await db.execute(stmt, {"link_id": link_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    return BaseResponse(success=True, message="Link marked for analysis")
