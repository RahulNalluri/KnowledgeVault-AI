import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import AccountEmailDelivery, User


class UserManagerTests(TestCase):
    def test_create_user_normalizes_identity_and_hashes_password(self) -> None:
        user = User.objects.create_user(
            email="  PERSON@Example.COM  ",
            full_name="  Example Person  ",
            password="strong-test-password",
        )

        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(user.full_name, "Example Person")
        self.assertTrue(user.check_password("strong-test-password"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_email_verified)

    def test_create_user_without_password_uses_an_unusable_password(self) -> None:
        user = User.objects.create_user(
            email="person@example.com",
            full_name="Example Person",
        )

        self.assertFalse(user.has_usable_password())

    def test_create_user_requires_email_and_full_name(self) -> None:
        invalid_identities = (
            {"email": "", "full_name": "Example Person"},
            {"email": "person@example.com", "full_name": "  "},
        )

        for identity in invalid_identities:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                User.objects.create_user(password="strong-test-password", **identity)

    def test_create_superuser_sets_required_flags(self) -> None:
        user = User.objects.create_superuser(
            email="admin@example.com",
            full_name="Admin User",
            password="strong-admin-password",
        )

        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_invalid_flags(self) -> None:
        invalid_flags = ({"is_staff": False}, {"is_superuser": False})

        for flags in invalid_flags:
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                User.objects.create_superuser(
                    email="admin@example.com",
                    full_name="Admin User",
                    password="strong-admin-password",
                    **flags,
                )

    def test_create_superuser_requires_password(self) -> None:
        with self.assertRaisesRegex(ValueError, "password"):
            User.objects.create_superuser(
                email="admin@example.com",
                full_name="Admin User",
            )

    def test_natural_key_lookup_is_case_insensitive(self) -> None:
        user = User.objects.create_user(
            email="person@example.com",
            full_name="Example Person",
        )

        found = User.objects.get_by_natural_key("PERSON@EXAMPLE.COM")

        self.assertEqual(found, user)


class UserModelTests(TestCase):
    def test_user_uses_uuid_primary_key_and_email_login(self) -> None:
        user = User.objects.create_user(
            email="person@example.com",
            full_name="Example Person",
        )

        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, ["full_name"])
        self.assertEqual(str(user), "person@example.com")

    def test_direct_save_normalizes_email_and_full_name(self) -> None:
        user = User(email="  PERSON@Example.COM ", full_name=" Example Person ")
        user.set_unusable_password()
        user.save()

        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(user.full_name, "Example Person")

    def test_email_is_unique_without_case_sensitivity(self) -> None:
        User.objects.create_user(
            email="person@example.com",
            full_name="First Person",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="PERSON@example.com",
                full_name="Second Person",
            )

    def test_avatar_uses_private_media_storage_path(self) -> None:
        avatar_field = User._meta.get_field("avatar")

        self.assertEqual(avatar_field.upload_to, "avatars/%Y/%m/")


class AccountEmailDeliveryModelTests(TestCase):
    def test_verification_delivery_requires_a_user(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccountEmailDelivery.objects.create(
                purpose=AccountEmailDelivery.Purpose.EMAIL_VERIFICATION,
                recipient_email="person@example.com",
            )

    def test_safe_string_representation_excludes_recipient(self) -> None:
        delivery = AccountEmailDelivery.objects.create(
            purpose=AccountEmailDelivery.Purpose.PASSWORD_RESET,
            recipient_email="private@example.com",
        )

        self.assertEqual(
            str(delivery),
            f"Password reset delivery {delivery.id}",
        )
        self.assertNotIn(delivery.recipient_email, str(delivery))
