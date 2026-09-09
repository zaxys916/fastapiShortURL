from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（config/ -> fastapishorturl/ -> src/ -> 项目根）
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置，优先从环境变量 / 项目根 .env 读取。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8"
    )

    APP_NAME: str = "fastapishorturl"
    APP_VERSION: str = "1.0.0"
    ASYNC_DATABASE_URL: str = "sqlite+aiosqlite:///src/fastapishorturl/short.db"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"


@lru_cache
def get_settings() -> Settings:
    return Settings()