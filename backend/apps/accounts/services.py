from django.db import IntegrityError, transaction

from .models import User


class AccountAlreadyExistsError(Exception):
    """Raised when registration races with an existing email address."""


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
