from app.core.timezone import today_cst

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler import crawl_keyword
from app.models import DailyStats, HardwareItem, PriceSnapshot
from app.services.llm_validator import validate_snapshot_rows_sequential
from app.services.stats import compute_daily_stats, save_snapshots


def primary_keyword(hardware: HardwareItem) -> str:
    return hardware.search_keywords[0] if hardware.search_keywords else hardware.name


async def run_single_hardware_crawl(
    db: AsyncSession,
    hardware: HardwareItem,
    *,
    max_pages: int = 3,
    validation_limit: int = 25,
    replace_today: bool = True,
) -> dict:
    today = today_cst()
    if replace_today:
        await db.execute(
            delete(DailyStats).where(
                DailyStats.hardware_id == hardware.id,
                DailyStats.stat_date == today,
            )
        )
        await db.execute(
            delete(PriceSnapshot).where(
                PriceSnapshot.hardware_id == hardware.id,
                PriceSnapshot.snapshot_date == today,
            )
        )
        await db.commit()

    raw_items = await crawl_keyword(primary_keyword(hardware), max_pages=max_pages)
    saved = await save_snapshots(db, hardware, raw_items, today)
    await db.commit()

    validation_rows = (
        await db.execute(
            select(PriceSnapshot, HardwareItem.name, HardwareItem.validation_rule)
            .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
            .where(
                PriceSnapshot.hardware_id == hardware.id,
                PriceSnapshot.snapshot_date == today,
                PriceSnapshot.is_valid.is_(None),
            )
            .order_by(PriceSnapshot.id)
            .limit(validation_limit)
        )
    ).all()
    skipped = (
        await db.execute(
            select(PriceSnapshot)
            .where(
                PriceSnapshot.hardware_id == hardware.id,
                PriceSnapshot.snapshot_date == today,
                PriceSnapshot.is_valid.is_(None),
            )
            .order_by(PriceSnapshot.id)
            .offset(validation_limit)
        )
    ).scalars().all()
    for row in skipped:
        row.is_valid = False
        row.validation_reason = "skipped by validation limit"
    await db.commit()

    validation = await validate_snapshot_rows_sequential(db, validation_rows, commit_each=True)
    stats = await compute_daily_stats(db, hardware, today)
    await db.commit()

    return {
        "hardware_id": hardware.id,
        "hardware": hardware.name,
        "raw": len(raw_items),
        "saved": saved,
        "validation": validation,
        "median_price": stats.median_price if stats else None,
        "sample_count": stats.sample_count if stats else 0,
    }
