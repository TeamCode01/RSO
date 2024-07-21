import datetime as dt
import os
import requests

from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.response import Response

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from services.models import FrontError
from services.serializers import FrontErrorSerializer


class FrontReportsViewSet(viewsets.ModelViewSet):
    """Отправка отчетов в телеграм бот."""

    serializer_class = FrontErrorSerializer
    queryset = FrontError.objects.all()

    @swagger_auto_schema(
                request_body=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=[],
                    properties={
                        'error_code': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                        ),
                        'error_description': openapi.Schema(
                            type=openapi.TYPE_STRING,
                        ),
                        'url': openapi.Schema(
                            type=openapi.TYPE_STRING,
                        ),
                        'method': openapi.Schema(
                            type=openapi.TYPE_STRING
                        ),
                    }
                )
            )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None

        front_error = FrontError.objects.create(
            user=user,
            error_code=serializer.validated_data['error_code'],
            error_description=serializer.validated_data.get('error_description', ''),
            url=serializer.validated_data['url'],
            method=serializer.validated_data['method']
        )
        response_serializer = self.get_serializer(front_error)
        headers = self.get_success_headers(response_serializer.data)
        self.send_to_telegram(response_serializer.data)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def send_to_telegram(self, error_data):
        bot_token = os.getenv('TG_BOT_TOKEN')
        chat_id = os.getenv('TG_CHAT_ID_GROUP')
        message = (
            f"Error Code: {error_data.get('error_code')}\n"
            f"Message: {error_data.get('error_description')}\n"
            "\n"
            f"URL: {error_data.get('url')}\n"
            "\n"
            f"Method: {error_data.get('method')}\n"
            f"Date: {error_data.get('created_at')}\n"
            f"User ID: {error_data.get('user')}"
        )
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': message
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        requests.post(url, data=payload, headers=headers)
