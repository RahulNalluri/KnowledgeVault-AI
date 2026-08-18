import hashlib
import logging
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .email_verification import issue_email_verification_token
from .models import (
    AccountEmailDelivery,
    EmailVerificationToken,
    PasswordResetToken,
    User,
)
from .password_reset import issue_password_reset_token

logger = logging.getLogger(__name__)

DELIVERY_LEASE = timedelta(minutes=10)
DISPATCH_LEASE = timedelta(minutes=5)
MAX_RETRY_DELAY = timedelta(hours=1)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _request_dispatch(delivery_id: UUID) -> bool:
    from .tasks import deliver_account_email

    try:
        deliver_account_email.apply_async(
            args=[str(delivery_id)],
            argsrepr=f"(<delivery {delivery_id}>,)",
        )
    except Exception:
        logger.exception(
            "Account email delivery dispatch failed",
            extra={"delivery_id": str(delivery_id)},
        )
        return False

    AccountEmailDelivery.objects.filter(
        pk=delivery_id,
        status=AccountEmailDelivery.Status.PENDING,
    ).update(dispatched_at=timezone.now())
    return True


def _dispatch_after_commit(delivery_id: UUID) -> None:
    transaction.on_commit(lambda: _request_dispatch(delivery_id))


@transaction.atomic
def queue_email_verification(*, user: User) -> bool:
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if not locked_user.is_active or locked_user.is_email_verified:
        return False

    delivery = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.EMAIL_VERIFICATION,
        recipient_email=locked_user.email,
        user=locked_user,
    )
    _dispatch_after_commit(delivery.id)
    return True


@transaction.atomic
def queue_password_reset(*, email: str) -> None:
    delivery = AccountEmailDelivery.objects.create(
        purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
        recipient_email=email,
    )
    _dispatch_after_commit(delivery.id)


def dispatch_pending_deliveries(*, limit: int = 100) -> int:
    now = timezone.now()
    stale_dispatch = now - DISPATCH_LEASE
    stale_delivery = now - DELIVERY_LEASE
    delivery_ids = list(
        AccountEmailDelivery.objects.filter(
            Q(
                status=AccountEmailDelivery.Status.PENDING,
                available_at__lte=now,
            )
            & (Q(dispatched_at__isnull=True) | Q(dispatched_at__lte=stale_dispatch))
            | Q(
                status=AccountEmailDelivery.Status.SENDING,
                started_at__lte=stale_delivery,
            )
        )
        .order_by("available_at", "created_at")
        .values_list("id", flat=True)[:limit]
    )
    return sum(_request_dispatch(delivery_id) for delivery_id in delivery_ids)


def _eligible_user(delivery: AccountEmailDelivery) -> User | None:
    if delivery.purpose == AccountEmailDelivery.Purpose.EMAIL_VERIFICATION:
        return (
            User.objects.select_for_update()
            .filter(
                pk=delivery.user_id,
                email=delivery.recipient_email,
                is_active=True,
                is_email_verified=False,
            )
            .first()
        )
    return (
        User.objects.select_for_update()
        .filter(email__iexact=delivery.recipient_email, is_active=True)
        .first()
    )


def _invalidate_previous_attempt(delivery: AccountEmailDelivery) -> None:
    if not delivery.token_hash:
        return
    token_model = (
        EmailVerificationToken
        if delivery.purpose == AccountEmailDelivery.Purpose.EMAIL_VERIFICATION
        else PasswordResetToken
    )
    token_model.objects.filter(
        token_hash=delivery.token_hash,
        used_at__isnull=True,
    ).update(used_at=timezone.now())


@transaction.atomic
def prepare_delivery(delivery_id: UUID | str) -> tuple[AccountEmailDelivery, User, str] | None:
    now = timezone.now()
    delivery = AccountEmailDelivery.objects.select_for_update().filter(pk=delivery_id).first()
    if delivery is None or delivery.status in {
        AccountEmailDelivery.Status.SENT,
        AccountEmailDelivery.Status.CANCELLED,
    }:
        return None
    if (
        delivery.status == AccountEmailDelivery.Status.SENDING
        and delivery.started_at
        and delivery.started_at > now - DELIVERY_LEASE
    ):
        return None

    user = _eligible_user(delivery)
    if user is None:
        delivery.status = AccountEmailDelivery.Status.CANCELLED
        delivery.started_at = None
        delivery.last_error_code = "RECIPIENT_NOT_ELIGIBLE"
        delivery.save(update_fields=["status", "started_at", "last_error_code", "updated_at"])
        return None

    _invalidate_previous_attempt(delivery)
    if delivery.purpose == AccountEmailDelivery.Purpose.EMAIL_VERIFICATION:
        token = issue_email_verification_token(user=user)
    else:
        token = issue_password_reset_token(user=user)
    if token is None:
        delivery.status = AccountEmailDelivery.Status.CANCELLED
        delivery.started_at = None
        delivery.last_error_code = "RECIPIENT_NOT_ELIGIBLE"
        delivery.save(update_fields=["status", "started_at", "last_error_code", "updated_at"])
        return None

    delivery.status = AccountEmailDelivery.Status.SENDING
    delivery.attempt_count = F("attempt_count") + 1
    delivery.started_at = now
    delivery.dispatched_at = now
    delivery.token_hash = _token_hash(token)
    delivery.last_error_code = ""
    delivery.save(
        update_fields=[
            "status",
            "attempt_count",
            "started_at",
            "dispatched_at",
            "token_hash",
            "last_error_code",
            "updated_at",
        ]
    )
    delivery.refresh_from_db(fields=["attempt_count"])
    return delivery, user, token


@transaction.atomic
def mark_delivery_sent(*, delivery_id: UUID | str, token_hash: str) -> bool:
    return bool(
        AccountEmailDelivery.objects.filter(
            pk=delivery_id,
            status=AccountEmailDelivery.Status.SENDING,
            token_hash=token_hash,
        ).update(
            status=AccountEmailDelivery.Status.SENT,
            sent_at=timezone.now(),
            started_at=None,
            last_error_code="",
        )
    )


@transaction.atomic
def release_delivery_for_retry(*, delivery_id: UUID | str, attempt_count: int) -> None:
    delay_seconds = min(60 * (2 ** max(attempt_count - 1, 0)), MAX_RETRY_DELAY.seconds)
    AccountEmailDelivery.objects.filter(
        pk=delivery_id,
        status=AccountEmailDelivery.Status.SENDING,
    ).update(
        status=AccountEmailDelivery.Status.PENDING,
        available_at=timezone.now() + timedelta(seconds=delay_seconds),
        dispatched_at=None,
        started_at=None,
        last_error_code="EMAIL_BACKEND_ERROR",
    )
