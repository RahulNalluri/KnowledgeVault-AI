import importlib
import sys

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

PRODUCTION_SETTINGS_MODULE = "config.settings.production"
DEVELOPMENT_SETTINGS_MODULE = "config.settings.development"
PRODUCTION_ENVIRONMENT = {
    "DJANGO_SECRET_KEY": "production-test-secret",
    "DJANGO_ALLOWED_HOSTS": "app.example.com",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://app.example.com",
    "DATABASE_URL": "postgresql://user:password@database:5432/knowledgevault",
    "REDIS_URL": "redis://redis:6379/0",
    "CELERY_BROKER_URL": "redis://redis:6379/1",
}


def set_production_environment(monkeypatch) -> None:
    for name, value in PRODUCTION_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)


def test_automated_tests_use_isolated_sqlite_database() -> None:
    database = settings.DATABASES["default"]

    assert database["ENGINE"] == "django.db.backends.sqlite3"
    assert "memory" in str(database["NAME"])


def test_automated_tests_do_not_require_external_ai_credentials() -> None:
    assert not hasattr(settings, "OPENROUTER_API_KEY")


def test_development_settings_parse_container_hosts_and_origins(monkeypatch) -> None:
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "localhost,backend")
    monkeypatch.setenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://localhost:3000,http://localhost:8000",
    )
    monkeypatch.setenv(
        "KV_CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    sys.modules.pop(DEVELOPMENT_SETTINGS_MODULE, None)

    try:
        development = importlib.import_module(DEVELOPMENT_SETTINGS_MODULE)

        assert development.ALLOWED_HOSTS == ["localhost", "backend"]
        assert development.CSRF_TRUSTED_ORIGINS == [
            "http://localhost:3000",
            "http://localhost:8000",
        ]
        assert development.CORS_ALLOWED_ORIGINS == [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    finally:
        sys.modules.pop(DEVELOPMENT_SETTINGS_MODULE, None)


@pytest.mark.parametrize("missing_name", PRODUCTION_ENVIRONMENT)
def test_production_settings_fail_when_required_value_is_missing(
    monkeypatch,
    missing_name,
) -> None:
    set_production_environment(monkeypatch)
    monkeypatch.delenv(missing_name)
    sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)

    try:
        with pytest.raises(
            ImproperlyConfigured,
            match=missing_name,
        ):
            importlib.import_module(PRODUCTION_SETTINGS_MODULE)
    finally:
        sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)


def test_production_settings_require_https_and_postgresql(monkeypatch) -> None:
    set_production_environment(monkeypatch)
    monkeypatch.setenv("KV_CORS_ALLOWED_ORIGINS", "https://app.example.com")
    sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)

    try:
        production = importlib.import_module(PRODUCTION_SETTINGS_MODULE)

        assert production.DEBUG is False
        assert production.SECURE_SSL_REDIRECT is True
        assert production.SESSION_COOKIE_SECURE is True
        assert production.CSRF_COOKIE_SECURE is True
        assert production.DATABASES["default"]["ENGINE"] == ("django.db.backends.postgresql")
        assert production.REDIS_URL == "redis://redis:6379/0"
        assert production.CELERY_BROKER_URL == "redis://redis:6379/1"
        assert production.CORS_ALLOWED_ORIGINS == ["https://app.example.com"]
    finally:
        sys.modules.pop(PRODUCTION_SETTINGS_MODULE, None)


def test_rest_api_defaults_are_secure_and_versioned() -> None:
    api_settings = settings.REST_FRAMEWORK

    assert api_settings["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]
    assert api_settings["DEFAULT_RENDERER_CLASSES"] == ["rest_framework.renderers.JSONRenderer"]
    assert api_settings["DEFAULT_PAGINATION_CLASS"] == (
        "config.api.pagination.DefaultPageNumberPagination"
    )
    assert settings.SPECTACULAR_SETTINGS["SCHEMA_PATH_PREFIX"] == r"/api/v1"
    assert settings.CORS_ALLOW_CREDENTIALS is True
    assert settings.MIDDLEWARE.index("corsheaders.middleware.CorsMiddleware") < (
        settings.MIDDLEWARE.index("django.middleware.common.CommonMiddleware")
    )
