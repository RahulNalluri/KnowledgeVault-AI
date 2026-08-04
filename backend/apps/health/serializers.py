from rest_framework import serializers

DEPENDENCY_STATUS_CHOICES = [("ok", "OK"), ("unavailable", "Unavailable")]


class LivenessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok"])


class DependencyChecksSerializer(serializers.Serializer):
    database = serializers.ChoiceField(choices=DEPENDENCY_STATUS_CHOICES)
    redis = serializers.ChoiceField(choices=DEPENDENCY_STATUS_CHOICES)
    celery_worker = serializers.ChoiceField(choices=DEPENDENCY_STATUS_CHOICES)


class ReadinessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ready", "not_ready"])
    checks = DependencyChecksSerializer()
