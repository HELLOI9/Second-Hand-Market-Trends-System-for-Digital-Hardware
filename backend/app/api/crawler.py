from app.core.timezone import now_cst, today_cst
import asyncio
import logging
import threading
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.models import CrawlRun, DailyStats
from app.schemas.hardware import CrawlerStatus, CrawlerRunResponse
from app.services import run_full_crawl
from app.crawler.xianyu import crawl_keyword

router = APIRouter(prefix="/crawler", tags=["crawler"])
logger = logging.getLogger(__name__)

DbDep = Annotated[AsyncSession, Depends(get_db)]

# 最近一次爬取摘要（内存缓存，足够第一阶段使用）
_last_summary: dict | None = None
_crawl_lock = threading.Lock()
_crawl_running = False
_crawl_stop_event = threading.Event()


async def _do_crawl(force: bool = False):
    global _last_summary
    async with AsyncSessionLocal() as db:
        _last_summary = await run_full_crawl(db, force=force, should_stop=_crawl_stop_event.is_set)


async def _do_thread_crawl(force: bool = False):
    global _last_summary
    engine = create_async_engine(settings.database_url, echo=settings.debug)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            _last_summary = await run_full_crawl(db, force=force, should_stop=_crawl_stop_event.is_set)
    finally:
        await engine.dispose()


def _crawl_thread_entry(force: bool = False) -> None:
    global _crawl_running
    try:
        asyncio.run(_do_thread_crawl(force))
    except Exception:
        logger.exception("手动采集任务异常退出")
    finally:
        with _crawl_lock:
            _crawl_running = False


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


ACTIVE_RUN_STATUSES = ("running", "crawling", "validating", "aggregating")


@router.post("/run", response_model=CrawlerRunResponse)
async def trigger_crawl(db: DbDep, force: bool = Query(False)):
    """手动触发一次完整爬取（异步后台执行）"""
    global _crawl_running
    active_run = (
        await db.execute(
            select(CrawlRun)
            .where(CrawlRun.status.in_(ACTIVE_RUN_STATUSES), CrawlRun.ended_at.is_(None))
            .order_by(CrawlRun.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if active_run is not None:
        return CrawlerRunResponse(
            status="running",
            summary={
                "message": "已有采集任务正在运行，请等待完成后再开始新一轮监测",
                "force": force,
                "active_run_id": active_run.id,
                "active_status": active_run.status,
            },
        )

    # 检查是否有单硬件采集正在运行
    from app.api.hardware import _hw_crawl_lock, _hw_crawls
    with _hw_crawl_lock:
        if any(v for v in _hw_crawls.values()):
            return CrawlerRunResponse(
                status="running",
                summary={"message": "请等待当前采集完毕后再开始新一轮监测", "force": force},
            )

    with _crawl_lock:
        if _crawl_running:
            return CrawlerRunResponse(status="running", summary={"message": "已有采集任务正在运行", "force": force})
        _crawl_stop_event.clear()
        _crawl_running = True
    threading.Thread(target=_crawl_thread_entry, args=(force,), daemon=True).start()
    message = "强制真实采集任务已在后台启动" if force else "爬取任务已在后台启动"
    return CrawlerRunResponse(status="started", summary={"message": message, "force": force})


@router.post("/pause", response_model=CrawlerRunResponse)
async def pause_crawl(db: DbDep):
    """请求暂停当前采集任务。"""
    _crawl_stop_event.set()
    active_run = (
        await db.execute(
            select(CrawlRun)
            .where(CrawlRun.status.in_(ACTIVE_RUN_STATUSES), CrawlRun.ended_at.is_(None))
            .order_by(CrawlRun.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if active_run is None:
        return CrawlerRunResponse(status="idle", summary={"message": "当前没有正在运行的采集任务"})

    active_run.status = "interrupted"
    active_run.ended_at = now_cst()
    await db.commit()
    return CrawlerRunResponse(
        status="paused",
        summary={
            "message": "已请求暂停当前采集任务",
            "active_run_id": active_run.id,
        },
    )


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
