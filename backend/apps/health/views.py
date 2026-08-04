from drf_spectacular.utils import extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .checks import celery_worker_is_ready, database_is_ready, redis_is_ready
from .serializers import LivenessSerializer, ReadinessSerializer


@extend_schema(
    tags=["Health"],
    auth=[],
    responses={200: LivenessSerializer},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def liveness(request: Request) -> Response:
    """Report that the Django process can serve HTTP requests."""

    return Response({"status": "ok"})


@extend_schema(
    tags=["Health"],
    auth=[],
    responses={200: ReadinessSerializer, 503: ReadinessSerializer},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def readiness(request: Request) -> Response:
    """Report whether required backend dependencies are available."""

    checks = {
        "database": database_is_ready(),
        "redis": redis_is_ready(),
        "celery_worker": celery_worker_is_ready(),
    }
    all_ready = all(checks.values())

    return Response(
        {
            "status": "ready" if all_ready else "not_ready",
            "checks": {
                name: "ok" if is_ready else "unavailable" for name, is_ready in checks.items()
            },
        },
        status=200 if all_ready else 503,
    )
