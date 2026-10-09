"""The worker: runs one Check per job from the `checks` queue (ADR 0001)."""

import logging
from datetime import UTC, datetime

import httpx2
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from uptime_watch.checks import check_url, make_client
from uptime_watch.config import get_settings
from uptime_watch.db import get_engine
from uptime_watch.models import Monitor, Result
from uptime_watch.queue import get_queue, get_redis

log = logging.getLogger(__name__)


def check_and_record(session: Session, client: httpx2.Client, monitor_id: int) -> Result | None:
    monitor = session.get(Monitor, monitor_id)
    if monitor is None or monitor.paused:
        # Deleted or paused while the job waited on the queue (ADR 0005).
        return None

    checked_at = datetime.now(UTC)
    outcome = check_url(client, monitor.url)
    result = Result(
        monitor_id=monitor_id,
        checked_at=checked_at,
        up=outcome.up,
        status_code=outcome.status_code,
        response_time_ms=outcome.response_time_ms,
        error=outcome.error,
    )
    session.add(result)
    try:
        session.commit()
    except IntegrityError:
        # The monitor was deleted while its check ran; its results are gone with it.
        session.rollback()
        return None
    return result


def run_check(monitor_id: int) -> None:
    """RQ job. The scheduler queues it with the monitor id only."""
    settings = get_settings()
    with Session(get_engine()) as session, make_client(settings.check_timeout_seconds) as client:
        result = check_and_record(session, client, monitor_id)
        if result is not None:
            log.info(
                "monitor %s: %s %s %s",
                monitor_id,
                "up" if result.up else "down",
                result.status_code or "-",
                result.error or f"{result.response_time_ms} ms",
            )


def main() -> None:
    from rq import Worker

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    connection = get_redis()
    Worker([get_queue(connection)], connection=connection).work()
