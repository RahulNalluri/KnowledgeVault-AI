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


def _required_integer(name: str) -> int:
    value = _required_environment_value(name)
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc


SECRET_KEY = _required_environment_value("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be at least 50 characters.")
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
CELERY_BROKER_URL = _required_environment_value("CELERY_BROKER_URL")

FRONTEND_URL = _required_environment_value("KV_FRONTEND_URL").rstrip("/")
DEFAULT_FROM_EMAIL = _required_environment_value("KV_DEFAULT_FROM_EMAIL")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = _required_environment_value("EMAIL_HOST")
EMAIL_PORT = _required_integer("EMAIL_PORT")
EMAIL_HOST_USER = _required_environment_value("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = _required_environment_value("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in _required_environment_value("DJANGO_CSRF_TRUSTED_ORIGINS").split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("KV_CORS_ALLOWED_ORIGINS", "").split(",")
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
