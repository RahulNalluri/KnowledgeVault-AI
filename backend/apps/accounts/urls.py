from django.urls import path

from .views import (
    CSRFTokenView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    RefreshView,
    RegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("csrf/", CSRFTokenView.as_view(), name="csrf"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("register/", RegistrationView.as_view(), name="register"),
]
