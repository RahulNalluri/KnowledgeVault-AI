from dataclasses import dataclass

from django.contrib.auth.models import update_last_login
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import InvalidRefreshToken
from .models import User


class AccountAlreadyExistsError(Exception):
    """Raised when registration races with an existing email address."""


class IncorrectCurrentPasswordError(Exception):
    """Raised when a password change does not confirm the current password."""


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str


def register_user(*, email: str, full_name: str, password: str) -> User:
    """Create a standard user while safely translating duplicate-email races."""

    try:
        with transaction.atomic():
            return User.objects.create_user(
                email=email,
                full_name=full_name,
                password=password,
            )
    except IntegrityError as exc:
        if User.objects.filter(email__iexact=email).exists():
            raise AccountAlreadyExistsError from exc
        raise


def issue_token_pair(user: User) -> TokenPair:
    refresh = RefreshToken.for_user(user)
    update_last_login(None, user)
    return TokenPair(
        access=str(refresh.access_token),
        refresh=str(refresh),
    )


@transaction.atomic
def rotate_refresh_token(encoded_token: str) -> TokenPair:
    try:
        current = RefreshToken(encoded_token)
        outstanding = OutstandingToken.objects.select_for_update().get(jti=current["jti"])
        if BlacklistedToken.objects.filter(token=outstanding).exists():
            raise InvalidRefreshToken
        user = JWTAuthentication().get_user(current)
        current.blacklist()
        replacement = RefreshToken.for_user(user)
    except (AuthenticationFailed, OutstandingToken.DoesNotExist, TokenError) as exc:
        raise InvalidRefreshToken from exc

    return TokenPair(
        access=str(replacement.access_token),
        refresh=str(replacement),
    )


def revoke_refresh_token(encoded_token: str | None) -> None:
    if not encoded_token:
        return
    try:
        RefreshToken(encoded_token).blacklist()
    except TokenError:
        return


@transaction.atomic
def change_user_password(*, user: User, current_password: str, new_password: str) -> User:
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if not locked_user.check_password(current_password):
        raise IncorrectCurrentPasswordError

    locked_user.set_password(new_password)
    locked_user.save(update_fields=["password", "updated_at"])

    outstanding_tokens = OutstandingToken.objects.select_for_update().filter(user=locked_user)
    for outstanding_token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(token=outstanding_token)

    return locked_user


@transaction.atomic
def update_user_profile(*, user: User, full_name: str) -> User:
    user.full_name = User.objects._clean_full_name(full_name)
    user.save(update_fields=["full_name", "updated_at"])
    return user
