"""Local development settings."""

import os

import dj_database_url
from dotenv import load_dotenv

from .base import *  # noqa: F403
from .base import BASE_DIR

load_dotenv(BASE_DIR.parent / ".env", override=False)

# This public fallback is intentionally development-only and is not a secret.
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "knowledgevault-development-only-key-not-for-production",
)
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "KV_CORS_ALLOWED_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

DATABASES = {
    "default": dj_database_url.config(
        default=("postgresql://knowledgevault:knowledgevault@localhost:5432/knowledgevault"),
        conn_max_age=0,
        conn_health_checks=True,
    ),
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6380/1")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
