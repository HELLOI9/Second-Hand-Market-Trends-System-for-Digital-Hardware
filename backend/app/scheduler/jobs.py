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


def start_scheduler():
    # CRAWLER_SCHEDULE 格式: "minute hour day month day_of_week"
    parts = settings.crawler_schedule.split()
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
    else:
        # 默认凌晨 2 点
        minute, hour, day, month, day_of_week = "0", "2", "*", "*", "*"

    scheduler.add_job(
        _scheduled_crawl,
        CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
        id="daily_crawl",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("调度器已启动，爬取计划：%s", settings.crawler_schedule)


def stop_scheduler():
    scheduler.shutdown(wait=False)
