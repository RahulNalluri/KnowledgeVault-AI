from django.urls import path

from .views import (
    CSRFTokenView,
    EmailVerificationConfirmView,
    EmailVerificationResendView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("csrf/", CSRFTokenView.as_view(), name="csrf"),
    path(
        "email/verification/confirm/",
        EmailVerificationConfirmView.as_view(),
        name="email-verification-confirm",
    ),
    path(
        "email/verification/resend/",
        EmailVerificationResendView.as_view(),
        name="email-verification-resend",
    ),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path("register/", RegistrationView.as_view(), name="register"),
]
