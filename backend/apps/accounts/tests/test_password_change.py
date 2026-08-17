from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.accounts.models import User
from apps.accounts.services import (
    IncorrectCurrentPasswordError,
    change_user_password,
    issue_token_pair,
)

CURRENT_PASSWORD = "Secure-Current-Password-731!"
NEW_PASSWORD = "Secure-Replacement-Password-947!"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="password-change@example.com",
        full_name="Password Change User",
        password=CURRENT_PASSWORD,
    )


def password_payload(**overrides) -> dict:
    payload = {
        "current_password": CURRENT_PASSWORD,
        "new_password": NEW_PASSWORD,
        "new_password_confirmation": NEW_PASSWORD,
    }
    payload.update(overrides)
    return payload


def authorize(client: APIClient, access_token: str) -> None:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")


@pytest.mark.django_db
def test_password_change_requires_authentication(api_client) -> None:
    response = api_client.post(
        reverse("accounts:password-change"),
        password_payload(),
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db
def test_password_change_updates_password_and_revokes_all_tokens(api_client, user) -> None:
    first_tokens = issue_token_pair(user)
    second_tokens = issue_token_pair(user)
    authorize(api_client, first_tokens.access)
    api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = first_tokens.refresh

    response = api_client.post(
        reverse("accounts:password-change"),
        password_payload(),
        format="json",
    )

    assert response.status_code == 204
    assert not response.content
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"] == 0
    assert OutstandingToken.objects.filter(user=user).count() == 2
    assert BlacklistedToken.objects.filter(token__user=user).count() == 2

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(CURRENT_PASSWORD)

    old_access = api_client.get(
        reverse("users:me"),
        HTTP_AUTHORIZATION=f"Bearer {second_tokens.access}",
    )
    assert old_access.status_code == 401
    assert old_access.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    csrf_response = api_client.get(reverse("accounts:csrf"))
    api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = second_tokens.refresh
    old_refresh = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.json()["csrf_token"],
    )
    assert old_refresh.status_code == 401
    assert old_refresh.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.django_db
def test_password_change_rejects_incorrect_current_password(api_client, user) -> None:
    tokens = issue_token_pair(user)
    authorize(api_client, tokens.access)

    response = api_client.post(
        reverse("accounts:password-change"),
        password_payload(current_password="Incorrect-Current-Password-842!"),
        format="json",
    )

    assert response.status_code == 400
    assert "current_password" in response.json()["error"]["details"]
    user.refresh_from_db()
    assert user.check_password(CURRENT_PASSWORD)
    assert BlacklistedToken.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "error_field"),
    (
        ({"new_password_confirmation": "Different-Password-538!"}, "new_password_confirmation"),
        (
            {
                "new_password": CURRENT_PASSWORD,
                "new_password_confirmation": CURRENT_PASSWORD,
            },
            "new_password",
        ),
        (
            {"new_password": "password", "new_password_confirmation": "password"},
            "new_password",
        ),
        (
            {"new_password": "x" * 129, "new_password_confirmation": "x" * 129},
            "new_password",
        ),
    ),
)
def test_password_change_validates_new_password(
    api_client,
    user,
    overrides,
    error_field,
) -> None:
    tokens = issue_token_pair(user)
    authorize(api_client, tokens.access)

    response = api_client.post(
        reverse("accounts:password-change"),
        password_payload(**overrides),
        format="json",
    )

    assert response.status_code == 400
    assert error_field in response.json()["error"]["details"]
    user.refresh_from_db()
    assert user.check_password(CURRENT_PASSWORD)


@pytest.mark.django_db
def test_password_change_rechecks_current_password_inside_transaction(api_client, user) -> None:
    tokens = issue_token_pair(user)
    authorize(api_client, tokens.access)

    with patch(
        "apps.accounts.serializers.change_user_password",
        side_effect=IncorrectCurrentPasswordError,
    ):
        response = api_client.post(
            reverse("accounts:password-change"),
            password_payload(),
            format="json",
        )

    assert response.status_code == 400
    assert "current_password" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_password_change_service_rejects_stale_current_password(user) -> None:
    with pytest.raises(IncorrectCurrentPasswordError):
        change_user_password(
            user=user,
            current_password="Incorrect-Current-Password-842!",
            new_password=NEW_PASSWORD,
        )

    user.refresh_from_db()
    assert user.check_password(CURRENT_PASSWORD)


@pytest.mark.django_db
def test_password_change_rejects_inactive_user(api_client, user) -> None:
    tokens = issue_token_pair(user)
    user.is_active = False
    user.save(update_fields=["is_active"])
    authorize(api_client, tokens.access)

    response = api_client.post(
        reverse("accounts:password-change"),
        password_payload(),
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.django_db
def test_password_change_is_rate_limited(api_client, user) -> None:
    tokens = issue_token_pair(user)
    authorize(api_client, tokens.access)
    payload = password_payload(current_password="Incorrect-Current-Password-842!")

    for _ in range(5):
        response = api_client.post(
            reverse("accounts:password-change"),
            payload,
            format="json",
        )
        assert response.status_code == 400

    throttled = api_client.post(
        reverse("accounts:password-change"),
        payload,
        format="json",
    )

    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "THROTTLED"
