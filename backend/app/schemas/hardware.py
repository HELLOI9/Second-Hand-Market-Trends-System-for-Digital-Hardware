from datetime import date
from pydantic import BaseModel
from app.models.price import PriceLevel


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
    search_keywords: list[str] = []
    validation_rule: str | None = None
    is_active: bool = True
    latest_stats: DailyStatsOut | None = None
    # 全站最近一轮采集日期（锚点）。详情页用它判断 latest_stats 是否为当轮数据。
    latest_run_date: date | None = None
    # latest_stats 是否早于全站锚点日（即不是本轮数据，属于历史回退）
    stats_is_stale: bool = False

    model_config = {"from_attributes": True}


class HardwareCreate(BaseModel):
    name: str
    category: str
    search_keywords: list[str] = []
    validation_rule: str | None = None
    cold_start: bool = True


class HardwareUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    search_keywords: list[str] | None = None
    validation_rule: str | None = None
    is_active: bool | None = None


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


class HardwareSampleOut(BaseModel):
    id: int
    price: float
    title: str
    item_url: str | None = None
    area: str | None = None
    seller: str | None = None
    image_url: str | None = None
    publish_time: str | None = None
    snapshot_date: date


class CrawlerStatus(BaseModel):
    last_run_date: date | None
    last_run_success: int
    last_run_failed: int


class CrawlerRunResponse(BaseModel):
    status: str
    summary: dict
