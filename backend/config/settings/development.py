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

DATABASES = {
    "default": dj_database_url.config(
        default=("postgresql://knowledgevault:knowledgevault@localhost:5432/knowledgevault"),
        conn_max_age=0,
        conn_health_checks=True,
    ),
}
