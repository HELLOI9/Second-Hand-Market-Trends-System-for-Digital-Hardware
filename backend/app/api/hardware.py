from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import HardwareItem, DailyStats
from app.schemas.hardware import HardwareListItem, HardwareDetail, DailyStatsOut, TrendResponse, TrendPoint

router = APIRouter(prefix="/hardware", tags=["hardware"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=dict[str, list[HardwareDetail]])
async def list_hardware(db: DbDep):
    """返回所有硬件（含最新统计），按分类分组"""
    result = await db.execute(select(HardwareItem).order_by(HardwareItem.category, HardwareItem.name))
    items = result.scalars().all()

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
