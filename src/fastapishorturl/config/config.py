from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "FastAPI ShortURL"
    app_version: str = "1.0.0"
    ASYNC_DATABASE_URL: str = "sqlite+aiosqlite:///short.db"
    TOKEN_SIGN_SECRET: str = "ZAXYS916"

@lru_cache
def get_settings():
    return Settings()

