import hashlib

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class LoginIPRateThrottle(SimpleRateThrottle):
    scope = "login_ip"

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LoginIdentityRateThrottle(SimpleRateThrottle):
    scope = "login_identity"

    def get_cache_key(self, request: Request, view: APIView) -> str:
        email = str(request.data.get("email", "")).strip().lower()
        identity_hash = hashlib.sha256(email.encode()).hexdigest()
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{self.get_ident(request)}:{identity_hash}",
        }


class PasswordResetIPRateThrottle(SimpleRateThrottle):
    scope = "password_reset_request_ip"

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PasswordResetIdentityRateThrottle(SimpleRateThrottle):
    scope = "password_reset_request_identity"

    def get_cache_key(self, request: Request, view: APIView) -> str:
        email = str(request.data.get("email", "")).strip().lower()
        identity_hash = hashlib.sha256(email.encode()).hexdigest()
        return self.cache_format % {
            "scope": self.scope,
            "ident": identity_hash,
        }
