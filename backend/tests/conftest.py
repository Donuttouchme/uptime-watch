import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from uptime_watch.db import escape_for_alembic

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(BACKEND_DIR / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set: add it to backend/.env", returncode=1)
    # The engine fixture runs `downgrade base`, which drops every table.
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.exit(
            f"TEST_DATABASE_URL must point to a database whose name ends in _test, got {database!r}",
            returncode=1,
        )
    return url


@pytest.fixture(scope="session")
def engine():
    url = _test_database_url()

    # Build the schema the way production will: through the migrations.
    # Going down to base first also exercises every downgrade.
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", escape_for_alembic(url))
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE monitors, results RESTART IDENTITY"))
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(session):
    from fastapi.testclient import TestClient

    from uptime_watch.api.app import app
    from uptime_watch.db import get_session

    def _session_override():
        yield session

    app.dependency_overrides[get_session] = _session_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _test_redis_url() -> str:
    url = (
        os.environ.get("TEST_REDIS_URL")
        or dotenv_values(BACKEND_DIR / ".env").get("TEST_REDIS_URL")
        or "redis://localhost:6379/15"
    )
    # Every test empties this database (FLUSHDB), so only the test database 15 is allowed.
    if urlsplit(url).path != "/15":
        pytest.exit(f"TEST_REDIS_URL must use Redis database 15, got {url!r}", returncode=1)
    return url


@pytest.fixture
def redis_conn():
    from redis import Redis
    from redis.exceptions import ConnectionError as RedisConnectionError

    connection = Redis.from_url(_test_redis_url())
    try:
        connection.ping()
    except RedisConnectionError:
        pytest.exit("Redis is not running: see 'Run locally' in the README", returncode=1)
    connection.flushdb()
    yield connection
    connection.flushdb()
    connection.close()


@pytest.fixture
def queue(redis_conn):
    from uptime_watch.queue import get_queue

    return get_queue(redis_conn)


@pytest.fixture
def app_uses_test_database(monkeypatch):
    """Point code that opens its own session (get_engine) at the test database."""
    from uptime_watch import config, db

    monkeypatch.setenv("DATABASE_URL", _test_database_url())
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    yield
    db.get_engine().dispose()
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
