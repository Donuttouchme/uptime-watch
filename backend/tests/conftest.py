import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from uptime_watch.db import escape_for_alembic

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(BACKEND_DIR / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set: add it to backend/.env", returncode=1)
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
        connection.execute(text("TRUNCATE monitors RESTART IDENTITY"))
    with Session(engine) as session:
        yield session
