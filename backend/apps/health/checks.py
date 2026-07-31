from django.conf import settings
from django.db import DatabaseError, connection
from redis import Redis
from redis.exceptions import RedisError


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
