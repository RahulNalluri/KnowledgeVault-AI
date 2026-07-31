from celery.exceptions import CeleryError
from django.conf import settings
from django.db import DatabaseError, connection
from kombu.exceptions import KombuError
from redis import Redis
from redis.exceptions import RedisError

from config.celery import app as celery_app


def database_is_ready() -> bool:
    """Return whether Django can execute a minimal database query."""

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return False

    return True


def redis_is_ready() -> bool:
    """Return whether the configured Redis server responds to PING."""

    client = None
    try:
        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        return bool(client.ping())
    except (RedisError, ValueError):
        return False
    finally:
        if client is not None:
            client.close()


def celery_worker_is_ready() -> bool:
    """Return whether at least one Celery worker responds to a control ping."""

    try:
        replies = celery_app.control.ping(timeout=1.0)
    except (CeleryError, KombuError, RedisError, OSError, ValueError):
        return False

    return any(
        isinstance(status, dict) and status.get("ok") == "pong"
        for reply in replies or []
        if isinstance(reply, dict)
        for status in reply.values()
    )
