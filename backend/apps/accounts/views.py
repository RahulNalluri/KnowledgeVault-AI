from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.api.serializers import ErrorResponseSerializer

from .serializers import RegisteredUserSerializer, RegistrationSerializer


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
        return Response(
            RegisteredUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )
