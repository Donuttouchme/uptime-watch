from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from uptime_watch.db import escape_for_alembic
from uptime_watch.models import Monitor, Result


def add_monitor(session, **fields):
    monitor = Monitor(name="Example", url="https://example.com/", **fields)
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return monitor


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


def test_new_monitor_is_due_at_once(session):
    monitor = add_monitor(session)

    assert monitor.next_check_at <= datetime.now(UTC)


def test_database_rejects_interval_outside_range(session):
    session.add(Monitor(name="Fast", url="https://example.com/", interval_seconds=10))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_database_rejects_empty_name(session):
    session.add(Monitor(name="", url="https://example.com/"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_database_rejects_impossible_status_code(session):
    monitor = add_monitor(session)
    session.add(Result(monitor_id=monitor.id, checked_at=datetime.now(UTC), up=False, status_code=99))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_database_rejects_negative_response_time(session):
    monitor = add_monitor(session)
    session.add(
        Result(monitor_id=monitor.id, checked_at=datetime.now(UTC), up=True, response_time_ms=-1)
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_result_without_response_is_allowed(session):
    monitor = add_monitor(session)
    session.add(
        Result(monitor_id=monitor.id, checked_at=datetime.now(UTC), up=False, error="timeout")
    )
    session.commit()

    assert session.scalar(select(func.count()).select_from(Result)) == 1


def test_deleting_a_monitor_deletes_its_results(session):
    monitor = add_monitor(session)
    session.add(
        Result(
            monitor_id=monitor.id,
            checked_at=datetime.now(UTC) - timedelta(seconds=5),
            up=True,
            status_code=200,
            response_time_ms=12,
        )
    )
    session.commit()

    session.delete(monitor)
    session.commit()

    assert session.scalar(select(func.count()).select_from(Result)) == 0


def test_escape_for_alembic_doubles_percent_signs():
    url = "postgresql+psycopg://u:p%40ss@localhost/db"

    assert escape_for_alembic(url) == "postgresql+psycopg://u:p%%40ss@localhost/db"
