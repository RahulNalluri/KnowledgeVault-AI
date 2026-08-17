import hashlib
import logging
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailVerificationToken, User

logger = logging.getLogger(__name__)


class InvalidEmailVerificationTokenError(Exception):
    """Raised when a verification token cannot safely verify an account."""


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@transaction.atomic
def issue_email_verification_token(*, user: User) -> str | None:
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if not locked_user.is_active or locked_user.is_email_verified:
        return None

    now = timezone.now()
    EmailVerificationToken.objects.filter(
        user=locked_user,
        expires_at__lte=now,
    ).delete()

    token = secrets.token_urlsafe(32)
    EmailVerificationToken.objects.create(
        user=locked_user,
        token_hash=_token_hash(token),
        expires_at=now + settings.EMAIL_VERIFICATION_TOKEN_LIFETIME,
    )
    return token


def send_email_verification(*, user: User) -> bool:
    token = issue_email_verification_token(user=user)
    if token is None:
        return False

    verification_url = f"{settings.FRONTEND_URL}/verify-email?{urlencode({'token': token})}"
    try:
        send_mail(
            subject="Verify your KnowledgeVault AI email",
            message=(
                "Verify your KnowledgeVault AI email address by opening this link:\n\n"
                f"{verification_url}\n\n"
                "This link expires in 24 hours and can be used only once."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Email verification delivery failed",
            extra={"user_id": str(user.pk)},
        )
        return False
    return True


@transaction.atomic
def confirm_email_verification(*, token: str) -> User:
    token_hash = _token_hash(token)
    user = (
        User.objects.select_for_update(of=("self",))
        .filter(email_verification_tokens__token_hash=token_hash)
        .first()
    )
    if user is None:
        raise InvalidEmailVerificationTokenError

    verification = EmailVerificationToken.objects.select_for_update().get(token_hash=token_hash)
    now = timezone.now()
    if (
        verification.used_at is not None
        or verification.expires_at <= now
        or not user.is_active
        or user.is_email_verified
    ):
        raise InvalidEmailVerificationTokenError

    user.is_email_verified = True
    user.save(update_fields=["is_email_verified", "updated_at"])
    EmailVerificationToken.objects.filter(
        user=user,
        used_at__isnull=True,
    ).update(used_at=now)
    return user
