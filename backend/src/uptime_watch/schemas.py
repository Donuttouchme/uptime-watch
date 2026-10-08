from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

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


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: HttpUrl | None = None
    interval_seconds: int | None = Field(
        default=None, ge=MIN_INTERVAL_SECONDS, le=MAX_INTERVAL_SECONDS
    )
    paused: bool | None = None

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> "MonitorUpdate":
        # Omitting a field means "leave it"; sending null would mean "erase it",
        # which none of these columns allow.
        nulls = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"fields cannot be null: {', '.join(nulls)}")
        return self


class MonitorPage(BaseModel):
    items: list[MonitorRead]
    total: int
    limit: int
    offset: int
