"""Fast, isolated settings used by automated tests."""

from .base import *  # noqa: F403

SECRET_KEY = "knowledgevault-test-only-signing-key-that-is-longer-than-fifty-characters"
DEBUG = False
AUTH_REFRESH_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# Redis calls are mocked in unit tests; this value prevents accidental use of
# a development database if a test constructs a client.
REDIS_URL = "redis://unused:6379/15"
CELERY_BROKER_URL = "memory://"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@knowledgevault.test"
FRONTEND_URL = "http://frontend.test"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
