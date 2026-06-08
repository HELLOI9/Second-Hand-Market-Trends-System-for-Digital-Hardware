import json
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CrawlRun, DailyStats, HardwareItem, PriceSnapshot


COOKIE_FILE = Path(__file__).resolve().parents[2] / "cookies.json"


def _run_progress(
    latest_run: CrawlRun | None,
    active_total: int,
    validation_total: int = 0,
    validation_pending: int = 0,
) -> dict | None:
    if latest_run is None:
        return None

    details = json.loads(latest_run.details_json or "[]")
    total = max(active_total, 1)
    crawled = latest_run.success + latest_run.failed + latest_run.skipped
    aggregated = sum(1 for item in details if item.get("status") in {"aggregated", "no_valid_samples", "aggregation_failed"})
    phase = latest_run.status

    validation_processed = max(0, validation_total - validation_pending)

    if phase in {"success", "partial"}:
        percent = 100
    elif phase == "validating":
        if validation_total:
            percent = 75 + round((validation_processed / validation_total) * 10)
        else:
            percent = 80
    elif phase == "aggregating":
        percent = 85 + round((aggregated / max(latest_run.success, 1)) * 15) if latest_run.success else 85
    else:
        percent = round((crawled / total) * 75)

    current = details[-1].get("hardware") if details else None
    return {
        "phase": phase,
        "percent": max(0, min(100, percent)),
        "processed": min(crawled, total),
        "total": active_total,
        "current_hardware": current,
        "validation_total": validation_total,
        "validation_processed": validation_processed,
        "validation_pending": validation_pending,
    }


async def crawler_health(db: AsyncSession) -> dict:
    hardware = (await db.execute(select(HardwareItem).where(HardwareItem.is_active == True))).scalars().all()
    today = date.today()
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
        if latest is None or latest.stat_date <= today - timedelta(days=2):
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

    latest_run = (
        await db.execute(select(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(1))
    ).scalar_one_or_none()
    run_count = (await db.execute(select(func.count()).select_from(CrawlRun))).scalar() or 0
    validation_total = 0
    validation_pending = 0
    if latest_run is not None and latest_run.status == "validating":
        details = json.loads(latest_run.details_json or "[]")
        crawled_ids = [
            item.get("hardware_id")
            for item in details
            if item.get("status") == "crawled" and item.get("hardware_id") is not None
        ]
        if crawled_ids:
            validation_total = (
                await db.execute(
                    select(func.count())
                    .select_from(PriceSnapshot)
                    .where(
                        PriceSnapshot.snapshot_date == today,
                        PriceSnapshot.hardware_id.in_(crawled_ids),
                    )
                )
            ).scalar() or 0
            validation_pending = (
                await db.execute(
                    select(func.count())
                    .select_from(PriceSnapshot)
                    .where(
                        PriceSnapshot.snapshot_date == today,
                        PriceSnapshot.hardware_id.in_(crawled_ids),
                        PriceSnapshot.is_valid.is_(None),
                    )
                )
            ).scalar() or 0

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
            "progress": _run_progress(latest_run, len(hardware), validation_total, validation_pending),
        },
        "alerts": alerts,
    }
