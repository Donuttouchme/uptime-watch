from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from uptime_watch.db import Base


class Monitor(Base):
    __tablename__ = "monitors"
    __table_args__ = (UniqueConstraint("url", name="uq_monitors_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2083))
    interval_seconds: Mapped[int] = mapped_column(default=60, server_default=text("60"))
    paused: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
