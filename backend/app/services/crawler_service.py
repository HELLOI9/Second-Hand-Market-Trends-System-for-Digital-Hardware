"""
爬取任务服务：遍历所有硬件，依次爬取并聚合统计
"""

import asyncio
import logging
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler import crawl_keyword
from app.models import HardwareItem, PriceSnapshot
from app.services.stats import save_snapshots, compute_daily_stats

logger = logging.getLogger(__name__)


async def run_full_crawl(db: AsyncSession) -> dict:
    """
    遍历所有硬件，爬取闲鱼数据并聚合统计。
    返回执行摘要 dict。
    """
    today = date.today()
    result = await db.execute(select(HardwareItem))
    hardware_list = result.scalars().all()

    summary = {"date": str(today), "total": len(hardware_list), "success": 0, "failed": 0, "skipped": 0, "details": []}

    for hw in hardware_list:
        # Skip if already crawled today
        existing = await db.execute(
            select(func.count()).select_from(PriceSnapshot).where(
                PriceSnapshot.hardware_id == hw.id,
                PriceSnapshot.snapshot_date == today,
            )
        )
        if existing.scalar() > 0:
            logger.info("Skipping %s — already crawled today", hw.name)
            summary["skipped"] += 1
            summary["details"].append({"hardware": hw.name, "status": "skipped"})
            continue

        try:
            logger.info("开始爬取：%s (%s)", hw.name, hw.search_keywords)
            raw_items = await crawl_keyword(hw.search_keywords)
            saved = await save_snapshots(db, hw, raw_items, today)
            stats = await compute_daily_stats(db, hw, today)
            await db.commit()
            summary["success"] += 1
            summary["details"].append({
                "hardware": hw.name,
                "raw": len(raw_items),
                "saved": saved,
                "median_price": stats.median_price if stats else None,
            })
        except Exception as e:
            await db.rollback()
            logger.error("爬取 %s 失败：%s", hw.name, e)
            summary["failed"] += 1
            summary["details"].append({"hardware": hw.name, "error": str(e)})

        # Wait 30s between items to avoid anti-bot detection
        if hw != hardware_list[-1]:
            logger.info("Waiting 30s before next item...")
            await asyncio.sleep(30)

    logger.info(
        "本次爬取完成：共 %d 个，成功 %d，失败 %d，跳过 %d",
        summary["total"], summary["success"], summary["failed"], summary["skipped"],
    )
    return summary
