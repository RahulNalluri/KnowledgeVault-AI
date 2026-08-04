from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def _clean_email(email: str | None) -> str:
        if not email:
            raise ValueError("Users must have an email address.")
        return BaseUserManager.normalize_email(email.strip()).lower()

    @staticmethod
    def _clean_full_name(full_name: str | None) -> str:
        if not full_name or not full_name.strip():
            raise ValueError("Users must have a full name.")
        return full_name.strip()

    def _create_user(
        self,
        email: str,
        full_name: str,
        password: str | None,
        **extra_fields,
    ):
        user = self.model(
            email=self._clean_email(email),
            full_name=self._clean_full_name(full_name),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields,
    ):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, full_name, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields,
    ):
        if not password:
            raise ValueError("Superusers must have a password.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusers must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers must have is_superuser=True.")

        return self._create_user(email, full_name, password, **extra_fields)

    def get_by_natural_key(self, username: str):
        return self.get(email__iexact=username)
