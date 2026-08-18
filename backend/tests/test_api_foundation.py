import uuid

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from config.api.pagination import DefaultPageNumberPagination


def test_request_id_is_generated_and_returned(client) -> None:
    response = client.get(reverse("health:live"))

    uuid.UUID(response.headers["X-Request-ID"])


def test_valid_request_id_is_preserved(client) -> None:
    request_id = str(uuid.uuid4())

    response = client.get(reverse("health:live"), headers={"X-Request-ID": request_id})

    assert response.headers["X-Request-ID"] == request_id


def test_invalid_request_id_is_replaced(client) -> None:
    response = client.get(
        reverse("health:live"),
        headers={"X-Request-ID": "not-a-uuid"},
    )

    assert response.headers["X-Request-ID"] != "not-a-uuid"
    uuid.UUID(response.headers["X-Request-ID"])


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:3000"])
def test_api_preflight_allows_configured_frontend(client) -> None:
    response = client.options(
        reverse("health:live"),
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


@pytest.mark.django_db
def test_api_root_requires_authentication(client, django_user_model) -> None:
    response = client.get(reverse("api-root"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"

    user = django_user_model.objects.create_user(
        email="member@example.com",
        full_name="Example Member",
        password="a-secure-test-password",
    )
    client.force_login(user)

    response = client.get(reverse("api-root"))

    assert response.status_code == 200
    assert response.json() == {}


def test_openapi_schema_includes_health_endpoints(client) -> None:
    response = client.get(reverse("api-schema"), {"format": "json"})

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "KnowledgeVault AI API"
    assert "/api/v1/health/live/" in schema["paths"]
    assert "/api/v1/health/ready/" in schema["paths"]
    registration = schema["paths"]["/api/v1/auth/register/"]["post"]
    assert registration["tags"] == ["Authentication"]
    assert "security" not in registration
    for path, method in (
        ("/api/v1/auth/csrf/", "get"),
        ("/api/v1/auth/login/", "post"),
        ("/api/v1/auth/refresh/", "post"),
        ("/api/v1/auth/logout/", "post"),
    ):
        operation = schema["paths"][path][method]
        assert operation["tags"] == ["Authentication"]
        assert "security" not in operation

    profile = schema["paths"]["/api/v1/users/me/"]
    assert profile["get"]["tags"] == ["Users"]
    assert profile["patch"]["tags"] == ["Users"]
    assert profile["get"]["security"]
    assert profile["patch"]["security"]

    password_change = schema["paths"]["/api/v1/auth/password/change/"]["post"]
    assert password_change["tags"] == ["Authentication"]
    assert password_change["security"]

    verification_confirm = schema["paths"]["/api/v1/auth/email/verification/confirm/"]["post"]
    verification_resend = schema["paths"]["/api/v1/auth/email/verification/resend/"]["post"]
    assert verification_confirm["tags"] == ["Authentication"]
    assert "security" not in verification_confirm
    assert verification_resend["tags"] == ["Authentication"]
    assert verification_resend["security"]

    password_reset_request = schema["paths"]["/api/v1/auth/password/reset/request/"]["post"]
    password_reset_confirm = schema["paths"]["/api/v1/auth/password/reset/confirm/"]["post"]
    assert password_reset_request["tags"] == ["Authentication"]
    assert "security" not in password_reset_request
    assert password_reset_confirm["tags"] == ["Authentication"]
    assert "security" not in password_reset_confirm


def test_api_documentation_is_public(client) -> None:
    response = client.get(reverse("api-docs"))

    assert response.status_code == 200
    assert b"swagger-ui" in response.content


def test_default_pagination_has_bounded_client_page_size() -> None:
    factory = APIRequestFactory()
    request = Request(factory.get("/", {"page_size": 500}))
    paginator = DefaultPageNumberPagination()

    page = paginator.paginate_queryset(list(range(150)), request)
    response = paginator.get_paginated_response(page)

    assert isinstance(paginator, PageNumberPagination)
    assert len(page) == 100
    assert response.data["count"] == 150
