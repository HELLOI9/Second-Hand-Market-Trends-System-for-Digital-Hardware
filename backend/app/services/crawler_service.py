"""
爬取任务服务：遍历所有硬件，依次爬取并聚合统计
"""

import asyncio
import json
import logging
from datetime import date, datetime
from typing import Callable

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crawler import crawl_keyword
from app.models import CrawlRun, DailyStats, HardwareItem, PriceSnapshot
from app.services.alerts_service import evaluate_alerts_after_crawl
from app.services.hardware_pool_service import primary_keyword
from app.services.llm_validator import validate_snapshot_rows_sequential
from app.services.stats import save_snapshots, compute_daily_stats

logger = logging.getLogger(__name__)
VALIDATION_LIMIT_PER_HARDWARE = 25


async def run_full_crawl(
    db: AsyncSession,
    force: bool = False,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    """
    遍历所有硬件，先完成全量爬取，再逐条 LLM 校验，最后统一聚合统计。
    返回执行摘要 dict。
    """
    today = date.today()
    run = CrawlRun(started_at=datetime.utcnow(), status="running")
    db.add(run)
    await db.commit()

    result = await db.execute(select(HardwareItem).where(HardwareItem.is_active == True))
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

    async def save_run_progress(status: str) -> None:
        run.status = status
        run.success = summary["success"]
        run.failed = summary["failed"]
        run.skipped = summary["skipped"]
        run.details_json = json.dumps(summary["details"], ensure_ascii=False)
        await db.commit()

    async def interrupt_run() -> dict:
        run.status = "interrupted"
        run.ended_at = datetime.utcnow()
        await save_run_progress("interrupted")
        logger.info("采集任务已暂停：成功 %d，失败 %d，跳过 %d", summary["success"], summary["failed"], summary["skipped"])
        return summary

    def stop_requested() -> bool:
        return should_stop is not None and should_stop()

    # Phase 1: crawl everything first
    await save_run_progress("crawling")
    for hw in hardware_list:
        if stop_requested():
            return await interrupt_run()

        existing = await db.execute(
            select(func.count()).select_from(PriceSnapshot).where(
                PriceSnapshot.hardware_id == hw.id,
                PriceSnapshot.snapshot_date == today,
            )
        )
        existing_count = existing.scalar() or 0
        if existing_count > 0 and not force:
            logger.info("Skipping %s — already crawled today", hw.name)
            summary["skipped"] += 1
            detail = {"hardware_id": hw.id, "hardware": hw.name, "status": "skipped"}
            summary["details"].append(detail)
            details_by_hardware_id[hw.id] = detail
            await save_run_progress("crawling")
            continue
        if existing_count > 0 and force:
            await db.execute(
                delete(PriceSnapshot).where(
                    PriceSnapshot.hardware_id == hw.id,
                    PriceSnapshot.snapshot_date == today,
                )
            )
            await db.execute(
                delete(DailyStats).where(
                    DailyStats.hardware_id == hw.id,
                    DailyStats.stat_date == today,
                )
            )
            await db.commit()
            logger.info("强制重新采集：已清理 %s 今日旧数据", hw.name)

        try:
            search_keywords = primary_keyword(hw)
            logger.info("开始爬取：%s (%s)", hw.name, search_keywords)
            raw_items = await crawl_keyword(search_keywords)
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
            await save_run_progress("crawling")
        except Exception as e:
            await db.rollback()
            logger.error("爬取 %s 失败：%s", hw.name, e)
            summary["failed"] += 1
            detail = {"hardware_id": hw.id, "hardware": hw.name, "status": "crawl_failed", "error": str(e)}
            summary["details"].append(detail)
            details_by_hardware_id[hw.id] = detail
            await save_run_progress("crawling")

        if hw != hardware_list[-1]:
            if stop_requested():
                return await interrupt_run()
            logger.info("Waiting 2s before next item...")
            await asyncio.sleep(2)

    # Phase 2: validate all new snapshots one by one
    if crawled_hardware and settings.llm_validation_enabled:
        if stop_requested():
            return await interrupt_run()
        await save_run_progress("validating")
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
        validation_counts: dict[int, int] = {}
        validation_rows = []
        for row in validation_result.all():
            snapshot, _ = row
            count = validation_counts.get(snapshot.hardware_id, 0)
            if count >= VALIDATION_LIMIT_PER_HARDWARE:
                snapshot.is_valid = False
                snapshot.validation_reason = "skipped by validation limit"
                continue
            validation_counts[snapshot.hardware_id] = count + 1
            validation_rows.append(row)
        await db.commit()
        logger.info("开始逐条 LLM 校验：共 %d 条快照", len(validation_rows))
        summary["validation"] = await validate_snapshot_rows_sequential(
            db,
            validation_rows,
            commit_each=True,
            should_stop=stop_requested,
        )
        if stop_requested():
            return await interrupt_run()
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
        await save_run_progress("validating")
    elif crawled_hardware:
        for hw in crawled_hardware:
            details_by_hardware_id[hw.id].update({
                "validated": 0,
                "valid": details_by_hardware_id[hw.id].get("saved", 0),
                "invalid": 0,
                "validation_failed": 0,
                "validation": "disabled",
            })
        summary["validation"] = {
            "validated": 0,
            "valid": sum(detail.get("saved", 0) for detail in details_by_hardware_id.values()),
            "invalid": 0,
            "failed": 0,
            "disabled": True,
        }
        await save_run_progress("crawling")

    # Phase 3: aggregate after all validation is complete
    if stop_requested():
        return await interrupt_run()
    await save_run_progress("aggregating")
    for hw in crawled_hardware:
        if stop_requested():
            return await interrupt_run()
        try:
            stats = await compute_daily_stats(db, hw, today)
            fired = await evaluate_alerts_after_crawl(db, hw, stats)
            await db.commit()
            detail = details_by_hardware_id[hw.id]
            detail["median_price"] = stats.median_price if stats else None
            detail["alerts_fired"] = fired
            detail["status"] = "aggregated" if stats else "no_valid_samples"
            if stats is None:
                summary["aggregation"]["empty"] += 1
            else:
                summary["aggregation"]["updated"] += 1
            await save_run_progress("aggregating")
        except Exception as e:
            await db.rollback()
            logger.error("聚合 %s 失败：%s", hw.name, e)
            detail = details_by_hardware_id[hw.id]
            detail["status"] = "aggregation_failed"
            detail["aggregation_error"] = str(e)
            await save_run_progress("aggregating")

    logger.info(
        "本次爬取完成：共 %d 个，成功 %d，失败 %d，跳过 %d；校验 %d 条；聚合更新 %d 个",
        summary["total"],
        summary["success"],
        summary["failed"],
        summary["skipped"],
        summary["validation"]["validated"],
        summary["aggregation"]["updated"],
    )
    run.status = "success" if summary["failed"] == 0 else "partial"
    run.ended_at = datetime.utcnow()
    await save_run_progress(run.status)
    return summary
