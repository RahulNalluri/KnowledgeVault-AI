from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField()
    request_id = serializers.UUIDField()


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()
