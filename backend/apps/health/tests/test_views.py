from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class LivenessViewTests(SimpleTestCase):
    def test_liveness_returns_ok_without_dependency_checks(self) -> None:
        with (
            patch("apps.health.views.database_is_ready") as mock_database,
            patch("apps.health.views.redis_is_ready") as mock_redis,
            patch("apps.health.views.celery_worker_is_ready") as mock_celery,
        ):
            response = self.client.get(reverse("health:live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_database.assert_not_called()
        mock_redis.assert_not_called()
        mock_celery.assert_not_called()

    def test_liveness_rejects_non_get_requests(self) -> None:
        response = self.client.post(reverse("health:live"))

        self.assertEqual(response.status_code, 405)


class ReadinessViewTests(TestCase):
    @patch("apps.health.views.celery_worker_is_ready", return_value=True)
    @patch("apps.health.views.redis_is_ready", return_value=True)
    def test_readiness_reports_available_dependencies(
        self,
        _mock_redis,
        _mock_celery,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "checks": {
                    "database": "ok",
                    "redis": "ok",
                    "celery_worker": "ok",
                },
            },
        )

    @patch("apps.health.views.celery_worker_is_ready", return_value=True)
    @patch("apps.health.views.redis_is_ready", return_value=True)
    @patch("apps.health.views.database_is_ready", return_value=False)
    def test_readiness_returns_safe_error_when_database_is_unavailable(
        self,
        _mock_database,
        _mock_redis,
        _mock_celery,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "checks": {
                    "database": "unavailable",
                    "redis": "ok",
                    "celery_worker": "ok",
                },
            },
        )

    @patch("apps.health.views.celery_worker_is_ready", return_value=True)
    @patch("apps.health.views.redis_is_ready", return_value=False)
    def test_readiness_returns_safe_error_when_redis_is_unavailable(
        self,
        _mock_redis,
        _mock_celery,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "checks": {
                    "database": "ok",
                    "redis": "unavailable",
                    "celery_worker": "ok",
                },
            },
        )

    @patch("apps.health.views.celery_worker_is_ready", return_value=False)
    @patch("apps.health.views.redis_is_ready", return_value=True)
    def test_readiness_returns_safe_error_when_no_celery_worker_is_available(
        self,
        _mock_redis,
        _mock_celery,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "checks": {
                    "database": "ok",
                    "redis": "ok",
                    "celery_worker": "unavailable",
                },
            },
        )

    @patch("apps.health.views.celery_worker_is_ready", return_value=False)
    @patch("apps.health.views.redis_is_ready", return_value=False)
    @patch("apps.health.views.database_is_ready", return_value=False)
    def test_readiness_reports_every_unavailable_dependency(
        self,
        _mock_database,
        _mock_redis,
        _mock_celery,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "checks": {
                    "database": "unavailable",
                    "redis": "unavailable",
                    "celery_worker": "unavailable",
                },
            },
        )

    def test_readiness_rejects_non_get_requests(self) -> None:
        response = self.client.post(reverse("health:ready"))

        self.assertEqual(response.status_code, 405)
