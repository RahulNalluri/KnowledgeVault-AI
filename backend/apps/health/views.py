from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


def _database_is_ready() -> bool:
    """Return whether Django can execute a minimal database query."""

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return False

    return True


@require_GET
def liveness(request: HttpRequest) -> JsonResponse:
    """Report that the Django process can serve HTTP requests."""

    return JsonResponse({"status": "ok"})


@require_GET
def readiness(request: HttpRequest) -> JsonResponse:
    """Report whether required backend dependencies are available."""

    database_ready = _database_is_ready()
    status_code = 200 if database_ready else 503

    return JsonResponse(
        {
            "status": "ready" if database_ready else "not_ready",
            "checks": {
                "database": "ok" if database_ready else "unavailable",
            },
        },
        status=status_code,
    )
