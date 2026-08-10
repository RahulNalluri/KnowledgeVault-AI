from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request


class CSRFValidationFailed(PermissionDenied):
    default_detail = _("CSRF validation failed.")
    default_code = "csrf_failed"


def enforce_csrf(request: Request) -> None:
    """Apply Django's CSRF validation to cookie-backed API operations."""

    middleware = CsrfViewMiddleware(HttpResponse)
    rejection = middleware.process_view(
        request._request,
        HttpResponse,
        (),
        {},
    )
    if rejection is not None:
        raise CSRFValidationFailed
