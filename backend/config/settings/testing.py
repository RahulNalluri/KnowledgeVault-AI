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
