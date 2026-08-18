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
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.accounts.models import AccountEmailDelivery, PasswordResetToken, User
from apps.accounts.password_reset import (
    InvalidPasswordResetTokenError,
    issue_password_reset_token,
    reset_password,
)
from apps.accounts.services import issue_token_pair
from apps.accounts.tasks import deliver_account_email

CURRENT_PASSWORD = "Secure-Current-Recovery-Password-731!"
NEW_PASSWORD = "Secure-Recovered-Password-947!"
GENERIC_MESSAGE = "If an active account exists, a password reset link has been sent."


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="reset@example.com",
        full_name="Reset User",
        password=CURRENT_PASSWORD,
    )


def token_from_email(index: int = -1) -> str:
    reset_url = mail.outbox[index].body.splitlines()[2]
    return parse_qs(urlparse(reset_url).query)["token"][0]


def reset_payload(token: str, **overrides) -> dict:
    payload = {
        "token": token,
        "new_password": NEW_PASSWORD,
        "new_password_confirmation": NEW_PASSWORD,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db(transaction=True)
def test_reset_request_is_enumeration_safe_and_stores_only_token_hash(client, user) -> None:
    existing = client.post(
        reverse("accounts:password-reset-request"),
        data={"email": "  RESET@Example.COM  "},
        content_type="application/json",
    )
    missing = client.post(
        reverse("accounts:password-reset-request"),
        data={"email": "missing@example.com"},
        content_type="application/json",
        REMOTE_ADDR="192.0.2.2",
    )

    assert existing.status_code == 202
    assert missing.status_code == 202
    assert existing.json() == missing.json() == {"message": GENERIC_MESSAGE}
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    raw_token = token_from_email()
    reset_token = PasswordResetToken.objects.get()
    assert reset_token.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert raw_token not in reset_token.token_hash
    assert reset_token.expires_at > timezone.now() + timedelta(minutes=59)
    sent_delivery = AccountEmailDelivery.objects.get(recipient_email=user.email)
    assert sent_delivery.status == AccountEmailDelivery.Status.SENT
    missing_delivery = AccountEmailDelivery.objects.get(recipient_email="missing@example.com")
    assert missing_delivery.status == AccountEmailDelivery.Status.CANCELLED


@pytest.mark.django_db(transaction=True)
def test_reset_request_is_no_op_for_inactive_user(client, user) -> None:
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.post(
        reverse("accounts:password-reset-request"),
        data={"email": user.email},
        content_type="application/json",
    )

    assert response.status_code == 202
    assert response.json() == {"message": GENERIC_MESSAGE}
    assert not mail.outbox
    assert not PasswordResetToken.objects.exists()
    assert AccountEmailDelivery.objects.get().status == AccountEmailDelivery.Status.CANCELLED


@pytest.mark.django_db(transaction=True)
def test_reset_request_survives_email_dispatch_failure(client, user, caplog) -> None:
    with patch(
        "apps.accounts.password_reset.send_mail",
        side_effect=RuntimeError("SMTP unavailable"),
    ):
        response = client.post(
            reverse("accounts:password-reset-request"),
            data={"email": user.email},
            content_type="application/json",
        )

    assert response.status_code == 202
    assert response.json() == {"message": GENERIC_MESSAGE}
    assert PasswordResetToken.objects.filter(user=user).count() == 1
    delivery = AccountEmailDelivery.objects.get()
    assert delivery.status == AccountEmailDelivery.Status.PENDING
    assert delivery.last_error_code == "EMAIL_BACKEND_ERROR"
    assert "Account email delivery dispatch failed" in caplog.text


@pytest.mark.django_db(transaction=True)
def test_reset_task_handles_token_issue_no_op(user) -> None:
    delivery = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email=user.email,
    )
    with patch(
        "apps.accounts.email_delivery.issue_password_reset_token",
        return_value=None,
    ):
        result = deliver_account_email.apply(args=[str(delivery.id)]).get()

    assert result is False
    assert not mail.outbox
    delivery.refresh_from_db()
    assert delivery.status == AccountEmailDelivery.Status.CANCELLED


@pytest.mark.django_db(transaction=True)
def test_reset_task_replaces_an_invalidated_retry_token(user) -> None:
    token = issue_password_reset_token(user=user)
    old_token = PasswordResetToken.objects.get()
    delivery = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email=user.email,
        token_hash=old_token.token_hash,
    )

    result = deliver_account_email.apply(args=[str(delivery.id)]).get()

    assert result is True
    assert len(mail.outbox) == 1
    assert token_from_email() != token
    old_token.refresh_from_db()
    assert old_token.used_at is not None


@pytest.mark.django_db
def test_reset_request_rejects_invalid_email(client) -> None:
    response = client.post(
        reverse("accounts:password-reset-request"),
        data={"email": "not-an-email"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "email" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_new_reset_token_removes_expired_records(user) -> None:
    expired_raw_token = issue_password_reset_token(user=user)
    expired = PasswordResetToken.objects.get()
    expired.expires_at = timezone.now() - timedelta(seconds=1)
    expired.save(update_fields=["expires_at"])

    replacement = issue_password_reset_token(user=user)

    assert replacement != expired_raw_token
    assert not PasswordResetToken.objects.filter(pk=expired.pk).exists()
    assert PasswordResetToken.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_issue_reset_token_is_no_op_for_inactive_user(user) -> None:
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert issue_password_reset_token(user=user) is None
    assert not PasswordResetToken.objects.exists()


@pytest.mark.django_db
def test_reset_changes_password_consumes_tokens_and_revokes_jwts(client, user) -> None:
    first_reset_token = issue_password_reset_token(user=user)
    issue_password_reset_token(user=user)
    first_jwt = issue_token_pair(user)
    second_jwt = issue_token_pair(user)

    response = client.post(
        reverse("accounts:password-reset-confirm"),
        data=reset_payload(first_reset_token),
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    assert response.headers["Cache-Control"] == "no-store"
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"] == 0
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(CURRENT_PASSWORD)
    assert PasswordResetToken.objects.filter(user=user, used_at__isnull=False).count() == 2
    assert BlacklistedToken.objects.filter(token__user=user).count() == 2

    old_access = client.get(
        reverse("users:me"),
        HTTP_AUTHORIZATION=f"Bearer {second_jwt.access}",
    )
    assert old_access.status_code == 401

    reused = client.post(
        reverse("accounts:password-reset-confirm"),
        data=reset_payload(first_reset_token),
        content_type="application/json",
    )
    assert reused.status_code == 400
    assert "token" in reused.json()["error"]["details"]
    assert first_jwt.refresh != second_jwt.refresh


@pytest.mark.django_db
def test_reset_rejects_expired_token(client, user) -> None:
    token = issue_password_reset_token(user=user)
    PasswordResetToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

    response = client.post(
        reverse("accounts:password-reset-confirm"),
        data=reset_payload(token),
        content_type="application/json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password(CURRENT_PASSWORD)


@pytest.mark.django_db
def test_reset_rejects_inactive_user_token(client, user) -> None:
    token = issue_password_reset_token(user=user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.post(
        reverse("accounts:password-reset-confirm"),
        data=reset_payload(token),
        content_type="application/json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("token", ("too-short", "x" * 43))
def test_reset_rejects_malformed_or_unknown_token(client, token) -> None:
    response = client.post(
        reverse("accounts:password-reset-confirm"),
        data=reset_payload(token),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "token" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_reset_service_rejects_unknown_token() -> None:
    with pytest.raises(InvalidPasswordResetTokenError):
        reset_password(
            token="unknown-token-that-is-long-enough-for-service",
            new_password=NEW_PASSWORD,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "error_field"),
    (
        (
            {"new_password_confirmation": "Different-Recovered-Password-842!"},
            "new_password_confirmation",
        ),
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
        (
            {
                "new_password": "reset@example.com",
                "new_password_confirmation": "reset@example.com",
            },
            "new_password",
        ),
    ),
)
def test_reset_validates_replacement_password(client, user, overrides, error_field) -> None:
    token = issue_password_reset_token(user=user)

    response = client.post(
        reverse("accounts:password-reset-confirm"),
        data=reset_payload(token, **overrides),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert error_field in response.json()["error"]["details"]
    user.refresh_from_db()
    assert user.check_password(CURRENT_PASSWORD)
    assert PasswordResetToken.objects.get().used_at is None


@pytest.mark.django_db(transaction=True)
def test_reset_request_identity_throttle_applies_across_client_addresses(client) -> None:
    url = reverse("accounts:password-reset-request")
    payload = {"email": "same-target@example.com"}

    for index in range(3):
        response = client.post(
            url,
            data=payload,
            content_type="application/json",
            REMOTE_ADDR=f"192.0.2.{index + 1}",
        )
        assert response.status_code == 202

    throttled = client.post(
        url,
        data=payload,
        content_type="application/json",
        REMOTE_ADDR="192.0.2.99",
    )
    assert throttled.status_code == 429


@pytest.mark.django_db(transaction=True)
def test_reset_request_ip_throttle_limits_many_identities(client) -> None:
    url = reverse("accounts:password-reset-request")

    for index in range(10):
        response = client.post(
            url,
            data={"email": f"missing-{index}@example.com"},
            content_type="application/json",
        )
        assert response.status_code == 202

    throttled = client.post(
        url,
        data={"email": "missing-final@example.com"},
        content_type="application/json",
    )
    assert throttled.status_code == 429


@pytest.mark.django_db
def test_reset_confirmation_is_rate_limited(client) -> None:
    url = reverse("accounts:password-reset-confirm")
    payload = reset_payload("x" * 43)

    for _ in range(10):
        response = client.post(url, data=payload, content_type="application/json")
        assert response.status_code == 400

    throttled = client.post(url, data=payload, content_type="application/json")
    assert throttled.status_code == 429


@pytest.mark.django_db
def test_password_reset_token_has_safe_string_representation(user) -> None:
    issue_password_reset_token(user=user)
    reset_token = PasswordResetToken.objects.get()

    assert str(reset_token) == f"Password reset token for {user.id}"
