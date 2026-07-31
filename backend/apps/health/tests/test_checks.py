from unittest.mock import MagicMock, Mock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings
from kombu.exceptions import OperationalError
from redis.exceptions import ConnectionError

from apps.health.checks import celery_worker_is_ready, database_is_ready, redis_is_ready


class DatabaseReadinessCheckTests(SimpleTestCase):
    @patch("apps.health.checks.connection")
    def test_returns_true_when_minimal_query_succeeds(self, mock_connection) -> None:
        cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        self.assertTrue(database_is_ready())

        cursor.execute.assert_called_once_with("SELECT 1")

    @patch("apps.health.checks.connection")
    def test_returns_false_when_database_query_fails(self, mock_connection) -> None:
        mock_connection.cursor.side_effect = DatabaseError("database unavailable")

        self.assertFalse(database_is_ready())


@override_settings(REDIS_URL="redis://redis.example:6379/0")
class RedisReadinessCheckTests(SimpleTestCase):
    @patch("apps.health.checks.Redis.from_url")
    def test_returns_true_when_ping_succeeds_and_closes_client(self, mock_from_url) -> None:
        client = Mock()
        client.ping.return_value = True
        mock_from_url.return_value = client

        self.assertTrue(redis_is_ready())

        mock_from_url.assert_called_once_with(
            "redis://redis.example:6379/0",
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.close.assert_called_once_with()

    @patch("apps.health.checks.Redis.from_url")
    def test_returns_false_and_closes_client_when_ping_fails(self, mock_from_url) -> None:
        client = Mock()
        client.ping.side_effect = ConnectionError("connection failed")
        mock_from_url.return_value = client

        self.assertFalse(redis_is_ready())

        client.close.assert_called_once_with()

    @override_settings(REDIS_URL="not-a-redis-url")
    def test_returns_false_for_an_invalid_url(self) -> None:
        self.assertFalse(redis_is_ready())


class CeleryWorkerReadinessCheckTests(SimpleTestCase):
    @patch("apps.health.checks.celery_app.control.ping")
    def test_returns_true_when_a_worker_responds_with_pong(self, mock_ping) -> None:
        mock_ping.return_value = [{"celery@worker": {"ok": "pong"}}]

        self.assertTrue(celery_worker_is_ready())

        mock_ping.assert_called_once_with(timeout=1.0)

    @patch("apps.health.checks.celery_app.control.ping", return_value=[])
    def test_returns_false_when_no_workers_respond(self, _mock_ping) -> None:
        self.assertFalse(celery_worker_is_ready())

    @patch("apps.health.checks.celery_app.control.ping")
    def test_ignores_malformed_worker_replies(self, mock_ping) -> None:
        mock_ping.return_value = [None, {"celery@worker": "unexpected"}]

        self.assertFalse(celery_worker_is_ready())

    @patch(
        "apps.health.checks.celery_app.control.ping",
        side_effect=OperationalError("broker unavailable"),
    )
    def test_returns_false_when_the_broker_is_unavailable(self, _mock_ping) -> None:
        self.assertFalse(celery_worker_is_ready())
