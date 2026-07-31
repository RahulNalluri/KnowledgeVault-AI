from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from redis.exceptions import ConnectionError

from apps.health.checks import redis_is_ready


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
