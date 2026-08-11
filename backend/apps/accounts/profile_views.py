from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api.serializers import ErrorResponseSerializer

from .serializers import (
    CurrentUserProfileSerializer,
    CurrentUserProfileUpdateSerializer,
)


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        responses={
            200: CurrentUserProfileSerializer,
            401: ErrorResponseSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        return Response(CurrentUserProfileSerializer(request.user).data)

    @extend_schema(
        tags=["Users"],
        request=CurrentUserProfileUpdateSerializer,
        responses={
            200: CurrentUserProfileSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
        },
    )
    def patch(self, request: Request) -> Response:
        serializer = CurrentUserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(CurrentUserProfileSerializer(user).data)
