from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .exceptions import InvalidCredentials
from .models import User
from .services import AccountAlreadyExistsError, register_user

DUPLICATE_EMAIL_MESSAGE = "An account with this email address already exists."


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    full_name = serializers.CharField(max_length=255, trim_whitespace=True)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        trim_whitespace=False,
    )

    def validate_email(self, value: str) -> str:
        email = User.objects._clean_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(DUPLICATE_EMAIL_MESSAGE)
        return email

    def validate(self, attrs: dict) -> dict:
        candidate = User(email=attrs["email"], full_name=attrs["full_name"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data: dict) -> User:
        try:
            return register_user(**validated_data)
        except AccountAlreadyExistsError as exc:
            raise serializers.ValidationError({"email": [DUPLICATE_EMAIL_MESSAGE]}) from exc


class RegisteredUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "is_email_verified",
            "created_at",
        )
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        write_only=True,
        max_length=128,
        trim_whitespace=False,
    )

    def validate(self, attrs: dict) -> dict:
        request = self.context["request"]
        user = authenticate(
            request=request._request,
            email=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise InvalidCredentials
        attrs["user"] = user
        return attrs


class CSRFTokenSerializer(serializers.Serializer):
    csrf_token = serializers.CharField(read_only=True)


class AccessTokenResponseSerializer(CSRFTokenSerializer):
    access = serializers.CharField(read_only=True)
    token_type = serializers.ChoiceField(choices=["Bearer"], read_only=True)
    expires_in = serializers.IntegerField(read_only=True)


class LoginResponseSerializer(AccessTokenResponseSerializer):
    user = RegisteredUserSerializer(read_only=True)


class EmptySerializer(serializers.Serializer):
    pass
