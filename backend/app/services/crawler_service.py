"""
爬取任务服务：遍历所有硬件，每个硬件独立完成「爬取 → LLM 校验 → 聚合」再处理下一个。
"""

import asyncio
import json
import logging
from app.core.timezone import now_cst, today_cst
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
VALIDATION_LIMIT_PER_HARDWARE = 100  # 提高到100条，覆盖更多样本


async def run_full_crawl(
    db: AsyncSession,
    force: bool = False,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    """
    遍历所有硬件，每个硬件依次完成：爬取 → LLM 校验 → 聚合统计。
    返回执行摘要 dict。
    """
    today = today_cst()
    run = CrawlRun(started_at=now_cst(), status="running")
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

    async def save_run_progress(status: str) -> None:
        run.status = status
        run.success = summary["success"]
        run.failed = summary["failed"]
        run.skipped = summary["skipped"]
        run.details_json = json.dumps(summary["details"], ensure_ascii=False)
        await db.commit()

    async def interrupt_run() -> dict:
        run.ended_at = now_cst()
        # 删除本轮写入但未完成校验的 snapshots（crawled_at >= 本次 run 启动时间）
        await db.execute(
            delete(PriceSnapshot).where(
                PriceSnapshot.crawled_at >= run.started_at,
            )
        )
        await save_run_progress("interrupted")
        logger.info("采集任务已中断，已清理本轮数据：成功 %d，失败 %d，跳过 %d", summary["success"], summary["failed"], summary["skipped"])
        return summary

    def stop_requested() -> bool:
        return should_stop is not None and should_stop()

    await save_run_progress("crawling")

    for hw in hardware_list:
        if stop_requested():
            return await interrupt_run()

        # ── 检查今日是否已采集 ────────────────────────
        existing_count = (await db.execute(
            select(func.count()).select_from(PriceSnapshot).where(
                PriceSnapshot.hardware_id == hw.id,
                PriceSnapshot.snapshot_date == today,
            )
        )).scalar() or 0

        if existing_count > 0 and not force:
            logger.info("Skipping %s — already crawled today", hw.name)
            summary["skipped"] += 1
            detail = {"hardware_id": hw.id, "hardware": hw.name, "status": "skipped"}
            summary["details"].append(detail)
            details_by_hardware_id[hw.id] = detail
            await save_run_progress("crawling")
            continue

        if existing_count > 0 and force:
            await db.execute(delete(PriceSnapshot).where(
                PriceSnapshot.hardware_id == hw.id,
                PriceSnapshot.snapshot_date == today,
            ))
            await db.execute(delete(DailyStats).where(
                DailyStats.hardware_id == hw.id,
                DailyStats.stat_date == today,
            ))
            await db.commit()
            logger.info("强制重新采集：已清理 %s 今日旧数据", hw.name)

        # ── Phase 1：爬取 ─────────────────────────────
        try:
            search_keywords = primary_keyword(hw)
            logger.info("开始爬取：%s (%s)", hw.name, search_keywords)
            raw_items = await crawl_keyword(search_keywords)
            saved = await save_snapshots(db, hw, raw_items, today)
            await db.commit()
            summary["success"] += 1
            detail: dict = {
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
                await asyncio.sleep(2)
            continue

        if stop_requested():
            return await interrupt_run()

        # ── Phase 2：LLM 校验（仅对本硬件当日快照）────
        if settings.llm_validation_enabled:
            validation_result = await db.execute(
                select(PriceSnapshot, HardwareItem.name, HardwareItem.validation_rule)
                .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
                .where(
                    PriceSnapshot.snapshot_date == today,
                    PriceSnapshot.hardware_id == hw.id,
                    PriceSnapshot.is_valid.is_(None),
                )
                .order_by(PriceSnapshot.price.desc())  # 按价格从高到低，优先验证真实商品
            )
            all_rows = validation_result.all()
            validation_rows = []
            for idx, row in enumerate(all_rows):
                snapshot = row[0]
                if idx >= VALIDATION_LIMIT_PER_HARDWARE:
                    snapshot.is_valid = False
                    snapshot.validation_reason = "skipped by validation limit"
                else:
                    validation_rows.append(row)
            await db.commit()

            detail["llm_total"] = len(validation_rows)
            detail["llm_done"] = 0
            await save_run_progress("crawling")

            _llm_counter = [0]  # mutable counter for throttling progress saves

            async def on_llm_progress(done: int, _total: int) -> None:
                detail["llm_done"] = done
                _llm_counter[0] += 1
                if _llm_counter[0] % 3 == 0:
                    await save_run_progress("crawling")

            logger.info("LLM 校验 %s：共 %d 条", hw.name, len(validation_rows))
            hw_val = await validate_snapshot_rows_sequential(
                db,
                validation_rows,
                commit_each=True,
                should_stop=stop_requested,
                on_progress=on_llm_progress,
            )
            detail["llm_done"] = hw_val["validated"] + hw_val["failed"]
            for key in ("validated", "valid", "invalid", "failed"):
                summary["validation"][key] += hw_val[key]

            detail.update({
                "validated": hw_val["validated"],
                "valid": hw_val["valid"],
                "invalid": hw_val["invalid"],
                "validation_failed": hw_val["failed"],
            })
            await save_run_progress("crawling")
        else:
            detail.update({
                "validated": 0,
                "valid": detail.get("saved", 0),
                "invalid": 0,
                "validation_failed": 0,
                "validation": "disabled",
                "llm_total": 0,
                "llm_done": 0,
            })

        if stop_requested():
            return await interrupt_run()

        # ── Phase 3：聚合 ─────────────────────────────
        try:
            stats = await compute_daily_stats(db, hw, today)
            fired = await evaluate_alerts_after_crawl(db, hw, stats)
            await db.commit()
            detail["median_price"] = stats.median_price if stats else None
            detail["alerts_fired"] = fired
            detail["status"] = "aggregated" if stats else "no_valid_samples"
            if stats is None:
                summary["aggregation"]["empty"] += 1
            else:
                summary["aggregation"]["updated"] += 1
            await save_run_progress("crawling")
        except Exception as e:
            await db.rollback()
            logger.error("聚合 %s 失败：%s", hw.name, e)
            detail["status"] = "aggregation_failed"
            detail["aggregation_error"] = str(e)
            await save_run_progress("crawling")

        if hw != hardware_list[-1]:
            if stop_requested():
                return await interrupt_run()
            logger.info("Waiting 2s before next item...")
            await asyncio.sleep(2)

    logger.info(
        "本次爬取完成：共 %d 个，成功 %d，失败 %d，跳过 %d；校验 %d 条；聚合更新 %d 个",
        summary["total"],
        summary["success"],
        summary["failed"],
        summary["skipped"],
        summary["validation"]["validated"],
        summary["aggregation"]["updated"],
    )
    run.ended_at = now_cst()
    run.status = "success" if summary["failed"] == 0 else "partial"
    await save_run_progress(run.status)
    return summary


async def run_single_hw_tracked(
    db: AsyncSession,
    hardware: HardwareItem,
    *,
    existing_run_id: int | None = None,
) -> dict:
    """
    针对单个硬件做完整采集流水线（爬取→LLM校验→聚合），
    创建独立 CrawlRun 并实时写入进度，供前端轮询。
    若传入 existing_run_id，则复用已创建的 CrawlRun 记录。
    """
    today = today_cst()
    if existing_run_id is not None:
        run = await db.get(CrawlRun, existing_run_id)
        if run is None:
            run = CrawlRun(started_at=now_cst(), status="crawling")
            db.add(run)
            await db.commit()
    else:
        run = CrawlRun(started_at=now_cst(), status="crawling")
        db.add(run)
        await db.commit()

    detail: dict = {
        "hardware_id": hardware.id,
        "hardware": hardware.name,
        "llm_total": 0,
        "llm_done": 0,
    }

    async def save_progress(status: str) -> None:
        run.status = status
        run.details_json = json.dumps([detail], ensure_ascii=False)
        await db.commit()

    await save_progress("crawling")

    # ── Phase 1: 爬取 ───────────────────────────────────────
    try:
        raw_items = await crawl_keyword(primary_keyword(hardware))
        saved = await save_snapshots(db, hardware, raw_items, today)
        await db.commit()
        detail.update({"raw": len(raw_items), "saved": saved, "status": "crawled"})
        await save_progress("crawling")
    except Exception as e:
        await db.rollback()
        logger.error("单硬件爬取 %s 失败：%s", hardware.name, e)
        detail.update({"status": "crawl_failed", "error": str(e)})
        run.ended_at = now_cst()
        await save_progress("failed")
        return {"status": "crawl_failed", "error": str(e)}

    # ── Phase 2: LLM 校验 ────────────────────────────────────
    if settings.llm_validation_enabled:
        all_rows = (
            await db.execute(
                select(PriceSnapshot, HardwareItem.name, HardwareItem.validation_rule)
                .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
                .where(
                    PriceSnapshot.snapshot_date == today,
                    PriceSnapshot.hardware_id == hardware.id,
                    PriceSnapshot.is_valid.is_(None),
                )
                .order_by(PriceSnapshot.price.desc())  # 按价格从高到低，优先验证真实商品
            )
        ).all()

        validation_rows = []
        for idx, row in enumerate(all_rows):
            snapshot = row[0]
            if idx >= VALIDATION_LIMIT_PER_HARDWARE:
                snapshot.is_valid = False
                snapshot.validation_reason = "skipped by validation limit"
            else:
                validation_rows.append(row)
        await db.commit()

        detail["llm_total"] = len(validation_rows)
        detail["llm_done"] = 0
        await save_progress("crawling")

        _counter = [0]

        async def on_llm_progress(done: int, _total: int) -> None:
            detail["llm_done"] = done
            _counter[0] += 1
            if _counter[0] % 3 == 0:
                await save_progress("crawling")

        hw_val = await validate_snapshot_rows_sequential(
            db, validation_rows, commit_each=True, on_progress=on_llm_progress
        )
        detail["llm_done"] = hw_val["validated"] + hw_val["failed"]
        detail.update({
            "validated": hw_val["validated"],
            "valid": hw_val["valid"],
            "invalid": hw_val["invalid"],
            "validation_failed": hw_val["failed"],
        })
        await save_progress("crawling")
    else:
        detail.update({
            "validated": 0, "valid": detail.get("saved", 0),
            "invalid": 0, "validation_failed": 0,
            "llm_total": 0, "llm_done": 0,
        })

    # ── Phase 3: 聚合 ────────────────────────────────────────
    try:
        stats = await compute_daily_stats(db, hardware, today)
        await db.commit()
        detail["median_price"] = stats.median_price if stats else None
        detail["status"] = "aggregated" if stats else "no_valid_samples"
    except Exception as e:
        await db.rollback()
        logger.error("单硬件聚合 %s 失败：%s", hardware.name, e)
        detail["status"] = "aggregation_failed"

    run.ended_at = now_cst()
    run.success = 1
    await save_progress("success")
    return detail
