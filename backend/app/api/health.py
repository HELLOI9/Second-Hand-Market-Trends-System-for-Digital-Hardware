from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.health_service import crawler_health

router = APIRouter(prefix="/health", tags=["health"])
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/crawler")
async def get_crawler_health(db: DbDep):
    return await crawler_health(db)
