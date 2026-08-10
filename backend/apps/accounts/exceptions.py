from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class InvalidCredentials(APIException):
    status_code = 401
    default_detail = _("Invalid email or password.")
    default_code = "invalid_credentials"


class InvalidRefreshToken(APIException):
    status_code = 401
    default_detail = _("The refresh token is invalid or expired.")
    default_code = "invalid_refresh_token"
