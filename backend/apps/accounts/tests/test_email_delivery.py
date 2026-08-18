from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.email_delivery import (
    DISPATCH_LEASE,
    dispatch_pending_deliveries,
    queue_password_reset,
)
from apps.accounts.email_verification import issue_email_verification_token
from apps.accounts.models import AccountEmailDelivery, EmailVerificationToken, User
from apps.accounts.tasks import (
    deliver_account_email,
    dispatch_pending_account_email_deliveries,
)

PASSWORD = "Durable-Email-Password-731!"


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="durable@example.com",
        full_name="Durable Email User",
        password=PASSWORD,
    )


@pytest.mark.django_db(transaction=True)
def test_broker_failure_leaves_durable_pending_row_without_a_raw_token(user, caplog) -> None:
    with patch(
        "apps.accounts.tasks.deliver_account_email.apply_async",
        side_effect=RuntimeError("broker unavailable"),
    ):
        queue_password_reset(email=user.email)

    delivery = AccountEmailDelivery.objects.get()
    assert delivery.status == AccountEmailDelivery.Status.PENDING
    assert delivery.dispatched_at is None
    assert delivery.token_hash == ""
    assert not EmailVerificationToken.objects.exists()
    assert "Account email delivery dispatch failed" in caplog.text
    assert user.email not in caplog.text


@pytest.mark.django_db
def test_periodic_dispatch_selects_ready_and_stale_rows_only() -> None:
    now = timezone.now()
    ready = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email="ready@example.com",
    )
    stale = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email="stale@example.com",
        dispatched_at=now - DISPATCH_LEASE - timedelta(seconds=1),
    )
    abandoned = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email="abandoned@example.com",
        status=AccountEmailDelivery.Status.SENDING,
        started_at=now - timedelta(minutes=11),
    )
    AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email="recent@example.com",
        dispatched_at=now,
    )
    AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email="future@example.com",
        available_at=now + timedelta(minutes=1),
    )

    with patch("apps.accounts.tasks.deliver_account_email.apply_async") as apply_async:
        dispatched = dispatch_pending_deliveries()

    assert dispatched == 3
    assert {call.kwargs["args"][0] for call in apply_async.call_args_list} == {
        str(ready.id),
        str(stale.id),
        str(abandoned.id),
    }
    ready.refresh_from_db()
    stale.refresh_from_db()
    assert ready.dispatched_at is not None
    assert stale.dispatched_at is not None


@pytest.mark.django_db
def test_periodic_task_delegates_to_dispatcher() -> None:
    with patch(
        "apps.accounts.tasks.dispatch_pending_deliveries",
        return_value=7,
    ) as dispatcher:
        result = dispatch_pending_account_email_deliveries.apply().get()

    assert result == 7
    dispatcher.assert_called_once_with()


@pytest.mark.django_db(transaction=True)
def test_duplicate_task_is_no_op_after_delivery_is_sent(user) -> None:
    delivery = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email=user.email,
    )

    assert deliver_account_email.apply(args=[str(delivery.id)]).get() is True
    assert deliver_account_email.apply(args=[str(delivery.id)]).get() is False
    assert len(mail.outbox) == 1


@pytest.mark.django_db(transaction=True)
def test_active_delivery_lease_prevents_concurrent_duplicate_send(user) -> None:
    delivery = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email=user.email,
        status=AccountEmailDelivery.Status.SENDING,
        started_at=timezone.now(),
    )

    assert deliver_account_email.apply(args=[str(delivery.id)]).get() is False
    assert not mail.outbox


@pytest.mark.django_db(transaction=True)
def test_stale_delivery_lease_reissues_token_and_completes(user) -> None:
    old_raw_token = issue_email_verification_token(user=user)
    old_token = EmailVerificationToken.objects.get()
    delivery = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.EMAIL_VERIFICATION,
        recipient_email=user.email,
        user=user,
        status=AccountEmailDelivery.Status.SENDING,
        started_at=timezone.now() - timedelta(minutes=11),
        token_hash=old_token.token_hash,
    )

    assert deliver_account_email.apply(args=[str(delivery.id)]).get() is True

    delivery.refresh_from_db()
    old_token.refresh_from_db()
    assert delivery.status == AccountEmailDelivery.Status.SENT
    assert delivery.token_hash != old_token.token_hash
    assert old_token.used_at is not None
    assert old_raw_token not in mail.outbox[0].body
