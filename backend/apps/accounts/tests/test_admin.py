from django.contrib import admin
from django.test import SimpleTestCase

from apps.accounts.admin import (
    AccountEmailDeliveryAdmin,
    EmailVerificationTokenAdmin,
    PasswordResetTokenAdmin,
    UserAdmin,
)
from apps.accounts.models import (
    AccountEmailDelivery,
    EmailVerificationToken,
    PasswordResetToken,
    User,
)


class UserAdminTests(SimpleTestCase):
    def test_custom_user_is_registered_with_custom_admin(self) -> None:
        self.assertIsInstance(admin.site._registry[User], UserAdmin)

    def test_sensitive_and_audit_fields_have_safe_admin_configuration(self) -> None:
        model_admin = admin.site._registry[User]

        self.assertIn("email", model_admin.search_fields)
        self.assertIn("id", model_admin.readonly_fields)
        self.assertIn("created_at", model_admin.readonly_fields)
        self.assertIn("updated_at", model_admin.readonly_fields)

    def test_verification_tokens_are_read_only_in_admin(self) -> None:
        model_admin = admin.site._registry[EmailVerificationToken]

        self.assertIsInstance(model_admin, EmailVerificationTokenAdmin)
        self.assertIn("token_hash", model_admin.readonly_fields)
        self.assertFalse(model_admin.has_add_permission(request=None))
        self.assertFalse(model_admin.has_change_permission(request=None))

    def test_password_reset_tokens_are_read_only_in_admin(self) -> None:
        model_admin = admin.site._registry[PasswordResetToken]

        self.assertIsInstance(model_admin, PasswordResetTokenAdmin)
        self.assertIn("token_hash", model_admin.readonly_fields)
        self.assertFalse(model_admin.has_add_permission(request=None))
        self.assertFalse(model_admin.has_change_permission(request=None))

    def test_email_deliveries_are_searchable_and_read_only_in_admin(self) -> None:
        model_admin = admin.site._registry[AccountEmailDelivery]

        self.assertIsInstance(model_admin, AccountEmailDeliveryAdmin)
        self.assertIn("recipient_email", model_admin.search_fields)
        self.assertIn("token_hash", model_admin.readonly_fields)
        self.assertFalse(model_admin.has_add_permission(request=None))
        self.assertFalse(model_admin.has_change_permission(request=None))
