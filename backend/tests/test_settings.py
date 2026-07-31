import importlib
import sys

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

PRODUCTION_SETTINGS_MODULE = "config.settings.production"


def test_automated_tests_use_isolated_sqlite_database() -> None:
    database = settings.DATABASES["default"]

    assert database["ENGINE"] == "django.db.backends.sqlite3"
    assert "memory" in str(database["NAME"])


def test_automated_tests_do_not_require_external_ai_credentials() -> None:
    assert not hasattr(settings, "OPENROUTER_API_KEY")


def test_production_settings_fail_when_secret_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)

    try:
        with pytest.raises(
            ImproperlyConfigured,
            match="DJANGO_SECRET_KEY",
        ):
            importlib.import_module(PRODUCTION_SETTINGS_MODULE)
    finally:
        sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)


def test_production_settings_require_https_and_postgresql(monkeypatch) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "production-test-secret")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "app.example.com")
    monkeypatch.setenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://app.example.com",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@database:5432/knowledgevault",
    )
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)

    try:
        production = importlib.import_module(PRODUCTION_SETTINGS_MODULE)

        assert production.DEBUG is False
        assert production.SECURE_SSL_REDIRECT is True
        assert production.SESSION_COOKIE_SECURE is True
        assert production.CSRF_COOKIE_SECURE is True
        assert production.DATABASES["default"]["ENGINE"] == ("django.db.backends.postgresql")
        assert production.REDIS_URL == "redis://redis:6379/0"
    finally:
        sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)
