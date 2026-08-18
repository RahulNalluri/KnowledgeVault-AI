from django.conf import settings
from django.middleware.csrf import get_token, rotate_token
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.api.csrf import enforce_csrf
from config.api.serializers import ErrorResponseSerializer

from .cookies import clear_refresh_cookie, set_refresh_cookie
from .email_delivery import queue_email_verification, queue_password_reset
from .email_verification import InvalidEmailVerificationTokenError, confirm_email_verification
from .exceptions import InvalidRefreshToken
from .serializers import (
    AccessTokenResponseSerializer,
    CSRFTokenSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestResponseSerializer,
    EmptySerializer,
    LoginResponseSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestResponseSerializer,
    PasswordResetRequestSerializer,
    RegisteredUserSerializer,
    RegistrationSerializer,
)
from .services import issue_token_pair, revoke_refresh_token, rotate_refresh_token
from .throttles import (
    LoginIdentityRateThrottle,
    LoginIPRateThrottle,
    PasswordResetIdentityRateThrottle,
    PasswordResetIPRateThrottle,
)


def _access_response_data(*, access: str, request: Request) -> dict:
    return {
        "access": access,
        "token_type": "Bearer",
        "expires_in": int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        "csrf_token": get_token(request._request),
    }


def _prevent_auth_response_caching(response: Response) -> Response:
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    return response


class RegistrationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registration"

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=RegistrationSerializer,
        responses={
            201: RegisteredUserSerializer,
            400: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        queue_email_verification(user=user)
        return Response(
            RegisteredUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class CSRFTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        responses={200: CSRFTokenSerializer},
    )
    def get(self, request: Request) -> Response:
        return _prevent_auth_response_caching(Response({"csrf_token": get_token(request._request)}))


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginIPRateThrottle, LoginIdentityRateThrottle]

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        enforce_csrf(request)
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = issue_token_pair(user)
        rotate_token(request._request)
        response = Response(
            {
                **_access_response_data(access=tokens.access, request=request),
                "user": RegisteredUserSerializer(user).data,
            }
        )
        set_refresh_cookie(response, tokens.refresh)
        return _prevent_auth_response_caching(response)


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=EmptySerializer,
        responses={
            200: AccessTokenResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        enforce_csrf(request)
        encoded_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not encoded_token:
            raise InvalidRefreshToken
        tokens = rotate_refresh_token(encoded_token)
        response = Response(_access_response_data(access=tokens.access, request=request))
        set_refresh_cookie(response, tokens.refresh)
        return _prevent_auth_response_caching(response)


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "logout"

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=EmptySerializer,
        responses={
            204: None,
            403: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        enforce_csrf(request)
        revoke_refresh_token(request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        rotate_token(request._request)
        return _prevent_auth_response_caching(response)


class PasswordChangeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_change"

    @extend_schema(
        tags=["Authentication"],
        request=PasswordChangeSerializer,
        responses={
            204: None,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(
            request.user,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return _prevent_auth_response_caching(response)


class EmailVerificationResendView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_verification_resend"

    @extend_schema(
        tags=["Authentication"],
        request=EmptySerializer,
        responses={
            202: EmailVerificationRequestResponseSerializer,
            401: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        queue_email_verification(user=request.user)
        return Response(
            {"message": "If verification is required, a new link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class EmailVerificationConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_verification_confirm"

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=EmailVerificationConfirmSerializer,
        responses={
            204: None,
            400: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_email_verification(token=serializer.validated_data["token"])
        except InvalidEmailVerificationTokenError as exc:
            raise serializers.ValidationError(
                {"token": ["The verification token is invalid or expired."]}
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetIPRateThrottle, PasswordResetIdentityRateThrottle]

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=PasswordResetRequestSerializer,
        responses={
            202: PasswordResetRequestResponseSerializer,
            400: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queue_password_reset(email=serializer.validated_data["email"])
        return Response(
            {"message": "If an active account exists, a password reset link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=PasswordResetConfirmSerializer,
        responses={
            204: None,
            400: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return _prevent_auth_response_caching(response)
