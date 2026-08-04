import logging
import uuid

from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def _request_id(context: dict) -> str:
    request = context.get("request")
    return getattr(request, "request_id", None) or str(uuid.uuid4())


def _error_code(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "VALIDATION_ERROR"
    if isinstance(exc, APIException):
        return str(exc.default_code).upper()
    return "INTERNAL_SERVER_ERROR"


def api_exception_handler(exc: Exception, context: dict) -> Response:
    response = exception_handler(exc, context)
    request_id = _request_id(context)

    if response is None:
        logger.error(
            "Unhandled API exception",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"request_id": request_id},
        )
        return Response(
            {
                "error": {
                    "code": _error_code(exc),
                    "message": "An unexpected error occurred.",
                    "details": {},
                    "request_id": request_id,
                }
            },
            status=500,
        )

    response_data = response.data
    if isinstance(response_data, dict) and "detail" in response_data:
        message = str(response_data["detail"])
        details = {}
    else:
        message = "Request validation failed."
        details = response_data

    response.data = {
        "error": {
            "code": _error_code(exc),
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }
    return response
