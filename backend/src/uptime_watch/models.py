from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from uptime_watch.db import Base


class Monitor(Base):
    __tablename__ = "monitors"
    __table_args__ = (
        UniqueConstraint("url", name="uq_monitors_url"),
        CheckConstraint("interval_seconds BETWEEN 30 AND 86400", name="ck_monitors_interval_range"),
        CheckConstraint("char_length(name) >= 1", name="ck_monitors_name_not_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2083))
    interval_seconds: Mapped[int] = mapped_column(default=60, server_default=text("60"))
    paused: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # When the monitor is next Due (ADR 0005). Set by the database, the API and the scheduler.
    next_check_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (
        CheckConstraint("status_code BETWEEN 100 AND 599", name="ck_results_status_code_range"),
        CheckConstraint("response_time_ms >= 0", name="ck_results_response_time_not_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    up: Mapped[bool]
    # All three are empty when no response arrived; error then says why.
    status_code: Mapped[int | None]
    response_time_ms: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(String(200))
