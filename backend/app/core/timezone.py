"""
统一时区工具：系统所有时间使用 UTC+8（北京时间）。
"""

from datetime import date, datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))


def now_cst() -> datetime:
    """返回当前 UTC+8 时间（naive datetime，不带 tzinfo）。"""
    return datetime.now(tz=CST).replace(tzinfo=None)


def today_cst() -> date:
    """返回当前 UTC+8 日期。"""
    return datetime.now(tz=CST).date()
