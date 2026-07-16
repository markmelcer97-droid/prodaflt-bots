"""
PRODAFLT FastAPI — Users router
CRUD + team role management for the gambling creative production team.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models import (
    UserCreate,
    UserOut,
    UserUpdate,
    BaseResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new team member."""
    stmt = text("""
        INSERT INTO users (telegram_id, username, first_name, role, team_role, is_active)
        VALUES (:telegram_id, :username, :first_name, :role, :team_role, :is_active)
        RETURNING id, telegram_id, username, first_name, role, team_role, is_active, created_at
    """)
    result = await db.execute(stmt, payload.model_dump())
    await db.commit()
    row = result.mappings().first()
    return UserOut(**dict(row))


@router.get("", response_model=PaginatedResponse)
async def list_users(
    role: Optional[str] = Query(None, description="Filter by user role"),
    team_role: Optional[str] = Query(None, description="Filter by team role"),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List team members with filtering and pagination."""
    # Build WHERE clause
    conditions = ["1=1"]
    params: dict = {}
    if role:
        conditions.append("role = :role")
        params["role"] = role
    if team_role:
        conditions.append("team_role = :team_role")
        params["team_role"] = team_role
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active

    where_clause = " AND ".join(conditions)

    # Count total
    count_stmt = text(f"SELECT COUNT(*) FROM users WHERE {where_clause}")
    total_result = await db.execute(count_stmt, params)
    total = total_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    select_stmt = text(f"""
        SELECT id, telegram_id, username, first_name, role, team_role, is_active, created_at
        FROM users
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
        items=[UserOut(**dict(r)).model_dump() for r in rows],
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single user by ID."""
    stmt = text("""
        SELECT id, telegram_id, username, first_name, role, team_role, is_active, created_at
        FROM users WHERE id = :user_id
    """)
    result = await db.execute(stmt, {"user_id": user_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(**dict(row))


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update user fields (partial)."""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["user_id"] = user_id

    stmt = text(f"""
        UPDATE users SET {set_clause}
        WHERE id = :user_id
        RETURNING id, telegram_id, username, first_name, role, team_role, is_active, created_at
    """)
    result = await db.execute(stmt, data)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(**dict(row))


@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete a user by setting is_active = false."""
    stmt = text("UPDATE users SET is_active = false WHERE id = :user_id")
    result = await db.execute(stmt, {"user_id": user_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return BaseResponse(success=True, message="User deactivated")
