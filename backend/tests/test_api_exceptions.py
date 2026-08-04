import uuid
from types import SimpleNamespace
from unittest.mock import patch

from rest_framework.exceptions import NotFound, ValidationError

from config.api.exceptions import api_exception_handler


def test_validation_errors_use_consistent_error_envelope() -> None:
    request_id = str(uuid.uuid4())
    context = {"request": SimpleNamespace(request_id=request_id)}

    response = api_exception_handler(
        ValidationError({"email": ["Enter a valid email address."]}),
        context,
    )

    assert response.status_code == 400
    assert response.data == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": {"email": ["Enter a valid email address."]},
            "request_id": request_id,
        }
    }


def test_api_errors_keep_a_safe_message_and_code() -> None:
    response = api_exception_handler(NotFound("Resource not found."), {})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"
    assert response.data["error"]["message"] == "Resource not found."
    assert response.data["error"]["details"] == {}
    uuid.UUID(response.data["error"]["request_id"])


def test_unhandled_errors_are_logged_and_hidden_from_clients() -> None:
    error = RuntimeError("database password must never be returned")

    with patch("config.api.exceptions.logger.error") as logger_error:
        response = api_exception_handler(error, {})

    assert response.status_code == 500
    assert response.data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert response.data["error"]["message"] == "An unexpected error occurred."
    assert "password" not in str(response.data)
    logger_error.assert_called_once()
