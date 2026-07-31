"""Fail-closed production settings."""

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def _required_environment_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Required environment variable is missing: {name}")
    return value


SECRET_KEY = _required_environment_value("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in _required_environment_value("DJANGO_ALLOWED_HOSTS").split(",")
    if host.strip()
]

DATABASES = {
    "default": dj_database_url.parse(
        _required_environment_value("DATABASE_URL"),
        conn_max_age=60,
        conn_health_checks=True,
        ssl_require=True,
    ),
}

REDIS_URL = _required_environment_value("REDIS_URL")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in _required_environment_value("DJANGO_CSRF_TRUSTED_ORIGINS").split(",")
    if origin.strip()
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
