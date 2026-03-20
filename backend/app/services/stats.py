"""
数据清洗与统计聚合服务

流程：
1. 清洗：过滤价格为 0 的记录，去除标题与硬件名明显不相关的记录
2. 去重：同一天同一硬件，相同价格+标题 hash 去重
3. 异常值过滤：使用 IQR 方法过滤离群价格
4. 统计：计算中位数、均值、最高/最低价、样本数
5. 行情判断：低位 / 正常 / 偏高（基于 30 天历史中位数分布）
"""

import logging
from datetime import date, datetime, timedelta
from typing import Sequence

import numpy as np
import pandas as pd
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler import RawItem
from app.models import HardwareItem, PriceSnapshot, DailyStats
from app.models.price import PriceLevel

logger = logging.getLogger(__name__)

# IQR 过滤倍数（典型值 1.5，宽松用 2.0 因为二手价格波动更大）
IQR_MULTIPLIER = 2.0

# 行情判断阈值（相对 30 天中位数的偏离比例）
LEVEL_LOW_THRESHOLD = -0.10     # 低于 10% => 低位
LEVEL_HIGH_THRESHOLD = 0.10     # 高于 10% => 偏高


def _filter_outliers(prices: list[float]) -> list[float]:
    """使用 IQR 方法过滤离群价格"""
    if len(prices) < 4:
        return prices
    arr = np.array(prices)
    q1, q3 = np.percentile(arr, 25), np.percentile(arr, 75)
    iqr = q3 - q1
    lower = q1 - IQR_MULTIPLIER * iqr
    upper = q3 + IQR_MULTIPLIER * iqr
    return [p for p in prices if lower <= p <= upper]


def _compute_price_level(today_median: float, historical_medians: list[float]) -> PriceLevel:
    """
    根据今日中位价与历史中位价的分布，判断行情高低。
    historical_medians：最近 30 天（不含今日）的每日中位价列表。
    """
    if not historical_medians or len(historical_medians) < 5:
        return PriceLevel.normal

    ref_median = float(np.median(historical_medians))
    if ref_median == 0:
        return PriceLevel.normal

    change_ratio = (today_median - ref_median) / ref_median
    if change_ratio <= LEVEL_LOW_THRESHOLD:
        return PriceLevel.low
    if change_ratio >= LEVEL_HIGH_THRESHOLD:
        return PriceLevel.high
    return PriceLevel.normal


async def save_snapshots(
    db: AsyncSession,
    hardware: HardwareItem,
    raw_items: list[RawItem],
    snapshot_date: date,
) -> int:
    """
    清洗 raw_items 并写入 price_snapshots 表，返回实际入库数量。
    同一天同一硬件，(title, price) 完全相同的记录视为重复，不重复写入。
    """
    if not raw_items:
        return 0

    # 过滤价格为 0 或极低的记录（比如 1 元明显是占位价）
    valid = [r for r in raw_items if r.price >= 10]

    # IQR 过滤
    prices = [r.price for r in valid]
    filtered_prices = set(_filter_outliers(prices))
    valid = [r for r in valid if r.price in filtered_prices]

    # 查询当天已有记录，避免重复插入
    existing = await db.execute(
        select(PriceSnapshot.title, PriceSnapshot.price).where(
            and_(
                PriceSnapshot.hardware_id == hardware.id,
                PriceSnapshot.snapshot_date == snapshot_date,
            )
        )
    )
    existing_set = {(row.title, row.price) for row in existing}

    count = 0
    for item in valid:
        key = (item.title, item.price)
        if key in existing_set:
            continue
        db.add(PriceSnapshot(
            hardware_id=hardware.id,
            price=item.price,
            title=item.title,
            item_url=item.item_url,
            snapshot_date=snapshot_date,
            area=item.area,
            seller=item.seller,
            image_url=item.image_url,
            publish_time=item.publish_time,
            crawled_at=datetime.utcnow(),
        ))
        existing_set.add(key)
        count += 1

    await db.flush()
    logger.info("硬件 [%s] 入库 %d 条价格记录", hardware.name, count)
    return count


async def compute_daily_stats(
    db: AsyncSession,
    hardware: HardwareItem,
    stat_date: date,
) -> DailyStats | None:
    """
    对指定硬件在 stat_date 当天的 price_snapshots 做统计聚合，写入 daily_stats。
    若当天无数据则返回 None。
    """
    # 拉取当天价格样本
    result = await db.execute(
        select(PriceSnapshot.price).where(
            and_(
                PriceSnapshot.hardware_id == hardware.id,
                PriceSnapshot.snapshot_date == stat_date,
                PriceSnapshot.is_valid == True,
            )
        )
    )
    prices = [row.price for row in result]

    if not prices:
        existing = await db.execute(
            select(DailyStats).where(
                and_(
                    DailyStats.hardware_id == hardware.id,
                    DailyStats.stat_date == stat_date,
                )
            )
        )
        stale_stats = existing.scalar_one_or_none()
        if stale_stats is not None:
            await db.delete(stale_stats)
            await db.flush()
            logger.info("硬件 [%s] %s 无有效样本，已删除旧聚合结果", hardware.name, stat_date)
        else:
            logger.warning("硬件 [%s] %s 无价格数据，跳过聚合", hardware.name, stat_date)
        return None

    # 拉取最近 30 天历史中位价，用于行情判断
    history_start = stat_date - timedelta(days=30)
    hist_result = await db.execute(
        select(DailyStats.median_price).where(
            and_(
                DailyStats.hardware_id == hardware.id,
                DailyStats.stat_date >= history_start,
                DailyStats.stat_date < stat_date,
            )
        )
    )
    historical_medians = [row.median_price for row in hist_result]

    # 计算统计量
    arr = np.array(prices)
    median_price = float(np.median(arr))
    avg_price = float(np.mean(arr))
    min_price = float(np.min(arr))
    max_price = float(np.max(arr))
    sample_count = len(prices)
    price_level = _compute_price_level(median_price, historical_medians)

    # Upsert daily_stats（同一天同一硬件只保留一条）
    existing = await db.execute(
        select(DailyStats).where(
            and_(
                DailyStats.hardware_id == hardware.id,
                DailyStats.stat_date == stat_date,
            )
        )
    )
    stats = existing.scalar_one_or_none()

    if stats is None:
        stats = DailyStats(hardware_id=hardware.id, stat_date=stat_date)
        db.add(stats)

    stats.median_price = median_price
    stats.avg_price = avg_price
    stats.min_price = min_price
    stats.max_price = max_price
    stats.sample_count = sample_count
    stats.price_level = price_level

    await db.flush()
    logger.info(
        "硬件 [%s] %s 聚合完成：中位价 %.0f，样本 %d，行情 %s",
        hardware.name, stat_date, median_price, sample_count, price_level.value,
    )
    return stats
