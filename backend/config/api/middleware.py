import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class RequestIDMiddleware:
    header_name = "X-Request-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    @staticmethod
    def _request_id(request: HttpRequest) -> str:
        supplied_id = request.headers.get("X-Request-ID", "")
        try:
            return str(uuid.UUID(supplied_id))
        except (ValueError, AttributeError):
            return str(uuid.uuid4())

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.request_id = self._request_id(request)
        response = self.get_response(request)
        response[self.header_name] = request.request_id
        return response
