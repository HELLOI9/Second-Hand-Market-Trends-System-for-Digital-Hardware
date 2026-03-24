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
import re
from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler import RawItem
from app.models import HardwareItem, PriceSnapshot, DailyStats
from app.models.price import PriceLevel

logger = logging.getLogger(__name__)

# 对数价格空间中的密度聚类参数
DBSCAN_EPS = 0.22
DBSCAN_MIN_SAMPLES = 4

# MAD fallback 阈值
MAD_Z_THRESHOLD = 3.5

# 聚类保底下限：低于主簇中位价一定比例的点直接剔除
RELATIVE_FLOOR_RATIO = 0.45

# 行情判断阈值（相对 30 天中位数的偏离比例）
LEVEL_LOW_THRESHOLD = -0.10     # 低于 10% => 低位
LEVEL_HIGH_THRESHOLD = 0.10     # 高于 10% => 偏高

GLOBAL_BLOCK_TOKENS = (
    "笔记本",
    "游戏本",
    "回收",
    "出租",
    "租赁",
)

CATEGORY_BLOCK_TOKENS = {
    "cpu": (
        "板u",
        "板U",
        "主板套装",
        "套板",
        "主板",
    ),
    "gpu": (
        "笔记本显卡",
        "主机整机",
    ),
    "memory": (
        "笔记本内存",
    ),
    "ssd": (
        "硬盘盒",
        "转接卡",
        "转接板",
        "扩展卡",
        "转接器",
        "扩展坞",
        "2230转2280",
        "2280转2230",
        "盒子",
    ),
}


def _dbscan_filter_log_prices(prices: list[float]) -> tuple[list[float], str]:
    """
    用一维 log(price) 空间上的 DBSCAN 风格聚类保留主簇。
    返回 (保留价格列表, 说明)。
    """
    if len(prices) < DBSCAN_MIN_SAMPLES:
        return prices, "not_enough_samples_for_dbscan"

    log_prices = np.log(np.array(prices, dtype=float))
    n = len(log_prices)

    neighbors: list[list[int]] = []
    for i in range(n):
        local = [j for j in range(n) if abs(log_prices[i] - log_prices[j]) <= DBSCAN_EPS]
        neighbors.append(local)

    core_points = {i for i, nb in enumerate(neighbors) if len(nb) >= DBSCAN_MIN_SAMPLES}
    if not core_points:
        return prices, "no_core_cluster_found"

    visited: set[int] = set()
    clusters: list[list[int]] = []

    for point in sorted(core_points):
        if point in visited:
            continue

        cluster: set[int] = set()
        stack = [point]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            cluster.add(current)

            if current in core_points:
                for nb in neighbors[current]:
                    if nb not in visited:
                        stack.append(nb)
                    cluster.add(nb)

        if cluster:
            clusters.append(sorted(cluster))

    if not clusters:
        return prices, "empty_cluster_result"

    median_log = float(np.median(log_prices))

    def _cluster_score(indices: list[int]) -> tuple[int, float]:
        cluster_logs = [float(log_prices[i]) for i in indices]
        cluster_center = float(np.median(cluster_logs))
        return (len(indices), -abs(cluster_center - median_log))

    best_cluster = max(clusters, key=_cluster_score)
    kept_prices = [prices[i] for i in best_cluster]

    if not kept_prices:
        return prices, "best_cluster_empty"

    cluster_median = float(np.median(kept_prices))
    kept_prices = [p for p in kept_prices if p >= cluster_median * RELATIVE_FLOOR_RATIO]
    if not kept_prices:
        return prices, "cluster_floor_removed_all"

    return kept_prices, f"dbscan_cluster_size={len(best_cluster)}"


def _mad_filter_log_prices(prices: list[float]) -> tuple[list[float], str]:
    """用 log(price) + MAD 做稳健离群过滤。"""
    if len(prices) < 4:
        return prices, "not_enough_samples_for_mad"

    log_prices = np.log(np.array(prices, dtype=float))
    median_log = float(np.median(log_prices))
    abs_dev = np.abs(log_prices - median_log)
    mad = float(np.median(abs_dev))

    if mad == 0:
        return prices, "mad_zero"

    robust_z = 0.6745 * abs_dev / mad
    kept_prices = [price for price, z in zip(prices, robust_z) if z <= MAD_Z_THRESHOLD]
    if not kept_prices:
        return prices, "mad_removed_all"

    cluster_median = float(np.median(kept_prices))
    kept_prices = [p for p in kept_prices if p >= cluster_median * RELATIVE_FLOOR_RATIO]
    if not kept_prices:
        return prices, "mad_floor_removed_all"

    return kept_prices, "mad_filter"


def _filter_outliers(prices: list[float]) -> tuple[list[float], str]:
    """
    更强的离群值过滤：
    1. 优先使用 log(price) + DBSCAN 风格密度聚类
    2. 如果 DBSCAN 没形成有效主簇，则回退到 MAD
    """
    if len(prices) < 4:
        return prices, "not_enough_samples"

    dbscan_prices, dbscan_reason = _dbscan_filter_log_prices(prices)
    if dbscan_prices != prices or dbscan_reason.startswith("dbscan_cluster_size="):
        return dbscan_prices, dbscan_reason

    return _mad_filter_log_prices(prices)


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


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", "", title).lower()


def _matches_ssd_capacity(hardware_name: str, normalized_title: str) -> bool:
    capacity_match = re.search(r"(\d+(?:\.\d+)?)TB", hardware_name, re.IGNORECASE)
    if not capacity_match:
        return True

    tb_value = capacity_match.group(1)
    variants = {
        f"{tb_value}tb",
        f"{tb_value}t",
    }
    if tb_value.endswith(".0"):
        variants.add(f"{tb_value[:-2]}tb")
        variants.add(f"{tb_value[:-2]}t")

    return any(variant in normalized_title for variant in variants)


def _passes_rule_filter(hardware: HardwareItem, item: RawItem) -> bool:
    normalized_title = _normalize_title(item.title)

    if any(token in normalized_title for token in GLOBAL_BLOCK_TOKENS):
        return False

    category_tokens = CATEGORY_BLOCK_TOKENS.get(hardware.category, ())
    if any(token.lower() in normalized_title for token in category_tokens):
        return False

    if hardware.category == "ssd" and not _matches_ssd_capacity(hardware.name, normalized_title):
        return False

    return True


async def _delete_stale_daily_stats(
    db: AsyncSession,
    hardware: HardwareItem,
    stat_date: date,
) -> None:
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

    # 仅做轻量规则过滤；离群值过滤放到 LLM 之后
    valid = [r for r in raw_items if r.price >= 10]
    valid = [r for r in valid if _passes_rule_filter(hardware, r)]

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
        await _delete_stale_daily_stats(db, hardware, stat_date)
        logger.warning("硬件 [%s] %s 无有效样本，跳过聚合", hardware.name, stat_date)
        return None

    filtered_prices, filter_reason = _filter_outliers(prices)
    if len(filtered_prices) != len(prices):
        logger.info(
            "硬件 [%s] %s 离群值过滤：原始 %d 条，有效 %d 条，方式 %s，剔除价格 %s",
            hardware.name,
            stat_date,
            len(prices),
            len(filtered_prices),
            filter_reason,
            sorted(p for p in prices if p not in set(filtered_prices)),
        )
    prices = filtered_prices

    if not prices:
        await _delete_stale_daily_stats(db, hardware, stat_date)
        logger.warning("硬件 [%s] %s 离群值过滤后无有效样本，跳过聚合", hardware.name, stat_date)
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
