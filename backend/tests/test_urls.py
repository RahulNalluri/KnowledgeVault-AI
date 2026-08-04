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
