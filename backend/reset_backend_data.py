"""
Reset backend business data and rebuild hardware_items from HARDWARE_POOL.

Behavior:
1. Delete all daily_stats
2. Delete all price_snapshots
3. Delete all hardware_items
4. Reinsert hardware_items from app.core.hardware_pool.HARDWARE_POOL

This script intentionally does not touch Alembic metadata tables.
"""

import asyncio

from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.core.hardware_pool import HARDWARE_POOL
from app.models import DailyStats, HardwareItem, PriceSnapshot


async def main() -> None:
    async with AsyncSessionLocal() as session:
        deleted_stats = await session.execute(delete(DailyStats))
        deleted_snapshots = await session.execute(delete(PriceSnapshot))
        deleted_hardware = await session.execute(delete(HardwareItem))

        for item in HARDWARE_POOL:
            session.add(
                HardwareItem(
                    name=item["name"],
                    category=item["category"],
                )
            )

        await session.commit()

    print("Backend data reset finished.")
    print(f"Deleted daily_stats: {deleted_stats.rowcount or 0}")
    print(f"Deleted price_snapshots: {deleted_snapshots.rowcount or 0}")
    print(f"Deleted hardware_items: {deleted_hardware.rowcount or 0}")
    print(f"Inserted hardware_items from HARDWARE_POOL: {len(HARDWARE_POOL)}")


if __name__ == "__main__":
    asyncio.run(main())
