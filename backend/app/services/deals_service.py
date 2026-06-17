import statistics
from datetime import timedelta

from app.core.timezone import today_cst

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyStats, HardwareItem, PriceSnapshot

DEAL_THRESHOLD = 0.15  # 低于基准 15% 才算捡漏


async def today_deals(db: AsyncSession, limit: int = 20) -> list[dict]:
    today = today_cst()

    # 用 DailyStats 确定有数据的最新日期
    latest_date = (
        await db.execute(select(func.max(DailyStats.stat_date)))
    ).scalar_one_or_none()
    target_date = latest_date if latest_date is not None else today
    history_start = target_date - timedelta(days=30)

    # 批量查当天所有硬件的 daily_stats
    today_stats_rows = (
        await db.execute(
            select(DailyStats, HardwareItem)
            .join(HardwareItem, DailyStats.hardware_id == HardwareItem.id)
            .where(
                DailyStats.stat_date == target_date,
                HardwareItem.is_active == True,
            )
        )
    ).all()
    if not today_stats_rows:
        return []

    hardware_ids = [hw.id for _, hw in today_stats_rows]

    # 批量查 30 天历史（不含 target_date 自身，避免用今天和今天比）
    hist_rows = (
        await db.execute(
            select(DailyStats.hardware_id, DailyStats.median_price)
            .where(
                and_(
                    DailyStats.hardware_id.in_(hardware_ids),
                    DailyStats.stat_date >= history_start,
                    DailyStats.stat_date < target_date,
                )
            )
        )
    ).all()

    # 按 hardware_id 聚合历史中位价
    hist_map: dict[int, list[float]] = {}
    for hw_id, median in hist_rows:
        hist_map.setdefault(hw_id, []).append(float(median))

    # 找出有捡漏潜力的硬件（当天 min_price 低于历史基准 15%）
    candidate_hw_ids: dict[int, tuple[float, float]] = {}  # hw_id -> (baseline, threshold_price)
    for stats, hardware in today_stats_rows:
        medians = hist_map.get(hardware.id, [])
        if len(medians) < 3:  # 历史数据不足，基准不可信
            continue
        baseline = statistics.median(medians)
        if baseline <= 0:
            continue
        threshold = baseline * (1 - DEAL_THRESHOLD)
        if stats.min_price <= threshold:
            candidate_hw_ids[hardware.id] = (baseline, threshold)

    if not candidate_hw_ids:
        return []

    # 找出每个候选硬件在最新一轮爬取中的最低有效样本
    # 先找每个硬件当天最晚的 crawled_at（即最新一轮）
    latest_crawl_rows = (
        await db.execute(
            select(PriceSnapshot.hardware_id, func.max(PriceSnapshot.crawled_at).label("latest_ts"))
            .where(
                and_(
                    PriceSnapshot.hardware_id.in_(list(candidate_hw_ids.keys())),
                    PriceSnapshot.snapshot_date == target_date,
                    PriceSnapshot.is_valid == True,
                )
            )
            .group_by(PriceSnapshot.hardware_id)
        )
    ).all()

    if not latest_crawl_rows:
        return []

    latest_ts_map = {row.hardware_id: row.latest_ts for row in latest_crawl_rows}

    # 查最新一轮（latest_ts 前 5 分钟内）的所有有效样本
    from datetime import timedelta as _td
    best_samples: dict[int, dict] = {}  # hw_id -> best deal dict

    for hw_id, latest_ts in latest_ts_map.items():
        baseline, threshold = candidate_hw_ids[hw_id]
        batch_start = latest_ts - _td(minutes=5)

        samples = (
            await db.execute(
                select(PriceSnapshot, HardwareItem)
                .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
                .where(
                    and_(
                        PriceSnapshot.hardware_id == hw_id,
                        PriceSnapshot.snapshot_date == target_date,
                        PriceSnapshot.is_valid == True,
                        PriceSnapshot.crawled_at >= batch_start,
                        PriceSnapshot.price <= threshold,
                    )
                )
                .order_by(PriceSnapshot.price.asc())
                .limit(1)
            )
        ).first()

        if samples is None:
            continue
        snapshot, hardware = samples
        discount = 1.0 - snapshot.price / baseline
        best_samples[hw_id] = {
            "hardware_id": hardware.id,
            "hardware_name": hardware.name,
            "category": hardware.category,
            "price": snapshot.price,
            "baseline_median": baseline,
            "discount_rate": discount,
            "title": snapshot.title,
            "item_url": snapshot.item_url,
            "area": snapshot.area,
            "seller": snapshot.seller,
            "image_url": snapshot.image_url,
            "snapshot_date": snapshot.snapshot_date,
        }

    deals = sorted(best_samples.values(), key=lambda d: d["discount_rate"], reverse=True)
    return deals[:limit]
