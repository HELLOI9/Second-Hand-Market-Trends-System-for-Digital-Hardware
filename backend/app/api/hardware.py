from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.database import get_db
from app.models import HardwareItem, DailyStats, PriceSnapshot
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
HARDWARE_ORDER_FALLBACK = 10_000


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

    # 批量拉取所有硬件的最新统计（子查询方式，避免 N+1）
    from sqlalchemy import func
    subq = (
        select(DailyStats.hardware_id, func.max(DailyStats.stat_date).label("max_date"))
        .group_by(DailyStats.hardware_id)
        .subquery()
    )
    stats_result = await db.execute(
        select(DailyStats).join(
            subq,
            and_(DailyStats.hardware_id == subq.c.hardware_id, DailyStats.stat_date == subq.c.max_date),
        )
    )
    latest_stats: dict[int, DailyStats] = {s.hardware_id: s for s in stats_result.scalars().all()}

    grouped: dict[str, list[HardwareDetail]] = {}
    for item in items:
        stats = latest_stats.get(item.id)
        detail = HardwareDetail(
            id=item.id,
            name=item.name,
            category=item.category,
            latest_stats=DailyStatsOut.model_validate(stats) if stats else None,
        )
        grouped.setdefault(item.category, []).append(detail)
    return grouped


@router.get("/admin", response_model=list[HardwareDetail])
async def list_hardware_admin(db: DbDep, _: AdminDep):
    from sqlalchemy import func

    result = await db.execute(select(HardwareItem).order_by(HardwareItem.category, HardwareItem.id))
    items = result.scalars().all()
    subq = (
        select(DailyStats.hardware_id, func.max(DailyStats.stat_date).label("max_date"))
        .group_by(DailyStats.hardware_id)
        .subquery()
    )
    stats_result = await db.execute(
        select(DailyStats).join(
            subq,
            and_(DailyStats.hardware_id == subq.c.hardware_id, DailyStats.stat_date == subq.c.max_date),
        )
    )
    latest_stats: dict[int, DailyStats] = {s.hardware_id: s for s in stats_result.scalars().all()}
    return [
        HardwareDetail(
            id=item.id,
            name=item.name,
            category=item.category,
            search_keywords=item.search_keywords,
            is_active=item.is_active,
            latest_stats=DailyStatsOut.model_validate(latest_stats.get(item.id)) if latest_stats.get(item.id) else None,
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
        is_active=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    if payload.cold_start:
        background_tasks.add_task(_cold_start, item.id)
    return HardwareDetail(id=item.id, name=item.name, category=item.category, search_keywords=item.search_keywords, is_active=item.is_active)


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
    return HardwareDetail(id=item.id, name=item.name, category=item.category, search_keywords=item.search_keywords, is_active=item.is_active)


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

    # 最新统计
    stats_result = await db.execute(
        select(DailyStats)
        .where(DailyStats.hardware_id == hardware_id)
        .order_by(desc(DailyStats.stat_date))
        .limit(1)
    )
    latest = stats_result.scalar_one_or_none()

    return HardwareDetail(
        id=hw.id,
        name=hw.name,
        category=hw.category,
        latest_stats=DailyStatsOut.model_validate(latest) if latest else None,
    )


@router.get("/{hardware_id}/trend", response_model=TrendResponse)
async def get_trend(hardware_id: int, days: int = 30, db: DbDep = None):
    """返回指定天数的价格走势（days=7|30|90）"""
    if days not in (7, 30, 90):
        raise HTTPException(status_code=400, detail="days 参数只支持 7、30、90")

    hw = await db.get(HardwareItem, hardware_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Hardware not found")

    since = date.today() - timedelta(days=days)
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
