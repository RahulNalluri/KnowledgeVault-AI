from django.conf import settings

from config import celery_app


def test_celery_uses_isolated_eager_test_configuration() -> None:
    assert celery_app.main == "knowledgevault_ai"
    assert celery_app.conf.broker_url == "memory://"
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True


def test_celery_accepts_json_only_and_ignores_results_by_default() -> None:
    assert list(celery_app.conf.accept_content) == ["json"]
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert settings.CELERY_TASK_IGNORE_RESULT is True
    assert settings.CELERY_TASK_ACKS_LATE is True
    assert settings.CELERY_TASK_REJECT_ON_WORKER_LOST is True
    assert settings.CELERY_WORKER_PREFETCH_MULTIPLIER == 1


def test_celery_beat_recovers_pending_account_email_deliveries() -> None:
    schedule = settings.CELERY_BEAT_SCHEDULE["dispatch-pending-account-email-deliveries"]

    assert schedule["task"] == "apps.accounts.tasks.dispatch_pending_account_email_deliveries"
    assert schedule["schedule"] == 60.0
