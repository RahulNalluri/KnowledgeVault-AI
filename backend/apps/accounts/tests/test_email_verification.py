import hashlib
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.email_delivery import queue_email_verification
from apps.accounts.email_verification import (
    InvalidEmailVerificationTokenError,
    confirm_email_verification,
    issue_email_verification_token,
)
from apps.accounts.models import AccountEmailDelivery, EmailVerificationToken, User
from apps.accounts.services import issue_token_pair

PASSWORD = "Secure-Verification-Password-731!"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="verify@example.com",
        full_name="Verification User",
        password=PASSWORD,
    )


def authorize(client: APIClient, user: User) -> None:
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")


def token_from_email(index: int = -1) -> str:
    verification_url = mail.outbox[index].body.splitlines()[2]
    return parse_qs(urlparse(verification_url).query)["token"][0]


@pytest.mark.django_db(transaction=True)
def test_registration_sends_verification_email_without_storing_raw_token(client) -> None:
    response = client.post(
        reverse("accounts:register"),
        data={
            "email": "new-user@example.com",
            "full_name": "New User",
            "password": PASSWORD,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new-user@example.com"]
    assert mail.outbox[0].from_email == settings.DEFAULT_FROM_EMAIL
    raw_token = token_from_email()
    verification = EmailVerificationToken.objects.get()
    assert verification.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert raw_token not in verification.token_hash
    assert verification.expires_at > timezone.now() + timedelta(hours=23)
    delivery = AccountEmailDelivery.objects.get()
    assert delivery.status == AccountEmailDelivery.Status.SENT
    assert delivery.token_hash == verification.token_hash
    assert delivery.sent_at is not None


@pytest.mark.django_db(transaction=True)
def test_registration_succeeds_when_email_delivery_fails(client, caplog) -> None:
    with patch(
        "apps.accounts.email_verification.send_mail",
        side_effect=RuntimeError("SMTP unavailable"),
    ):
        response = client.post(
            reverse("accounts:register"),
            data={
                "email": "delivery-failure@example.com",
                "full_name": "Delivery Failure",
                "password": PASSWORD,
            },
            content_type="application/json",
        )

    assert response.status_code == 201
    assert User.objects.filter(email="delivery-failure@example.com").exists()
    assert EmailVerificationToken.objects.count() == 1
    delivery = AccountEmailDelivery.objects.get()
    assert delivery.status == AccountEmailDelivery.Status.PENDING
    assert delivery.last_error_code == "EMAIL_BACKEND_ERROR"
    assert "Account email delivery dispatch failed" in caplog.text


@pytest.mark.django_db
def test_resend_requires_authentication(api_client) -> None:
    response = api_client.post(
        reverse("accounts:email-verification-resend"),
        {},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.django_db(transaction=True)
def test_resend_sends_only_to_authenticated_user(api_client, user) -> None:
    authorize(api_client, user)

    response = api_client.post(
        reverse("accounts:email-verification-resend"),
        {"email": "attacker-controlled@example.com"},
        format="json",
    )

    assert response.status_code == 202
    assert response.json() == {"message": "If verification is required, a new link has been sent."}
    assert mail.outbox[0].to == [user.email]
    assert EmailVerificationToken.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_resend_is_no_op_for_verified_user(api_client, user) -> None:
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    authorize(api_client, user)

    response = api_client.post(
        reverse("accounts:email-verification-resend"),
        {},
        format="json",
    )

    assert response.status_code == 202
    assert not mail.outbox
    assert not EmailVerificationToken.objects.exists()


@pytest.mark.django_db
def test_resend_is_no_op_for_inactive_user_service(user) -> None:
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert queue_email_verification(user=user) is False
    assert not mail.outbox
    assert not EmailVerificationToken.objects.exists()
    assert not AccountEmailDelivery.objects.exists()


@pytest.mark.django_db
def test_new_token_removes_expired_records(user) -> None:
    expired_raw_token = issue_email_verification_token(user=user)
    expired = EmailVerificationToken.objects.get()
    expired.expires_at = timezone.now() - timedelta(seconds=1)
    expired.save(update_fields=["expires_at"])

    replacement = issue_email_verification_token(user=user)

    assert replacement != expired_raw_token
    assert not EmailVerificationToken.objects.filter(pk=expired.pk).exists()
    assert EmailVerificationToken.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_confirm_verifies_user_and_consumes_all_active_tokens(client, user) -> None:
    first_token = issue_email_verification_token(user=user)
    issue_email_verification_token(user=user)

    response = client.post(
        reverse("accounts:email-verification-confirm"),
        data={"token": first_token},
        content_type="application/json",
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.is_email_verified is True
    assert EmailVerificationToken.objects.filter(user=user, used_at__isnull=False).count() == 2

    reused = client.post(
        reverse("accounts:email-verification-confirm"),
        data={"token": first_token},
        content_type="application/json",
    )
    assert reused.status_code == 400
    assert "token" in reused.json()["error"]["details"]


@pytest.mark.django_db
def test_confirm_rejects_expired_token(client, user) -> None:
    token = issue_email_verification_token(user=user)
    EmailVerificationToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

    response = client.post(
        reverse("accounts:email-verification-confirm"),
        data={"token": token},
        content_type="application/json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_email_verified is False


@pytest.mark.django_db
def test_confirm_rejects_inactive_user_token(client, user) -> None:
    token = issue_email_verification_token(user=user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.post(
        reverse("accounts:email-verification-confirm"),
        data={"token": token},
        content_type="application/json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_confirm_rejects_unused_token_for_already_verified_user(client, user) -> None:
    token = issue_email_verification_token(user=user)
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    response = client.post(
        reverse("accounts:email-verification-confirm"),
        data={"token": token},
        content_type="application/json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("token", ("too-short", "x" * 43))
def test_confirm_rejects_malformed_or_unknown_token(client, token) -> None:
    response = client.post(
        reverse("accounts:email-verification-confirm"),
        data={"token": token},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "token" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_confirmation_service_rejects_unknown_token() -> None:
    with pytest.raises(InvalidEmailVerificationTokenError):
        confirm_email_verification(token="unknown-token-that-is-long-enough-for-service")


@pytest.mark.django_db
def test_resend_is_rate_limited(api_client, user) -> None:
    authorize(api_client, user)
    url = reverse("accounts:email-verification-resend")

    for _ in range(3):
        response = api_client.post(url, {}, format="json")
        assert response.status_code == 202

    throttled = api_client.post(url, {}, format="json")
    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "THROTTLED"


@pytest.mark.django_db
def test_confirmation_is_rate_limited(client) -> None:
    url = reverse("accounts:email-verification-confirm")
    payload = {"token": "x" * 43}

    for _ in range(10):
        response = client.post(url, data=payload, content_type="application/json")
        assert response.status_code == 400

    throttled = client.post(url, data=payload, content_type="application/json")
    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "THROTTLED"


@pytest.mark.django_db
def test_verification_token_has_safe_string_representation(user) -> None:
    issue_email_verification_token(user=user)
    verification = EmailVerificationToken.objects.get()

    assert str(verification) == f"Email verification token for {user.id}"
