"""
LLM validation API routes.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.services.llm_validator import validate_batch, get_validation_status

router = APIRouter(prefix="/validator", tags=["validator"])


async def _run_validation_task(limit: int) -> None:
    async with AsyncSessionLocal() as db:
        await validate_batch(db, limit)


@router.post("/run")
async def run_validation(
    background_tasks: BackgroundTasks,
    limit: int = 100,
):
    """Trigger LLM validation for unvalidated snapshots (background task)."""
    background_tasks.add_task(_run_validation_task, limit)
    return {"status": "started", "limit": limit}


@router.get("/status")
async def validation_status(db: AsyncSession = Depends(get_db)):
    """Get validation progress."""
    return await get_validation_status(db)
