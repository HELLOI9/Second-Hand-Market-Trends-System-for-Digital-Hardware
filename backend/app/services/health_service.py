import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_cst, today_cst
from app.models import CrawlRun, DailyStats, HardwareItem


COOKIE_FILE = Path(__file__).resolve().parents[2] / "cookies.json"


def _run_progress(
    latest_run: CrawlRun | None,
    active_total: int,
) -> dict | None:
    if latest_run is None:
        return None

    details = json.loads(latest_run.details_json or "[]")
    total = max(active_total, 1)
    phase = latest_run.status

    # ── 爬取进度 ──────────────────────────────────────────
    # 已完成全流水线（爬取+校验+聚合）的条目
    fully_done = sum(1 for d in details if d.get("status") in {"aggregated", "no_valid_samples", "aggregation_failed"})
    # 已完成爬取（含后续仍在校验/聚合中的）
    crawl_done = sum(1 for d in details if d.get("status") not in {None})

    if phase in {"success", "partial"}:
        crawl_percent = 100
    else:
        crawl_percent = round((crawl_done / total) * 100)

    current = next(
        (d.get("hardware") for d in reversed(details)
         if d.get("status") not in {"aggregated", "no_valid_samples", "aggregation_failed", "skipped"}),
        details[-1].get("hardware") if details else None,
    )

    # ── LLM 校验进度 ──────────────────────────────────────
    # llm_total/llm_done 只统计已进入 LLM 阶段的硬件，
    # 用 active_total 作全局分母才能反映整体进度
    llm_total_seen = sum(d.get("llm_total", 0) for d in details)
    llm_done_seen = sum(d.get("llm_done", 0) for d in details)
    if phase in {"success", "partial"}:
        llm_percent = 100
    elif active_total > 0:
        # 每个硬件最多 25 条，用实际 seen total 作全局分母估算
        # 但 llm_total 只含已进入 LLM 的硬件，未进入的视为 0/0
        # 进度 = 全局已完成 LLM 的硬件数 / active_total
        llm_hw_done = sum(
            1 for d in details
            if d.get("llm_total", 0) > 0 and d.get("llm_done", 0) >= d.get("llm_total", 0)
        )
        llm_hw_in_progress = sum(
            1 for d in details
            if d.get("llm_total", 0) > 0 and d.get("llm_done", 0) < d.get("llm_total", 0)
        )
        # 当前正在进行的那个硬件按其自身进度折算
        in_progress_frac = 0.0
        for d in details:
            t = d.get("llm_total", 0)
            dn = d.get("llm_done", 0)
            if t > 0 and dn < t:
                in_progress_frac = dn / t
                break
        llm_percent = round(((llm_hw_done + in_progress_frac) / active_total) * 100)
    else:
        llm_percent = 0
    llm_total = llm_total_seen
    llm_done = llm_done_seen

    # 当前正在做 LLM 校验的硬件
    llm_current_detail = next(
        (d for d in reversed(details)
         if d.get("llm_total", 0) > 0 and d.get("llm_done", 0) < d.get("llm_total", 0)),
        None,
    )
    if llm_current_detail is None:
        llm_current_detail = next(
            (d for d in reversed(details) if d.get("status") == "crawled"),
            None,
        )
    llm_current = llm_current_detail.get("hardware") if llm_current_detail else None
    llm_current_done = llm_current_detail.get("llm_done") if llm_current_detail else None
    llm_current_total = llm_current_detail.get("llm_total") if llm_current_detail else None

    return {
        "phase": phase,
        # 整体进度（保留兼容）
        "percent": max(0, min(100, crawl_percent)),
        "processed": crawl_done,
        "total": active_total,
        "current_hardware": current,
        # 爬取进度
        "crawl_percent": max(0, min(100, crawl_percent)),
        "crawl_done": crawl_done,
        "crawl_total": active_total,
        # LLM 校验进度
        "llm_percent": max(0, min(100, llm_percent)),
        "llm_done": llm_done,
        "llm_total": llm_total,
        "llm_current_hardware": llm_current,
        "llm_current_done": llm_current_done,
        "llm_current_total": llm_current_total,
        # 旧字段兼容（前端用）
        "validation_total": llm_total,
        "validation_processed": llm_done,
        "validation_pending": max(0, llm_total - llm_done),
    }


async def crawler_health(db: AsyncSession) -> dict:
    hardware = (await db.execute(select(HardwareItem).where(HardwareItem.is_active == True))).scalars().all()
    today = today_cst()
    alerts: list[dict] = []

    for hw in hardware:
        recent = (
            await db.execute(
                select(DailyStats)
                .where(DailyStats.hardware_id == hw.id)
                .order_by(DailyStats.stat_date.desc())
                .limit(8)
            )
        ).scalars().all()
        latest = recent[0] if recent else None
        if latest is None:
            # 从未采集过，不产生预警，等首次采集完成再评估
            continue
        if latest.stat_date <= today - timedelta(days=2):
            alerts.append({"level": "warning", "hardware_id": hw.id, "hardware": hw.name, "message": "连续 2 天无样本"})
            continue
        if len(recent) >= 2:
            baseline = recent[-1].sample_count
            if baseline > 0 and latest.sample_count <= baseline * 0.3:
                alerts.append({
                    "level": "warning",
                    "hardware_id": hw.id,
                    "hardware": hw.name,
                    "message": "样本数较上期下降超过 70%",
                })

    cookie_age_days = None
    cookie_ok = COOKIE_FILE.exists()
    if cookie_ok:
        cookie_age_days = (datetime.now() - datetime.fromtimestamp(COOKIE_FILE.stat().st_mtime)).days
        if cookie_age_days > 30:
            alerts.append({"level": "warning", "hardware": "cookies.json", "message": "cookies 文件超过 30 天未更新"})
    else:
        alerts.append({"level": "error", "hardware": "cookies.json", "message": "cookies 文件不存在"})

    # 排除 skipped=-1 的单硬件采集记录，只取全量采集的最新一条
    latest_run = (
        await db.execute(
            select(CrawlRun)
            .where(CrawlRun.skipped != -1)
            .order_by(CrawlRun.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    run_count = (await db.execute(select(func.count()).select_from(CrawlRun))).scalar() or 0

    # 查询正在运行的单硬件采集任务（skipped == -1 且状态为活跃）
    active_hw_runs_result = await db.execute(
        select(CrawlRun)
        .where(
            CrawlRun.skipped == -1,
            CrawlRun.status.in_(("running", "crawling", "validating", "aggregating")),
            CrawlRun.ended_at.is_(None),
        )
    )
    active_hw_runs = active_hw_runs_result.scalars().all()
    active_hw_crawls_list = []
    for hw_run in active_hw_runs:
        details = json.loads(hw_run.details_json or "[]")
        hw_name = details[0].get("hardware") if details else None
        active_hw_crawls_list.append({
            "run_id": hw_run.id,
            "hardware_name": hw_name,
            "started_at": hw_run.started_at,
            "progress": _run_progress(hw_run, active_total=1),
        })

    return {
        "status": "ok" if not alerts else "warning",
        "cookie_exists": cookie_ok,
        "cookie_age_days": cookie_age_days,
        "active_hardware": len(hardware),
        "run_count": run_count,
        "latest_run": None if latest_run is None else {
            "id": latest_run.id,
            "status": latest_run.status,
            "started_at": latest_run.started_at,
            "ended_at": latest_run.ended_at,
            "success": latest_run.success,
            "failed": latest_run.failed,
            "skipped": latest_run.skipped,
            "details": json.loads(latest_run.details_json or "[]"),
            "progress": _run_progress(latest_run, len(hardware)),
        },
        "active_hw_crawls": active_hw_crawls_list,
        "alerts": alerts,
    }
