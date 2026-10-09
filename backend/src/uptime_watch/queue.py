from redis import Redis
from rq import Queue

from uptime_watch.config import get_settings

QUEUE_NAME = "checks"


def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def get_queue(connection: Redis) -> Queue:
    return Queue(QUEUE_NAME, connection=connection)
