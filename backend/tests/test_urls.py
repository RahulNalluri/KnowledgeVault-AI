from django.urls import resolve, reverse

from apps.health.views import liveness, readiness


def test_health_route_contracts_are_stable() -> None:
    assert reverse("health:live") == "/api/v1/health/live/"
    assert reverse("health:ready") == "/api/v1/health/ready/"
    assert resolve("/api/v1/health/live/").func is liveness
    assert resolve("/api/v1/health/ready/").func is readiness


def test_api_foundation_route_contracts_are_stable() -> None:
    assert reverse("api-schema") == "/api/v1/schema/"
    assert reverse("api-docs") == "/api/v1/docs/"
    assert reverse("api-root") == "/api/v1/"
    assert reverse("accounts:register") == "/api/v1/auth/register/"
    assert reverse("accounts:csrf") == "/api/v1/auth/csrf/"
    assert reverse("accounts:login") == "/api/v1/auth/login/"
    assert reverse("accounts:refresh") == "/api/v1/auth/refresh/"
    assert reverse("accounts:logout") == "/api/v1/auth/logout/"
    assert reverse("accounts:password-change") == "/api/v1/auth/password/change/"
    assert reverse("users:me") == "/api/v1/users/me/"
