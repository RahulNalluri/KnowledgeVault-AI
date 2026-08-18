import logging

from celery import shared_task

from .models import User
from .password_reset import (
    issue_password_reset_token,
    password_reset_token_is_active,
    send_password_reset_email,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def deliver_password_reset_email(
    self,
    email: str,
    token: str | None = None,
) -> bool:
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return False

    if token is not None and not password_reset_token_is_active(user=user, token=token):
        return False
    token = token or issue_password_reset_token(user=user)
    if token is None:
        return False

    try:
        send_password_reset_email(user=user, token=token)
    except Exception as exc:
        raise self.retry(
            exc=exc,
            args=(email, token),
            argsrepr="(<redacted email>, <redacted token>)",
            countdown=min(60 * (2**self.request.retries), 15 * 60),
        ) from exc
    return True


def dispatch_password_reset_email(*, email: str) -> bool:
    try:
        deliver_password_reset_email.apply_async(
            args=[email],
            argsrepr="(<redacted email>,)",
        )
    except Exception:
        logger.exception("Password reset email dispatch failed")
        return False
    return True
