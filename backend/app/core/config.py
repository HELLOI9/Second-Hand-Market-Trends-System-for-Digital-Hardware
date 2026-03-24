from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://market:market_pass@localhost:5432/market"
    crawler_schedule: str = "0 2 * * *"
    debug: bool = False
    llm_base_url: str = "http://localhost:8082"
    llm_model: str = "Qwen3.5-9B-Q8_0.gguf"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production", "off", "false", "0", "no"}:
                return False
            if lowered in {"debug", "dev", "development", "on", "true", "1", "yes"}:
                return True
        return value

    class Config:
        env_file = str(ROOT_ENV_FILE)
        extra = "ignore"


settings = Settings()
