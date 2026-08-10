import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.exceptions import InvalidRefreshToken
from apps.accounts.models import User
from apps.accounts.services import issue_token_pair, rotate_refresh_token

PASSWORD = "Secure-Authentication-Password-731!"


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
        email="person@example.com",
        full_name="Example Person",
        password=PASSWORD,
    )


def csrf_token(client: APIClient) -> str:
    response = client.get(reverse("accounts:csrf"))
    assert response.status_code == 200
    return response.json()["csrf_token"]


def login(client: APIClient, user: User) -> tuple:
    token = csrf_token(client)
    response = client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200, response.json()
    return response, response.json()["csrf_token"]


def test_csrf_endpoint_sets_httponly_cookie(api_client) -> None:
    response = api_client.get(reverse("accounts:csrf"))

    assert response.status_code == 200
    assert response.json()["csrf_token"]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    cookie = response.cookies[settings.CSRF_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"


@pytest.mark.django_db
def test_login_requires_csrf(api_client, user) -> None:
    response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"
    assert settings.AUTH_REFRESH_COOKIE_NAME not in response.cookies
    assert OutstandingToken.objects.count() == 0


@pytest.mark.django_db
def test_login_returns_access_token_and_secure_refresh_cookie(api_client, user) -> None:
    response, returned_csrf = login(api_client, user)

    payload = response.json()
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == 300
    assert payload["csrf_token"] == returned_csrf
    assert payload["user"]["email"] == user.email
    assert "password" not in str(payload)
    assert "refresh" not in payload
    assert response.headers["Cache-Control"] == "no-store"

    access = AccessToken(payload["access"])
    assert uuid.UUID(str(access["user_id"])) == user.id
    refresh_cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    assert refresh_cookie.value
    assert refresh_cookie["httponly"] is True
    assert not refresh_cookie["secure"]
    assert refresh_cookie["samesite"] == "Lax"
    assert refresh_cookie["path"] == "/api/v1/auth/"
    assert OutstandingToken.objects.filter(user=user).count() == 1

    user.refresh_from_db()
    assert user.last_login is not None


@pytest.mark.django_db
def test_access_token_authenticates_protected_api(api_client, user) -> None:
    response, _csrf = login(api_client, user)

    protected = api_client.get(
        reverse("api-root"),
        HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}",
    )

    assert protected.status_code == 200
    assert protected.json() == {}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "password"),
    (
        ("person@example.com", "wrong-password"),
        ("missing@example.com", PASSWORD),
    ),
)
def test_login_uses_generic_invalid_credentials_error(
    api_client,
    user,
    email,
    password,
) -> None:
    token = csrf_token(api_client)

    response = api_client.post(
        reverse("accounts:login"),
        {"email": email, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.json()["error"]["message"] == "Invalid email or password."
    assert settings.AUTH_REFRESH_COOKIE_NAME not in response.cookies


@pytest.mark.django_db
def test_inactive_user_cannot_log_in(api_client, user) -> None:
    user.is_active = False
    user.save(update_fields=["is_active"])
    token = csrf_token(api_client)

    response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.django_db
def test_login_is_throttled_by_client_and_identity(api_client, user) -> None:
    token = csrf_token(api_client)

    for _ in range(5):
        response = api_client.post(
            reverse("accounts:login"),
            {"email": user.email, "password": "wrong-password"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 401

    response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "wrong-password"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "THROTTLED"


@pytest.mark.django_db
def test_refresh_rotates_and_blacklists_previous_token(api_client, user) -> None:
    login_response, token = login(api_client, user)
    old_refresh = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

    response = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 200, response.json()
    new_refresh = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
    assert new_refresh != old_refresh
    assert response.json()["access"]
    assert "refresh" not in response.json()
    assert OutstandingToken.objects.filter(user=user).count() == 2
    assert BlacklistedToken.objects.count() == 1

    api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = old_refresh
    reused = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=response.json()["csrf_token"],
    )
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.django_db
def test_refresh_rechecks_blacklist_after_locking_token(user) -> None:
    tokens = issue_token_pair(user)
    filtered = MagicMock()
    filtered.exists.side_effect = [False, True]

    with (
        patch(
            "rest_framework_simplejwt.tokens.BlacklistedToken.objects.filter",
            return_value=filtered,
        ),
        pytest.raises(InvalidRefreshToken) as exc_info,
    ):
        rotate_refresh_token(tokens.refresh)

    assert exc_info.value.default_code == "invalid_refresh_token"


@pytest.mark.django_db
def test_refresh_rejects_missing_or_invalid_cookie(api_client) -> None:
    token = csrf_token(api_client)

    missing = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"

    api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = "not-a-jwt"
    invalid = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.django_db
def test_refresh_rejects_inactive_user(api_client, user) -> None:
    _login_response, token = login(api_client, user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.django_db
def test_password_change_invalidates_existing_tokens(api_client, user) -> None:
    login_response, token = login(api_client, user)
    access = login_response.json()["access"]
    user.set_password("A-New-Secure-Password-945!")
    user.save(update_fields=["password"])

    protected = api_client.get(
        reverse("api-root"),
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )
    refresh = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert protected.status_code == 401
    assert refresh.status_code == 401
    assert refresh.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.django_db
def test_logout_revokes_refresh_token_and_clears_cookie(api_client, user) -> None:
    login_response, token = login(api_client, user)
    old_refresh = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

    response = api_client.post(
        reverse("accounts:logout"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 204
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"] == 0
    assert BlacklistedToken.objects.count() == 1

    api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = old_refresh
    refresh = api_client.post(
        reverse("accounts:refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(api_client),
    )
    assert refresh.status_code == 401


@pytest.mark.django_db
def test_logout_is_csrf_protected_and_idempotent(api_client) -> None:
    without_csrf = api_client.post(reverse("accounts:logout"), {}, format="json")
    assert without_csrf.status_code == 403

    response = api_client.post(
        reverse("accounts:logout"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(api_client),
    )
    assert response.status_code == 204
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"] == 0

    api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = "invalid-token"
    invalid_cookie = api_client.post(
        reverse("accounts:logout"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(api_client),
    )
    assert invalid_cookie.status_code == 204


@pytest.mark.django_db
def test_invalid_access_token_uses_safe_error_envelope(api_client) -> None:
    response = api_client.get(
        reverse("api-root"),
        HTTP_AUTHORIZATION="Bearer not-a-jwt",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_NOT_VALID"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
