import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    full_name = models.CharField(max_length=255)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["-date_joined"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
            models.CheckConstraint(
                condition=~models.Q(full_name=""),
                name="accounts_user_full_name_not_empty",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        self.email = type(self).objects._clean_email(self.email)
        self.full_name = type(self).objects._clean_full_name(self.full_name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email


class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"], name="acct_verify_user_exp_idx"),
        ]

    def __str__(self) -> str:
        return f"Email verification token for {self.user_id}"


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"], name="acct_reset_user_exp_idx"),
        ]

    def __str__(self) -> str:
        return f"Password reset token for {self.user_id}"


class AccountEmailDelivery(models.Model):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "EMAIL_VERIFICATION", "Email verification"
        PASSWORD_RESET = "PASSWORD_RESET", "Password reset"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENDING = "SENDING", "Sending"
        SENT = "SENT", "Sent"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    recipient_email = models.EmailField(max_length=254)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_deliveries",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    dispatched_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    token_hash = models.CharField(max_length=64, blank=True, editable=False)
    last_error_code = models.CharField(max_length=64, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["status", "available_at"],
                name="acct_email_status_avail_idx",
            ),
            models.Index(
                fields=["purpose", "recipient_email", "created_at"],
                name="acct_email_recipient_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(purpose="PASSWORD_RESET") | models.Q(user__isnull=False)),
                name="acct_verify_delivery_has_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_purpose_display()} delivery {self.id}"
