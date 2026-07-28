from unittest.mock import patch

from django.db import OperationalError
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
    def test_readiness_reports_available_database(self) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "checks": {"database": "ok"},
            },
        )

    @patch(
        "apps.health.views.connection.cursor",
        side_effect=OperationalError("database unavailable"),
    )
    def test_readiness_returns_safe_error_when_database_is_unavailable(
        self,
        _mock_cursor,
    ) -> None:
        response = self.client.get(reverse("health:ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "checks": {"database": "unavailable"},
            },
        )
        self.assertNotContains(response, "database unavailable", status_code=503)

    def test_readiness_rejects_non_get_requests(self) -> None:
        response = self.client.post(reverse("health:ready"))

        self.assertEqual(response.status_code, 405)
