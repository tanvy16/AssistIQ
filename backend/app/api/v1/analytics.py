from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.services.ticket_analytics_service import ALLOWED_WINDOWS, ticket_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/tickets")
async def get_ticket_analytics(
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    if days not in ALLOWED_WINDOWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"days must be one of {list(ALLOWED_WINDOWS)}",
        )
    return await ticket_analytics(db, days)
