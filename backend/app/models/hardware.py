from datetime import datetime

from app.core.timezone import now_cst

from sqlalchemy import ARRAY, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timezone import now_cst


class HardwareItem(Base):
    """固定监控硬件池"""

    __tablename__ = "hardware_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # cpu / gpu / memory / ssd
    search_keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    validation_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_cst)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_cst, onupdate=now_cst)

    # 关联
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="hardware", cascade="all, delete-orphan")
    daily_stats: Mapped[list["DailyStats"]] = relationship(back_populates="hardware", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<HardwareItem {self.category}/{self.name}>"
