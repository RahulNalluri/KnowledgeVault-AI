from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from .checks import celery_worker_is_ready, database_is_ready, redis_is_ready


@require_GET
def liveness(request: HttpRequest) -> JsonResponse:
    """Report that the Django process can serve HTTP requests."""

    return JsonResponse({"status": "ok"})


@require_GET
def readiness(request: HttpRequest) -> JsonResponse:
    """Report whether required backend dependencies are available."""

    checks = {
        "database": database_is_ready(),
        "redis": redis_is_ready(),
        "celery_worker": celery_worker_is_ready(),
    }
    all_ready = all(checks.values())

    return JsonResponse(
        {
            "status": "ready" if all_ready else "not_ready",
            "checks": {
                name: "ok" if is_ready else "unavailable" for name, is_ready in checks.items()
            },
        },
        status=200 if all_ready else 503,
    )
