from datetime import date, datetime
from sqlalchemy import String, Text, ForeignKey, Date, DateTime, Float, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class PriceLevel(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"


class PriceSnapshot(Base):
    """每日爬取的原始价格样本"""

    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    hardware_id: Mapped[int] = mapped_column(ForeignKey("hardware_items.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    item_url: Mapped[str | None] = mapped_column(Text)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Fields from spider.py
    area: Mapped[str | None] = mapped_column(String(100))
    seller: Mapped[str | None] = mapped_column(String(100))
    image_url: Mapped[str | None] = mapped_column(Text)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    hardware: Mapped["HardwareItem"] = relationship(back_populates="price_snapshots")

    def __repr__(self) -> str:
        return f"<PriceSnapshot hardware_id={self.hardware_id} price={self.price} date={self.snapshot_date}>"


class DailyStats(Base):
    """每日价格聚合统计"""

    __tablename__ = "daily_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    hardware_id: Mapped[int] = mapped_column(ForeignKey("hardware_items.id"), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    median_price: Mapped[float] = mapped_column(Float, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    min_price: Mapped[float] = mapped_column(Float, nullable=False)
    max_price: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    price_level: Mapped[PriceLevel] = mapped_column(Enum(PriceLevel), nullable=False)

    hardware: Mapped["HardwareItem"] = relationship(back_populates="daily_stats")

    def __repr__(self) -> str:
        return f"<DailyStats hardware_id={self.hardware_id} date={self.stat_date} median={self.median_price}>"
