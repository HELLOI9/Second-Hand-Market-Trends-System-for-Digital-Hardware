from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HardwareItem(Base):
    """固定监控硬件池"""

    __tablename__ = "hardware_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # cpu / gpu / memory / ssd

    # 关联
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="hardware", cascade="all, delete-orphan")
    daily_stats: Mapped[list["DailyStats"]] = relationship(back_populates="hardware", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<HardwareItem {self.category}/{self.name}>"
