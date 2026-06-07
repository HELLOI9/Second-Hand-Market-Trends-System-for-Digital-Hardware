from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyStats, HardwareItem, PriceSnapshot


async def today_deals(db: AsyncSession, limit: int = 20) -> list[dict]:
    today = date.today()
    latest_date = (await db.execute(select(func.max(PriceSnapshot.snapshot_date)))).scalar_one_or_none()
    target_date = today if latest_date == today else latest_date
    if target_date is None:
        return []

    rows = (
        await db.execute(
            select(PriceSnapshot, HardwareItem)
            .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
            .where(
                PriceSnapshot.snapshot_date == target_date,
                PriceSnapshot.is_valid == True,
            )
        )
    ).all()

    deals: list[dict] = []
    for snapshot, hardware in rows:
        start = target_date - timedelta(days=30)
        medians = (
            await db.execute(
                select(DailyStats.median_price)
                .where(
                    and_(
                        DailyStats.hardware_id == hardware.id,
                        DailyStats.stat_date >= start,
                        DailyStats.stat_date <= target_date,
                    )
                )
            )
        ).scalars().all()
        if not medians:
            continue
        ordered = sorted(medians)
        baseline = ordered[len(ordered) // 2]
        if baseline <= 0:
            continue
        discount = 1 - snapshot.price / baseline
        if snapshot.price <= baseline * 0.85:
            deals.append({
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
            })

    deals.sort(key=lambda item: item["discount_rate"], reverse=True)
    return deals[:limit]
