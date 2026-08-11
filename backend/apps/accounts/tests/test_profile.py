import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import issue_token_pair

PASSWORD = "Secure-Profile-Password-731!"


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="person@example.com",
        full_name="Example Person",
        password=PASSWORD,
    )


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def authenticate(client: APIClient, user: User) -> None:
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")


@pytest.mark.django_db
def test_profile_requires_authentication(api_client) -> None:
    response = api_client.get(reverse("users:me"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_profile_patch_requires_authentication(api_client) -> None:
    response = api_client.patch(
        reverse("users:me"),
        {"full_name": "Unauthorized Change"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_profile_returns_only_safe_current_user_fields(api_client, user) -> None:
    authenticate(api_client, user)

    response = api_client.get(reverse("users:me"))

    assert response.status_code == 200
    assert set(response.json()) == {
        "id",
        "email",
        "full_name",
        "avatar",
        "is_email_verified",
        "date_joined",
        "last_login",
        "created_at",
        "updated_at",
    }
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == user.email
    assert response.json()["avatar"] is None
    assert "password" not in response.content.decode()
    assert "is_staff" not in response.json()
    assert "is_superuser" not in response.json()


@pytest.mark.django_db
def test_profile_patch_updates_and_normalizes_full_name(api_client, user) -> None:
    authenticate(api_client, user)
    original_updated_at = user.updated_at

    response = api_client.patch(
        reverse("users:me"),
        {"full_name": "  Updated Person  "},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Person"
    user.refresh_from_db()
    assert user.full_name == "Updated Person"
    assert user.updated_at > original_updated_at
    assert response.json()["updated_at"] == user.updated_at.isoformat().replace("+00:00", "Z")


@pytest.mark.django_db
def test_empty_profile_patch_is_safe_no_op(api_client, user) -> None:
    authenticate(api_client, user)

    response = api_client.patch(reverse("users:me"), {}, format="json")

    assert response.status_code == 200
    assert response.json()["full_name"] == user.full_name


@pytest.mark.django_db
def test_profile_rejects_read_only_and_unknown_fields(api_client, user) -> None:
    authenticate(api_client, user)

    response = api_client.patch(
        reverse("users:me"),
        {
            "email": "changed@example.com",
            "avatar": "unsafe/path.png",
            "is_email_verified": True,
            "unknown": "value",
        },
        format="json",
    )

    assert response.status_code == 400
    assert set(response.json()["error"]["details"]) == {
        "avatar",
        "email",
        "is_email_verified",
        "unknown",
    }
    user.refresh_from_db()
    assert user.email == "person@example.com"
    assert user.is_email_verified is False
    assert not user.avatar


@pytest.mark.django_db
def test_profile_rejects_blank_name_and_non_object_payload(api_client, user) -> None:
    authenticate(api_client, user)

    blank = api_client.patch(
        reverse("users:me"),
        {"full_name": "   "},
        format="json",
    )
    non_object = api_client.patch(
        reverse("users:me"),
        ["not", "an", "object"],
        format="json",
    )

    assert blank.status_code == 400
    assert "full_name" in blank.json()["error"]["details"]
    assert non_object.status_code == 400


@pytest.mark.django_db
def test_profile_rejects_unsupported_methods(api_client, user) -> None:
    authenticate(api_client, user)

    put_response = api_client.put(
        reverse("users:me"),
        {"full_name": "Replacement"},
        format="json",
    )
    delete_response = api_client.delete(reverse("users:me"))

    assert put_response.status_code == 405
    assert delete_response.status_code == 405


@pytest.mark.django_db
def test_inactive_user_cannot_use_existing_profile_token(api_client, user) -> None:
    authenticate(api_client, user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = api_client.get(reverse("users:me"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.django_db
def test_inactive_user_cannot_patch_profile(api_client, user) -> None:
    authenticate(api_client, user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = api_client.patch(
        reverse("users:me"),
        {"full_name": "Blocked Change"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
    user.refresh_from_db()
    assert user.full_name == "Example Person"
