import hashlib

from celery import shared_task

from .email_delivery import (
    dispatch_pending_deliveries,
    mark_delivery_sent,
    prepare_delivery,
    release_delivery_for_retry,
)
from .email_verification import send_email_verification_email
from .models import AccountEmailDelivery
from .password_reset import send_password_reset_email


@shared_task(bind=True, max_retries=3)
def deliver_account_email(self, delivery_id: str) -> bool:
    prepared = prepare_delivery(delivery_id)
    if prepared is None:
        return False
    delivery, user, token = prepared

    try:
        if delivery.purpose == AccountEmailDelivery.Purpose.EMAIL_VERIFICATION:
            send_email_verification_email(user=user, token=token)
        else:
            send_password_reset_email(user=user, token=token)
    except Exception as exc:
        release_delivery_for_retry(
            delivery_id=delivery.id,
            attempt_count=delivery.attempt_count,
        )
        raise self.retry(
            exc=exc,
            args=(str(delivery.id),),
            argsrepr=f"(<delivery {delivery.id}>,)",
            countdown=min(60 * (2**self.request.retries), 15 * 60),
        ) from exc
    return mark_delivery_sent(
        delivery_id=delivery.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
    )


@shared_task
def dispatch_pending_account_email_deliveries() -> int:
    return dispatch_pending_deliveries()
