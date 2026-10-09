"""The scheduler: queues a Check for every Due monitor (ADR 0001, ADR 0005).

Exactly one scheduler may be active; a Postgres advisory lock enforces it.
"""

import logging
import signal
import threading

from rq import Queue
from sqlalchemy import Connection, Engine, text
from sqlalchemy.orm import Session

from uptime_watch.config import get_settings
from uptime_watch.db import get_engine
from uptime_watch.queue import get_queue, get_redis
from uptime_watch.worker import run_check

log = logging.getLogger(__name__)

# Any fixed number works; only the scheduler takes this lock.
SCHEDULER_LOCK_KEY = 7_420_001
FAILED_JOB_TTL_SECONDS = 86_400

_TAKE_DUE = text(
    """
    UPDATE monitors
    SET next_check_at = now() + make_interval(secs => interval_seconds)
    WHERE NOT paused AND next_check_at <= now()
    RETURNING id, interval_seconds
    """
)


def enqueue_due(session: Session, queue: Queue) -> list[int]:
    """Queue one check per Due monitor and move each one's next check an interval ahead.

    The UPDATE and the queueing share one transaction: if Redis fails, the
    UPDATE rolls back and the monitors are still due on the next tick.

    Delivery is at-least-once, not exactly-once. If Redis fails part-way, or the
    commit fails after the enqueues, the jobs already queued stay queued while the
    UPDATE rolls back, so those monitors are queued again next tick. The job TTL
    (one interval) bounds the extra to one check per monitor.
    """
    try:
        rows = session.execute(_TAKE_DUE).all()
        for monitor_id, interval_seconds in rows:
            # A job older than one interval is stale: a newer one is already behind it.
            queue.enqueue(
                run_check,
                monitor_id,
                ttl=interval_seconds,
                result_ttl=0,
                failure_ttl=FAILED_JOB_TTL_SECONDS,
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return [monitor_id for monitor_id, _ in rows]


def try_acquire_lock(connection: Connection) -> bool:
    """Take the scheduler lock on this connection.

    The lock is session-level: it lasts as long as the database session. With a
    pooled engine, closing the Connection only returns the session to the pool and
    does not end it, so the caller must invalidate() the connection to release the
    lock (as run() does).
    """
    return bool(
        connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": SCHEDULER_LOCK_KEY}
        ).scalar()
    )


def run(engine: Engine, queue: Queue, tick_seconds: float, stop: threading.Event) -> None:
    lock_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        if not try_acquire_lock(lock_connection):
            log.warning("another scheduler is running; waiting for its lock")
            while not try_acquire_lock(lock_connection):
                if stop.wait(tick_seconds):
                    return
        log.info("scheduler lock acquired; checking for due monitors every %s s", tick_seconds)

        while True:
            # If the lock's connection died, so did the lock: fail rather than run unprotected.
            lock_connection.execute(text("SELECT 1"))
            try:
                with Session(engine) as session:
                    queued = enqueue_due(session, queue)
                if queued:
                    log.info("queued %d checks", len(queued))
            except Exception:
                log.exception("tick failed; trying again next tick")
            if stop.wait(tick_seconds):
                return
    finally:
        # close() would only return the connection to the pool, with the lock
        # still held; invalidate() closes the database connection and frees the lock.
        lock_connection.invalidate()
        lock_connection.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    run(get_engine(), get_queue(get_redis()), get_settings().scheduler_tick_seconds, stop)
    log.info("scheduler stopped")
