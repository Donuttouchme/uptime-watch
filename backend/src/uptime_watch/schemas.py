from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

MIN_INTERVAL_SECONDS = 30
MAX_INTERVAL_SECONDS = 86_400


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # HttpUrl accepts only http/https and normalises host case and the bare-host slash,
    # so "https://Example.com" and "https://example.com/" are the same monitor.
    url: HttpUrl
    interval_seconds: int = Field(default=60, ge=MIN_INTERVAL_SECONDS, le=MAX_INTERVAL_SECONDS)
    paused: bool = False


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    interval_seconds: int
    paused: bool
    created_at: datetime
