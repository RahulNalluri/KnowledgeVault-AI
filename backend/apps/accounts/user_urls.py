from django.urls import path

from .profile_views import CurrentUserProfileView

app_name = "users"

urlpatterns = [
    path("me/", CurrentUserProfileView.as_view(), name="me"),
]
