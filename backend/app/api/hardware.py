import asyncio
import threading
from datetime import timedelta
from app.core.timezone import today_cst
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, desc, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import require_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.hardware_pool import HARDWARE_POOL
from app.models import HardwareItem, DailyStats, PriceSnapshot, CrawlRun
from app.schemas.hardware import (
    HardwareCreate,
    HardwareDetail,
    HardwareUpdate,
    DailyStatsOut,
    TrendResponse,
    TrendPoint,
    HardwareSampleOut,
)
from app.services.hardware_pool_service import run_single_hardware_crawl

router = APIRouter(prefix="/hardware", tags=["hardware"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[None, Depends(require_admin)]

# ── 单硬件立即采集任务状态 ────────────────────────────────────────
_hw_crawl_lock = threading.Lock()
_hw_crawls: dict[int, bool] = {}   # hw_id → running
_hw_run_ids: dict[int, int] = {}   # hw_id → latest CrawlRun.id
HARDWARE_ORDER_FALLBACK = 10_000


async def _global_latest_stat_date(db: AsyncSession):
    """全站最近一轮采集日期（所有 DailyStats 的 MAX(stat_date)）。

    作为聚合视图（首页环图/热力图/表格）的锚点：只有该日当天有统计的商品
    才计入分布，缺数据的商品归为「今日无数据」，不再回退到历史旧数据。
    """
    from sqlalchemy import func
    return (
        await db.execute(select(func.max(DailyStats.stat_date)))
    ).scalar()


@router.get("", response_model=dict[str, list[HardwareDetail]])
async def list_hardware(db: DbDep):
    """返回所有硬件（含最新统计），按分类分组"""
    result = await db.execute(select(HardwareItem).where(HardwareItem.is_active == True))
    items = result.scalars().all()
    items.sort(
        key=lambda item: (
            item.category,
            item.id if item.id is not None else HARDWARE_ORDER_FALLBACK,
            item.name,
        )
    )

    # 锚定全站最近一轮采集日：只取该日当天有统计的商品，缺数据者归为「今日无数据」
    anchor_date = await _global_latest_stat_date(db)
    latest_stats: dict[int, DailyStats] = {}
    if anchor_date is not None:
        stats_result = await db.execute(
            select(DailyStats).where(DailyStats.stat_date == anchor_date)
        )
        latest_stats = {s.hardware_id: s for s in stats_result.scalars().all()}

    grouped: dict[str, list[HardwareDetail]] = {}
    for item in items:
        stats = latest_stats.get(item.id)
        detail = HardwareDetail(
            id=item.id,
            name=item.name,
            category=item.category,
            latest_stats=DailyStatsOut.model_validate(stats) if stats else None,
            latest_run_date=anchor_date,
        )
        grouped.setdefault(item.category, []).append(detail)
    return grouped


@router.get("/admin", response_model=list[HardwareDetail])
async def list_hardware_admin(db: DbDep, _: AdminDep):
    result = await db.execute(select(HardwareItem).order_by(HardwareItem.category, HardwareItem.id))
    items = result.scalars().all()

    # 与首页口径一致：锚定全站最近一轮采集日
    anchor_date = await _global_latest_stat_date(db)
    latest_stats: dict[int, DailyStats] = {}
    if anchor_date is not None:
        stats_result = await db.execute(
            select(DailyStats).where(DailyStats.stat_date == anchor_date)
        )
        latest_stats = {s.hardware_id: s for s in stats_result.scalars().all()}

    return [
        HardwareDetail(
            id=item.id,
            name=item.name,
            category=item.category,
            search_keywords=item.search_keywords,
            validation_rule=item.validation_rule,
            is_active=item.is_active,
            latest_stats=DailyStatsOut.model_validate(latest_stats.get(item.id)) if latest_stats.get(item.id) else None,
            latest_run_date=anchor_date,
        )
        for item in items
    ]


async def _cold_start(hardware_id: int):
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        hardware = await session.get(HardwareItem, hardware_id)
        if hardware is not None:
            await run_single_hardware_crawl(session, hardware)


@router.post("", response_model=HardwareDetail)
async def create_hardware(payload: HardwareCreate, background_tasks: BackgroundTasks, db: DbDep, _: AdminDep):
    item = HardwareItem(
        name=payload.name,
        category=payload.category,
        search_keywords=payload.search_keywords or [payload.name],
        validation_rule=payload.validation_rule,
        is_active=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    if payload.cold_start:
        background_tasks.add_task(_cold_start, item.id)
    return HardwareDetail(id=item.id, name=item.name, category=item.category, search_keywords=item.search_keywords, validation_rule=item.validation_rule, is_active=item.is_active)


@router.patch("/{hardware_id}", response_model=HardwareDetail)
async def update_hardware(hardware_id: int, payload: HardwareUpdate, db: DbDep, _: AdminDep):
    item = await db.get(HardwareItem, hardware_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Hardware not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return HardwareDetail(id=item.id, name=item.name, category=item.category, search_keywords=item.search_keywords, validation_rule=item.validation_rule, is_active=item.is_active)


@router.delete("/{hardware_id}")
async def delete_hardware(hardware_id: int, db: DbDep, _: AdminDep):
    item = await db.get(HardwareItem, hardware_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Hardware not found")
    item.is_active = False
    await db.commit()
    return {"status": "deleted"}


@router.post("/{hardware_id}/restore")
async def restore_hardware(hardware_id: int, db: DbDep, _: AdminDep):
    item = await db.get(HardwareItem, hardware_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Hardware not found")
    item.is_active = True
    await db.commit()
    return {"status": "restored"}


@router.post("/{hardware_id}/crawl")
async def crawl_hardware(hardware_id: int, background_tasks: BackgroundTasks, db: DbDep, _: AdminDep):
    item = await db.get(HardwareItem, hardware_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Hardware not found")
    background_tasks.add_task(_cold_start, item.id)
    return {"status": "started", "hardware_id": item.id}


@router.get("/{hardware_id}", response_model=HardwareDetail)
async def get_hardware(hardware_id: int, db: DbDep):
    """返回单个硬件详情 + 最新一天统计数据"""
    hw = await db.get(HardwareItem, hardware_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Hardware not found")

    # 详情页保留该商品自己「最近一次有数据」的统计（即便不是本轮）
    stats_result = await db.execute(
        select(DailyStats)
        .where(DailyStats.hardware_id == hardware_id)
        .order_by(desc(DailyStats.stat_date))
        .limit(1)
    )
    latest = stats_result.scalar_one_or_none()

    # 全站锚点日：若该商品最新统计早于锚点日，说明本轮没采到，属于旧数据
    anchor_date = await _global_latest_stat_date(db)
    is_stale = bool(latest and anchor_date and latest.stat_date < anchor_date)

    return HardwareDetail(
        id=hw.id,
        name=hw.name,
        category=hw.category,
        latest_stats=DailyStatsOut.model_validate(latest) if latest else None,
        latest_run_date=anchor_date,
        stats_is_stale=is_stale,
    )


@router.get("/{hardware_id}/trend", response_model=TrendResponse)
async def get_trend(hardware_id: int, days: int = 30, db: DbDep = None):
    """返回指定天数的价格走势（days=7|30|90）"""
    if days not in (7, 30, 90):
        raise HTTPException(status_code=400, detail="days 参数只支持 7、30、90")

    hw = await db.get(HardwareItem, hardware_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Hardware not found")

    since = today_cst() - timedelta(days=days)
    result = await db.execute(
        select(DailyStats)
        .where(
            and_(
                DailyStats.hardware_id == hardware_id,
                DailyStats.stat_date >= since,
            )
        )
        .order_by(DailyStats.stat_date)
    )
    stats_list = result.scalars().all()

    trend = [
        TrendPoint(
            date=s.stat_date,
            median_price=s.median_price,
            avg_price=s.avg_price,
            min_price=s.min_price,
            max_price=s.max_price,
            sample_count=s.sample_count,
            price_level=s.price_level,
        )
        for s in stats_list
    ]

    return TrendResponse(hardware_id=hardware_id, hardware_name=hw.name, days=days, trend=trend)


@router.get("/{hardware_id}/samples", response_model=list[HardwareSampleOut])
async def get_hardware_samples(hardware_id: int, limit: int = 8, db: DbDep = None):
    """返回某个订阅对象最新有效样本，用于详情页精选相关商品。"""
    hw = await db.get(HardwareItem, hardware_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Hardware not found")

    limit = max(1, min(limit, 24))
    latest_date = (
        await db.execute(
            select(PriceSnapshot.snapshot_date)
            .where(
                and_(
                    PriceSnapshot.hardware_id == hardware_id,
                    PriceSnapshot.is_valid == True,
                )
            )
            .order_by(desc(PriceSnapshot.snapshot_date))
            .limit(1)
        )
    ).scalar_one_or_none()

    if latest_date is None:
        return []

    latest_stats = (
        await db.execute(
            select(DailyStats)
            .where(
                and_(
                    DailyStats.hardware_id == hardware_id,
                    DailyStats.stat_date == latest_date,
                )
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    baseline = latest_stats.median_price if latest_stats else None
    price_filters = []
    if baseline and baseline > 0:
        price_filters = [
            PriceSnapshot.price >= baseline * 0.45,
            PriceSnapshot.price <= baseline * 1.35,
        ]

    result = await db.execute(
        select(PriceSnapshot)
        .where(
            and_(
                PriceSnapshot.hardware_id == hardware_id,
                PriceSnapshot.snapshot_date == latest_date,
                PriceSnapshot.is_valid == True,
                *price_filters,
            )
        )
        .order_by(PriceSnapshot.price.asc(), desc(PriceSnapshot.crawled_at))
        .limit(limit)
    )

    return [
        HardwareSampleOut(
            id=item.id,
            price=item.price,
            title=item.title,
            item_url=item.item_url,
            area=item.area,
            seller=item.seller,
            image_url=item.image_url,
            publish_time=item.publish_time.isoformat() if item.publish_time else None,
            snapshot_date=item.snapshot_date,
        )
        for item in result.scalars().all()
    ]


def _hw_crawl_thread(hw_id: int, run_id: int) -> None:
    """在独立线程 + 独立 asyncio loop + 独立引擎中执行单硬件采集流水线"""
    import logging
    from app.core.config import settings as _settings
    from app.services.crawler_service import run_single_hw_tracked

    logger = logging.getLogger(__name__)

    async def _run():
        # 独立线程必须使用独立引擎——asyncpg 连接不能跨事件循环
        _engine = create_async_engine(_settings.database_url, echo=False)
        _Session = async_sessionmaker(_engine, expire_on_commit=False)
        try:
            async with _Session() as db:
                hw = await db.get(HardwareItem, hw_id)
                if hw is None:
                    logger.warning("单硬件采集：hw_id=%d 不存在", hw_id)
                    return
                await run_single_hw_tracked(db, hw, existing_run_id=run_id)
        finally:
            await _engine.dispose()

    try:
        asyncio.run(_run())
    except Exception:
        logger.exception("单硬件采集线程异常 hw_id=%d", hw_id)
        # 保证 CrawlRun 被标记为 failed
        from app.core.timezone import now_cst as _now

        async def _mark_failed():
            _engine2 = create_async_engine(_settings.database_url, echo=False)
            _Session2 = async_sessionmaker(_engine2, expire_on_commit=False)
            try:
                async with _Session2() as db2:
                    r = await db2.get(CrawlRun, run_id)
                    if r and r.status == "crawling":
                        r.status = "failed"
                        r.ended_at = _now()
                        await db2.commit()
            finally:
                await _engine2.dispose()

        try:
            asyncio.run(_mark_failed())
        except Exception:
            pass
    finally:
        with _hw_crawl_lock:
            _hw_crawls[hw_id] = False


@router.post("/{hardware_id}/crawl-now")
async def crawl_hardware_now(hardware_id: int, db: DbDep):
    """立即为单个硬件触发一次采集（在独立线程异步执行）"""
    hw = await db.get(HardwareItem, hardware_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Hardware not found")

    # 检查是否有全量采集任务正在运行——同一时间只允许一个采集任务
    from app.api.crawler import ACTIVE_RUN_STATUSES
    active_full_run = (
        await db.execute(
            select(CrawlRun)
            .where(
                CrawlRun.status.in_(ACTIVE_RUN_STATUSES),
                CrawlRun.ended_at.is_(None),
                CrawlRun.skipped != -1,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if active_full_run is not None:
        return {"status": "rejected", "message": "请等待当前采集完毕后再进行下一次采集"}

    # 检查是否有其他单硬件采集任务正在运行
    with _hw_crawl_lock:
        any_running = any(v for v in _hw_crawls.values())
        if any_running:
            return {"status": "rejected", "message": "请等待当前采集完毕后再进行下一次采集"}
        if _hw_crawls.get(hardware_id):
            run_id = _hw_run_ids.get(hardware_id)
            return {"status": "already_running", "run_id": run_id}
        _hw_crawls[hardware_id] = True

    # 预先建 CrawlRun 记录，获取 run_id 供前端轮询
    # skipped=-1 标记为单硬件采集，health 端点会忽略
    from app.core.timezone import now_cst
    run = CrawlRun(started_at=now_cst(), status="crawling", skipped=-1)
    db.add(run)
    await db.commit()
    _hw_run_ids[hardware_id] = run.id

    threading.Thread(
        target=_hw_crawl_thread,
        args=(hardware_id, run.id),
        daemon=True,
    ).start()

    return {"status": "started", "run_id": run.id}


@router.get("/{hardware_id}/crawl-progress")
async def hw_crawl_progress(hardware_id: int, db: DbDep):
    """查询单硬件采集进度"""
    from app.services.health_service import _run_progress

    run_id = _hw_run_ids.get(hardware_id)
    running = bool(_hw_crawls.get(hardware_id))

    if run_id is None:
        return {"running": False, "run_id": None, "progress": None}

    run = await db.get(CrawlRun, run_id)
    if run is None:
        return {"running": running, "run_id": run_id, "progress": None}

    progress = _run_progress(run, active_total=1)
    return {"running": running, "run_id": run_id, "progress": progress}


@router.post("/reset", dependencies=[Depends(require_admin)])
async def reset_hardware_data(db: DbDep):
    """清空所有业务数据并按硬件池重建 hardware_items。需要管理员 Token。"""
    await db.execute(delete(DailyStats))
    await db.execute(delete(PriceSnapshot))
    await db.execute(delete(CrawlRun))
    await db.execute(delete(HardwareItem))

    for item in HARDWARE_POOL:
        db.add(HardwareItem(
            name=item["name"],
            category=item["category"],
            search_keywords=item.get("search_keywords") or [item["name"]],
            validation_rule=item.get("validation_rule"),
        ))

    await db.commit()
    return {"status": "ok", "inserted": len(HARDWARE_POOL)}
