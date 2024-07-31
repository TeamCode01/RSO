from rest_framework import serializers

from services.models import FrontError


class FrontErrorSerializer(serializers.ModelSerializer):
    """Сериализация ошибок для фронтенда."""

    class Meta:
        fields = (
            'id',
            'user',
            'error_code',
            'error_description',
            'url',
            'method',
            'created_at'
        )
        model = FrontError
        read_only_fields = ('created_at', 'user')
