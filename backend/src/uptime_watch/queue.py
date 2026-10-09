from redis import Redis
from rq import Queue

from uptime_watch.config import get_settings

QUEUE_NAME = "checks"
# A hung Redis must not block the scheduler inside its transaction, holding row locks.
REDIS_TIMEOUT_SECONDS = 5


def get_redis() -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        socket_timeout=REDIS_TIMEOUT_SECONDS,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
    )


def get_queue(connection: Redis) -> Queue:
    return Queue(QUEUE_NAME, connection=connection)
