from django.urls import path

from .views import liveness, readiness

app_name = "health"

urlpatterns = [
    path("live/", liveness, name="live"),
    path("ready/", readiness, name="ready"),
]
