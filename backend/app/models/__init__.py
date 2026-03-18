from app.core.database import Base  # noqa: F401 — 让 Alembic 能发现所有模型

from .hardware import HardwareItem
from .price import PriceSnapshot, DailyStats

__all__ = ["HardwareItem", "PriceSnapshot", "DailyStats"]
