from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.deals_service import today_deals

router = APIRouter(prefix="/deals", tags=["deals"])
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/today")
async def get_today_deals(db: DbDep, limit: int = Query(20, ge=1, le=100)):
    return await today_deals(db, limit=limit)
