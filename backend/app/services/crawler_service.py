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
from app.services.llm_validator import validate_snapshot_rows_sequential
from app.services.stats import save_snapshots, compute_daily_stats

logger = logging.getLogger(__name__)


async def run_full_crawl(db: AsyncSession) -> dict:
    """
    遍历所有硬件，先完成全量爬取，再逐条 LLM 校验，最后统一聚合统计。
    返回执行摘要 dict。
    """
    today = date.today()
    result = await db.execute(select(HardwareItem))
    hardware_list = result.scalars().all()

    summary = {
        "date": str(today),
        "total": len(hardware_list),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "details": [],
        "validation": {"validated": 0, "valid": 0, "invalid": 0, "failed": 0},
        "aggregation": {"updated": 0, "empty": 0},
    }
    details_by_hardware_id: dict[int, dict] = {}
    crawled_hardware: list[HardwareItem] = []

    # Phase 1: crawl everything first
    for hw in hardware_list:
        existing = await db.execute(
            select(func.count()).select_from(PriceSnapshot).where(
                PriceSnapshot.hardware_id == hw.id,
                PriceSnapshot.snapshot_date == today,
            )
        )
        if existing.scalar() > 0:
            logger.info("Skipping %s — already crawled today", hw.name)
            summary["skipped"] += 1
            detail = {"hardware_id": hw.id, "hardware": hw.name, "status": "skipped"}
            summary["details"].append(detail)
            details_by_hardware_id[hw.id] = detail
            continue

        try:
            logger.info("开始爬取：%s (%s)", hw.name, hw.search_keywords)
            raw_items = await crawl_keyword(hw.search_keywords)
            saved = await save_snapshots(db, hw, raw_items, today)
            await db.commit()
            summary["success"] += 1
            crawled_hardware.append(hw)
            detail = {
                "hardware_id": hw.id,
                "hardware": hw.name,
                "raw": len(raw_items),
                "saved": saved,
                "status": "crawled",
            }
            summary["details"].append(detail)
            details_by_hardware_id[hw.id] = detail
        except Exception as e:
            await db.rollback()
            logger.error("爬取 %s 失败：%s", hw.name, e)
            summary["failed"] += 1
            detail = {"hardware_id": hw.id, "hardware": hw.name, "status": "crawl_failed", "error": str(e)}
            summary["details"].append(detail)
            details_by_hardware_id[hw.id] = detail

        if hw != hardware_list[-1]:
            logger.info("Waiting 30s before next item...")
            await asyncio.sleep(30)

    # Phase 2: validate all new snapshots one by one
    if crawled_hardware:
        hardware_ids = [hw.id for hw in crawled_hardware]
        validation_result = await db.execute(
            select(PriceSnapshot, HardwareItem.name)
            .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
            .where(
                PriceSnapshot.snapshot_date == today,
                PriceSnapshot.hardware_id.in_(hardware_ids),
                PriceSnapshot.is_valid.is_(None),
            )
            .order_by(PriceSnapshot.hardware_id, PriceSnapshot.id)
        )
        validation_rows = validation_result.all()
        logger.info("开始逐条 LLM 校验：共 %d 条快照", len(validation_rows))
        summary["validation"] = await validate_snapshot_rows_sequential(
            db,
            validation_rows,
            commit_each=True,
        )
        validation_by_hardware: dict[int, dict[str, int]] = {
            hw.id: {"validated": 0, "valid": 0, "invalid": 0, "validation_failed": 0}
            for hw in crawled_hardware
        }
        for snapshot, _ in validation_rows:
            counts = validation_by_hardware[snapshot.hardware_id]
            if snapshot.is_valid is None:
                counts["validation_failed"] += 1
                continue
            counts["validated"] += 1
            if snapshot.is_valid:
                counts["valid"] += 1
            else:
                counts["invalid"] += 1
        for hw in crawled_hardware:
            details_by_hardware_id[hw.id].update(validation_by_hardware[hw.id])

    # Phase 3: aggregate after all validation is complete
    for hw in crawled_hardware:
        try:
            stats = await compute_daily_stats(db, hw, today)
            await db.commit()
            detail = details_by_hardware_id[hw.id]
            detail["median_price"] = stats.median_price if stats else None
            detail["status"] = "aggregated" if stats else "no_valid_samples"
            if stats is None:
                summary["aggregation"]["empty"] += 1
            else:
                summary["aggregation"]["updated"] += 1
        except Exception as e:
            await db.rollback()
            logger.error("聚合 %s 失败：%s", hw.name, e)
            detail = details_by_hardware_id[hw.id]
            detail["status"] = "aggregation_failed"
            detail["aggregation_error"] = str(e)

    logger.info(
        "本次爬取完成：共 %d 个，成功 %d，失败 %d，跳过 %d；校验 %d 条；聚合更新 %d 个",
        summary["total"],
        summary["success"],
        summary["failed"],
        summary["skipped"],
        summary["validation"]["validated"],
        summary["aggregation"]["updated"],
    )
    return summary
