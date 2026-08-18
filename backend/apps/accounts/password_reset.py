import hashlib
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import PasswordResetToken, User
from .services import revoke_all_user_refresh_tokens


class InvalidPasswordResetTokenError(Exception):
    """Raised when a reset token cannot safely update an account password."""


class InvalidResetPasswordError(Exception):
    """Raised when a replacement password fails user-aware validation."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__(*messages)
        self.messages = messages


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@transaction.atomic
def issue_password_reset_token(*, user: User) -> str | None:
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if not locked_user.is_active:
        return None

    now = timezone.now()
    PasswordResetToken.objects.filter(
        user=locked_user,
        expires_at__lte=now,
    ).delete()

    token = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=locked_user,
        token_hash=_token_hash(token),
        expires_at=now + settings.PASSWORD_RESET_TOKEN_LIFETIME,
    )
    return token


def send_password_reset_email(*, user: User, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?{urlencode({'token': token})}"
    send_mail(
        subject="Reset your KnowledgeVault AI password",
        message=(
            "Reset your KnowledgeVault AI password by opening this link:\n\n"
            f"{reset_url}\n\n"
            "This link expires in one hour and can be used only once."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def password_reset_token_is_active(*, user: User, token: str) -> bool:
    return PasswordResetToken.objects.filter(
        user=user,
        token_hash=_token_hash(token),
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).exists()


@transaction.atomic
def reset_password(*, token: str, new_password: str) -> User:
    token_hash = _token_hash(token)
    user = (
        User.objects.select_for_update(of=("self",))
        .filter(password_reset_tokens__token_hash=token_hash)
        .first()
    )
    if user is None:
        raise InvalidPasswordResetTokenError

    reset_token = PasswordResetToken.objects.select_for_update().get(token_hash=token_hash)
    now = timezone.now()
    if reset_token.used_at is not None or reset_token.expires_at <= now or not user.is_active:
        raise InvalidPasswordResetTokenError

    if user.check_password(new_password):
        raise InvalidResetPasswordError(["The new password must differ from the current password."])
    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise InvalidResetPasswordError(list(exc.messages)) from exc

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    PasswordResetToken.objects.filter(
        user=user,
        used_at__isnull=True,
    ).update(used_at=now)
    revoke_all_user_refresh_tokens(user=user)
    return user
