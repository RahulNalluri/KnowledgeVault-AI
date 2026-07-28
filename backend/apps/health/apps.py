from django.apps import AppConfig


class HealthConfig(AppConfig):
    """Application configuration for operational health checks."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.health"
    verbose_name = "Health"
