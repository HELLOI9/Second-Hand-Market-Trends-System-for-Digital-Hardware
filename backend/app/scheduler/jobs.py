"""
APScheduler 定时任务：每天凌晨 2 点执行一次全量爬取
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services import run_full_crawl

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _scheduled_crawl():
    logger.info("定时任务触发：开始全量爬取")
    async with AsyncSessionLocal() as db:
        summary = await run_full_crawl(db)
    logger.info("定时任务完成：%s", summary)


def _parse_schedule_times(times_str: str) -> list[tuple[str, str]]:
    """Parse 'HH:MM,HH:MM,...' into list of (hour, minute) tuples."""
    result = []
    for token in times_str.split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split(":")
        if len(parts) == 2:
            try:
                h, m = int(parts[0]), int(parts[1])
                if 0 <= h <= 23 and 0 <= m <= 59:
                    result.append((str(h), str(m)))
            except ValueError:
                pass
    return result or [("2", "0")]


def start_scheduler():
    times = _parse_schedule_times(settings.crawler_schedule_times)

    for i, (hour, minute) in enumerate(times):
        scheduler.add_job(
            _scheduled_crawl,
            CronTrigger(hour=hour, minute=minute),
            id=f"daily_crawl_{i}",
            replace_existing=True,
            misfire_grace_time=3600,
        )

    scheduler.start()
    logger.info("调度器已启动，爬取时间点：%s", settings.crawler_schedule_times)


def stop_scheduler():
    scheduler.shutdown(wait=False)
