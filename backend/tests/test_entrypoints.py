from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.wsgi import WSGIHandler

from config.asgi import application as asgi_application
from config.wsgi import application as wsgi_application


def test_asgi_application_is_configured() -> None:
    assert isinstance(asgi_application, ASGIHandler)


def test_wsgi_application_is_configured() -> None:
    assert isinstance(wsgi_application, WSGIHandler)
