from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables.

    `.env` is only a local convenience; in containers and CI the same names
    come from the real environment.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    scheduler_tick_seconds: float = Field(default=5, gt=0)
    check_timeout_seconds: float = Field(default=10, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
