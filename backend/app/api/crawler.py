from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.models import DailyStats
from app.schemas.hardware import CrawlerStatus, CrawlerRunResponse
from app.services import run_full_crawl
from app.crawler.xianyu import crawl_keyword

router = APIRouter(prefix="/crawler", tags=["crawler"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

# 最近一次爬取摘要（内存缓存，足够第一阶段使用）
_last_summary: dict | None = None


async def _do_crawl():
    global _last_summary
    async with AsyncSessionLocal() as db:
        _last_summary = await run_full_crawl(db)


@router.get("/status", response_model=CrawlerStatus)
async def get_status(db: DbDep):
    """返回最近一次爬取时间和结果"""
    result = await db.execute(
        select(func.max(DailyStats.stat_date))
    )
    last_date = result.scalar_one_or_none()

    success = _last_summary.get("success", 0) if _last_summary else 0
    failed = _last_summary.get("failed", 0) if _last_summary else 0

    return CrawlerStatus(last_run_date=last_date, last_run_success=success, last_run_failed=failed)


@router.post("/run", response_model=CrawlerRunResponse)
async def trigger_crawl(background_tasks: BackgroundTasks):
    """手动触发一次完整爬取（异步后台执行）"""
    background_tasks.add_task(_do_crawl)
    return CrawlerRunResponse(status="started", summary={"message": "爬取任务已在后台启动"})


@router.get("/test")
async def test_crawl(
    keyword: str = Query(..., description="搜索关键词，例如：RTX 4090"),
    pages: int = Query(1, ge=1, le=5, description="爬取页数（1-5）"),
):
    """调试接口：对单个关键词爬取并直接返回原始结果，不写入数据库"""
    items = await crawl_keyword(keyword, max_pages=pages)
    return {
        "keyword": keyword,
        "count": len(items),
        "items": [
            {
                "title": item.title,
                "price": item.price,
                "area": item.area,
                "seller": item.seller,
                "item_url": item.item_url,
                "publish_time": item.publish_time.isoformat() if item.publish_time else None,
            }
            for item in items
        ],
    }
