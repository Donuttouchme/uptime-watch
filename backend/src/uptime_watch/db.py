from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from uptime_watch.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping drops dead connections, e.g. after a database restart.
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def escape_for_alembic(url: str) -> str:
    # Alembic's ini parser treats % as interpolation; a %-encoded password would break it.
    return url.replace("%", "%%")
