from datetime import timedelta

from app.core.timezone import now_cst

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyStats, HardwareItem, PriceAlert
from app.models.price import PriceLevel
from app.services.notifier import send_notification


def _alert_applies(alert: PriceAlert, hardware: HardwareItem) -> bool:
    if alert.scope_type == "all":
        return True
    if alert.scope_type == "category":
        return alert.scope_value == hardware.category
    if alert.scope_type == "hardware":
        return alert.scope_value == str(hardware.id)
    return False


def _rule_matches(alert: PriceAlert, stats: DailyStats, history_median: float | None) -> bool:
    if alert.rule_type == "below_price":
        return alert.threshold is not None and stats.median_price <= alert.threshold
    if alert.rule_type == "below_median_pct":
        if alert.threshold is None or not history_median:
            return False
        return stats.median_price <= history_median * (1 - alert.threshold)
    if alert.rule_type == "level_low":
        return stats.price_level == PriceLevel.low
    return False


async def evaluate_alerts_after_crawl(db: AsyncSession, hardware: HardwareItem, stats: DailyStats | None) -> int:
    if stats is None:
        return 0

    historical = (
        await db.execute(
            select(DailyStats.median_price)
            .where(
                DailyStats.hardware_id == hardware.id,
                DailyStats.stat_date < stats.stat_date,
            )
            .order_by(DailyStats.stat_date.desc())
            .limit(30)
        )
    ).scalars().all()
    history_median = None
    if historical:
        ordered = sorted(historical)
        history_median = ordered[len(ordered) // 2]

    alerts = (
        await db.execute(select(PriceAlert).where(PriceAlert.is_active == True))
    ).scalars().all()
    fired = 0
    now = now_cst()
    for alert in alerts:
        if not _alert_applies(alert, hardware):
            continue
        if alert.last_fired_at and alert.last_fired_at + timedelta(hours=alert.cooldown_hours) > now:
            continue
        if not _rule_matches(alert, stats, history_median):
            continue
        message = (
            f"价格提醒命中：{hardware.name}\n"
            f"中位价 ¥{stats.median_price:.0f}，样本 {stats.sample_count} 条，状态 {stats.price_level.value}"
        )
        if await send_notification(alert.channel, alert.channel_target, message):
            alert.last_fired_at = now
            fired += 1
    await db.commit()
    return fired
