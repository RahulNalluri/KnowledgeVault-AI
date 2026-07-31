from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class LivenessViewTests(SimpleTestCase):
    def test_liveness_returns_ok_without_dependency_checks(self) -> None:
        response = self.client.get(reverse("health:live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_liveness_rejects_non_get_requests(self) -> None:
        response = self.client.post(reverse("health:live"))

        self.assertEqual(response.status_code, 405)


class ReadinessViewTests(TestCase):
    @patch("apps.health.views.redis_is_ready", return_value=True)
    def test_readiness_reports_available_dependencies(self, _mock_redis) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "checks": {"database": "ok", "redis": "ok"},
            },
        )

    @patch("apps.health.views.redis_is_ready", return_value=True)
    @patch("apps.health.views.database_is_ready", return_value=False)
    def test_readiness_returns_safe_error_when_database_is_unavailable(
        self,
        _mock_database,
        _mock_redis,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "checks": {"database": "unavailable", "redis": "ok"},
            },
        )

    @patch("apps.health.views.redis_is_ready", return_value=False)
    def test_readiness_returns_safe_error_when_redis_is_unavailable(
        self,
        _mock_redis,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "checks": {"database": "ok", "redis": "unavailable"},
            },
        )

    def test_readiness_rejects_non_get_requests(self) -> None:
        response = self.client.post(reverse("health:ready"))

        self.assertEqual(response.status_code, 405)
