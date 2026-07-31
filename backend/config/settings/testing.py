"""Fast, isolated settings used by automated tests."""

from .base import *  # noqa: F403

SECRET_KEY = "knowledgevault-test-only-key"
DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# Redis calls are mocked in unit tests; this value prevents accidental use of
# a development database if a test constructs a client.
REDIS_URL = "redis://unused:6379/15"
