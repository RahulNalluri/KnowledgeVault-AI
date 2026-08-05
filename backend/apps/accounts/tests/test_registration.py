from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.accounts.serializers import (
    DUPLICATE_EMAIL_MESSAGE,
    RegistrationSerializer,
)
from apps.accounts.services import AccountAlreadyExistsError, register_user

VALID_PASSWORD = "Secure-Vault-Registration-731!"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_registration_serializer_normalizes_and_creates_user() -> None:
    serializer = RegistrationSerializer(
        data={
            "email": "  PERSON@Example.COM  ",
            "full_name": "  Example Person  ",
            "password": VALID_PASSWORD,
        }
    )

    assert serializer.is_valid(), serializer.errors
    user = serializer.save()

    assert user.email == "person@example.com"
    assert user.full_name == "Example Person"
    assert user.check_password(VALID_PASSWORD)


@pytest.mark.django_db
def test_registration_serializer_rejects_case_insensitive_duplicate_email() -> None:
    User.objects.create_user(
        email="person@example.com",
        full_name="Existing Person",
        password=VALID_PASSWORD,
    )
    serializer = RegistrationSerializer(
        data={
            "email": "PERSON@example.com",
            "full_name": "Another Person",
            "password": VALID_PASSWORD,
        }
    )

    assert not serializer.is_valid()
    assert serializer.errors["email"] == [DUPLICATE_EMAIL_MESSAGE]


@pytest.mark.django_db
def test_registration_serializer_uses_django_password_validation() -> None:
    serializer = RegistrationSerializer(
        data={
            "email": "person@example.com",
            "full_name": "Example Person",
            "password": "password",
        }
    )

    assert not serializer.is_valid()
    assert "password" in serializer.errors
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_registration_serializer_rejects_oversized_password() -> None:
    serializer = RegistrationSerializer(
        data={
            "email": "person@example.com",
            "full_name": "Example Person",
            "password": "a" * 129,
        }
    )

    assert not serializer.is_valid()
    assert "password" in serializer.errors
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_registration_serializer_translates_duplicate_race() -> None:
    serializer = RegistrationSerializer(
        data={
            "email": "person@example.com",
            "full_name": "Example Person",
            "password": VALID_PASSWORD,
        }
    )
    assert serializer.is_valid(), serializer.errors

    with (
        patch(
            "apps.accounts.serializers.register_user",
            side_effect=AccountAlreadyExistsError,
        ),
        pytest.raises(ValidationError) as exc_info,
    ):
        serializer.save()

    assert exc_info.value.detail == {"email": [DUPLICATE_EMAIL_MESSAGE]}


@pytest.mark.django_db
def test_registration_service_translates_duplicate_integrity_race() -> None:
    User.objects.create_user(
        email="person@example.com",
        full_name="Existing Person",
        password=VALID_PASSWORD,
    )

    with (
        patch.object(User.objects, "create_user", side_effect=IntegrityError),
        pytest.raises(AccountAlreadyExistsError),
    ):
        register_user(
            email="person@example.com",
            full_name="Another Person",
            password=VALID_PASSWORD,
        )


@pytest.mark.django_db
def test_registration_service_does_not_hide_unrelated_integrity_errors() -> None:
    with (
        patch.object(User.objects, "create_user", side_effect=IntegrityError),
        pytest.raises(IntegrityError),
    ):
        register_user(
            email="person@example.com",
            full_name="Example Person",
            password=VALID_PASSWORD,
        )


@pytest.mark.django_db
def test_registration_endpoint_creates_account_without_exposing_password(client) -> None:
    response = client.post(
        reverse("accounts:register"),
        data={
            "email": "PERSON@example.com",
            "full_name": "Example Person",
            "password": VALID_PASSWORD,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json()) == {
        "id",
        "email",
        "full_name",
        "is_email_verified",
        "created_at",
    }
    assert response.json()["email"] == "person@example.com"
    assert response.json()["is_email_verified"] is False
    assert "password" not in response.content.decode()
    assert User.objects.get().check_password(VALID_PASSWORD)


@pytest.mark.django_db
def test_registration_endpoint_returns_consistent_validation_error(client) -> None:
    response = client.post(
        reverse("accounts:register"),
        data={
            "email": "not-an-email",
            "full_name": "",
            "password": "123",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Request validation failed."
    assert set(error["details"]) == {"email", "full_name", "password"}
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_registration_endpoint_rejects_unsupported_method(client) -> None:
    response = client.get(reverse("accounts:register"))

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


@pytest.mark.django_db
def test_registration_endpoint_has_strict_scoped_throttle(client) -> None:
    url = reverse("accounts:register")

    for _ in range(5):
        response = client.post(url, data={}, content_type="application/json")
        assert response.status_code == 400

    response = client.post(url, data={}, content_type="application/json")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "THROTTLED"
