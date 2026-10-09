import threading
from datetime import UTC, datetime, timedelta

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from uptime_watch.models import Monitor
from uptime_watch.scheduler import enqueue_due, run, try_acquire_lock


def add_monitor(session, url, due_in_seconds, **fields):
    monitor = Monitor(
        name=url,
        url=url,
        next_check_at=datetime.now(UTC) + timedelta(seconds=due_in_seconds),
        **fields,
    )
    session.add(monitor)
    session.commit()
    return monitor


def autocommit_connection(engine):
    # NullPool: close() really closes the database connection, which is what
    # releases an advisory lock. A pooled connection would keep the lock alive.
    unpooled = create_engine(engine.url, poolclass=NullPool)
    return unpooled.connect().execution_options(isolation_level="AUTOCOMMIT")


def test_queues_only_due_unpaused_monitors(session, queue):
    due = add_monitor(session, "https://due.example/", -1, interval_seconds=45)
    add_monitor(session, "https://paused.example/", -1, paused=True)
    add_monitor(session, "https://later.example/", 300)

    assert enqueue_due(session, queue) == [due.id]

    [job] = queue.get_jobs()
    assert job.func_name == "uptime_watch.worker.run_check"
    assert job.args == (due.id,)
    assert job.ttl == 45


def test_moves_the_next_check_one_interval_ahead(session, queue):
    due = add_monitor(session, "https://due.example/", -1, interval_seconds=120)

    enqueue_due(session, queue)
    session.refresh(due)

    assert due.next_check_at >= datetime.now(UTC) + timedelta(seconds=110)


def test_a_second_tick_queues_nothing(session, queue):
    add_monitor(session, "https://due.example/", -1)

    enqueue_due(session, queue)

    assert enqueue_due(session, queue) == []
    assert queue.count == 1


class BrokenQueue:
    def enqueue(self, *args, **kwargs):
        raise RedisConnectionError("Redis is down")


def test_redis_failure_keeps_the_monitor_due(session):
    due = add_monitor(session, "https://due.example/", -1)

    with pytest.raises(RedisConnectionError):
        enqueue_due(session, BrokenQueue())
    session.refresh(due)

    assert due.next_check_at <= datetime.now(UTC)


def test_the_lock_admits_one_scheduler(engine):
    first, second = autocommit_connection(engine), autocommit_connection(engine)
    try:
        assert try_acquire_lock(first) is True
        assert try_acquire_lock(second) is False
        first.close()
        assert try_acquire_lock(second) is True
    finally:
        first.close()
        second.close()


def test_run_ticks_once_then_stops(session, engine, queue):
    add_monitor(session, "https://due.example/", -1)
    stop = threading.Event()
    stop.set()

    run(engine, queue, 0.01, stop)

    assert queue.count == 1


def test_run_waits_while_another_scheduler_holds_the_lock(session, engine, queue):
    add_monitor(session, "https://due.example/", -1)
    holder = autocommit_connection(engine)
    try:
        assert try_acquire_lock(holder)
        stop = threading.Event()
        stop.set()

        run(engine, queue, 0.01, stop)

        assert queue.count == 0
    finally:
        holder.close()


def test_run_survives_a_failing_tick(session, engine):
    add_monitor(session, "https://due.example/", -1)
    stop = threading.Event()
    stop.set()

    run(engine, BrokenQueue(), 0.01, stop)  # logs the error instead of raising
