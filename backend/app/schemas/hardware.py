from datetime import date
from pydantic import BaseModel
from app.models.price import PriceLevel


class HardwareListItem(BaseModel):
    id: int
    name: str
    category: str

    model_config = {"from_attributes": True}


class DailyStatsOut(BaseModel):
    stat_date: date
    median_price: float
    avg_price: float
    min_price: float
    max_price: float
    sample_count: int
    price_level: PriceLevel

    model_config = {"from_attributes": True}


class HardwareDetail(BaseModel):
    id: int
    name: str
    category: str
    latest_stats: DailyStatsOut | None = None

    model_config = {"from_attributes": True}


class TrendPoint(BaseModel):
    date: date
    median_price: float
    avg_price: float
    min_price: float
    max_price: float
    sample_count: int
    price_level: PriceLevel


class TrendResponse(BaseModel):
    hardware_id: int
    hardware_name: str
    days: int
    trend: list[TrendPoint]


class CrawlerStatus(BaseModel):
    last_run_date: date | None
    last_run_success: int
    last_run_failed: int


class CrawlerRunResponse(BaseModel):
    status: str
    summary: dict
