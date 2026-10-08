import pytest
from sqlalchemy.exc import IntegrityError

from uptime_watch.db import escape_for_alembic
from uptime_watch.models import Monitor


def test_monitor_gets_defaults_on_insert(session):
    monitor = Monitor(name="Example", url="https://example.com/")
    session.add(monitor)
    session.commit()
    session.refresh(monitor)

    assert monitor.id is not None
    assert monitor.interval_seconds == 60
    assert monitor.paused is False
    assert monitor.created_at.tzinfo is not None


def test_monitor_url_is_unique(session):
    session.add(Monitor(name="First", url="https://example.com/"))
    session.commit()

    session.add(Monitor(name="Second", url="https://example.com/"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_escape_for_alembic_doubles_percent_signs():
    url = "postgresql+psycopg://u:p%40ss@localhost/db"

    assert escape_for_alembic(url) == "postgresql+psycopg://u:p%%40ss@localhost/db"
