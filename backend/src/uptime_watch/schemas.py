from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, model_validator

MIN_INTERVAL_SECONDS = 30
MAX_INTERVAL_SECONDS = 86_400
MAX_URL_LENGTH = 2083
# Postgres text cannot hold NUL, and control characters in a name help nobody.
NO_CONTROL_CHARACTERS = r"^[^\x00-\x1f\x7f]*$"


def _check_url_length(url: HttpUrl) -> HttpUrl:
    # Measured after normalisation: percent-encoding can make a URL several times longer
    # than it was typed, and the column is sized for the normalised form.
    if len(str(url)) > MAX_URL_LENGTH:
        raise ValueError(f"url must be at most {MAX_URL_LENGTH} characters once normalised")
    return url


MonitorUrl = Annotated[HttpUrl, AfterValidator(_check_url_length)]


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=NO_CONTROL_CHARACTERS)
    # HttpUrl accepts only http/https and normalises host case and the bare-host slash,
    # so "https://Example.com" and "https://example.com/" are the same monitor.
    url: MonitorUrl
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
    name: str | None = Field(
        default=None, min_length=1, max_length=100, pattern=NO_CONTROL_CHARACTERS
    )
    url: MonitorUrl | None = None
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
