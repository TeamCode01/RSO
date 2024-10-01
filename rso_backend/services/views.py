from datetime import datetime
import os
from urllib.parse import urlparse
import requests

from django.conf import settings
from django.db.models import Q
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.tokens import RefreshToken


from services.models import FrontError
from services.serializers import FrontErrorSerializer
from users.models import RSOUser


class FrontReportsViewSet(viewsets.ModelViewSet):
    """Отправка отчетов в телеграм бот.

    error_code - код ошибки.
    error_description - описание ошибки.
    url - URL запроса.
    method - метод запроса(POST, GET и т.д).
    """

    serializer_class = FrontErrorSerializer
    queryset = FrontError.objects.all()
    permission_classes = [permissions.AllowAny, ]

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
            error_description=serializer.validated_data.get(
                'error_description', ''
            ),
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
        error_url_host = urlparse( error_data.get('url')).netloc.split(':')[0]
        try:
            if error_url_host == '127.0.0.1' or error_url_host == 'localhost':
                message_thread_id = os.getenv('TG_LOCAL_TOPIC_ID')
            elif error_url_host == '213.139.208.147':
                message_thread_id = os.getenv('TG_DEV_TOPIC_ID')
            else:
                message_thread_id = os.getenv('TG_MAIN_TOPIC_ID')
        except Exception:
            message_thread_id = None
        payload = {
            'chat_id': chat_id,
            'text': message,
            'message_thread_id': message_thread_id
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        requests.post(url, data=payload, headers=headers)


class VKLoginAPIView(APIView):

    """Вход через VK.

    Принимает silent_token и uuid полученные от ВК.
    В ответе access_token и  refresh_token бекенда RSO.
    Время жизни access_token - 5 часов.
    Время жизни refresh_token - 7 дней.
    """

    permission_classes = [permissions.AllowAny,]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'silent_token': openapi.Schema(type=openapi.TYPE_STRING),
                'uuid': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )
    )
    def post(self, request):
        silent_token = request.data.get('silent_token')
        uuid = request.data.get('uuid')

        if not silent_token or not uuid:
            return Response(
                {'error': 'Silent token и uuid не были переданы в запросе.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            response = requests.post(
                'https://api.vk.com/method/auth.exchangeSilentAuthToken',
                params={
                    'v': settings.VK_API_VERSION,
                    'token': silent_token,
                    'access_token': settings.VITE_SERVICE_TOKEN,
                    'uuid': uuid
                })
            response_data = response.json()

            if 'response' in response_data:
                access_token = response_data['response']['access_token']
                email = response_data['response'].get('email')
                phone = response_data['response'].get('phone')
            else:
                return Response(
                    {'error': response_data.get('error', 'Unknown error')},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except requests.RequestException as e:
            return Response(
                {'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response = requests.get(
            'https://api.vk.com/method/account.getProfileInfo',
            params={
                'access_token': access_token,
                'v': settings.VK_API_VERSION,
            }
        )
        vk_user_data = response.json().get('response')

        if not vk_user_data:
            return Response(
                {
                    'error': 'Неправильный access token '
                    'или ошибка в полученном ответе от ВК.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        vk_id = vk_user_data.get('id')
        first_name = vk_user_data.get('first_name')
        last_name = vk_user_data.get('last_name')
        screen_name = vk_user_data.get('screen_name', '')
        bdate = vk_user_data.get('bdate', None)
        city = (
            vk_user_data.get(
                'city'
            ).get(
                'title'
            ) if vk_user_data.get('city') else None
        )
        # photo_url = vk_user_data.get('photo_200', None) до S3 не загружаю на сервер
        sex = vk_user_data.get('sex', None)

        if bdate:
            parsed_date = datetime.strptime(bdate, '%d.%m.%Y')
            formatted_date = parsed_date.strftime('%Y-%m-%d')

        gender = None
        if sex == 2:
            gender = 'male'
        elif sex == 1:
            gender = 'female'

        if screen_name != '':
            user = RSOUser.objects.filter(
                Q(social_vk='https://vk.com/'+str(screen_name)) | Q(social_vk='https://vk.com/id'+str(vk_id)) | Q(email=email)
            ).first()
        else:
            user = RSOUser.objects.filter(
                Q(email=email) | Q(social_vk='https://vk.com/id'+str(vk_id))
            ).first()

        if user:
            if not user.first_name:
                user.first_name = first_name
            if not user.last_name:
                user.last_name = last_name
            if not user.gender and gender:
                user.gender = gender
            if not user.username:
                user.username = f'{vk_id}_{screen_name}'
            if not user.date_of_birth and bdate:
                user.date_of_birth = formatted_date
            if not user.phone_number and phone:
                user.phone_number = phone
            if not user.address and city:
                user.address = city

        if not user:
            user = RSOUser.objects.create(
                social_vk='https://vk.com/id'+str(vk_id),
                first_name=first_name,
                last_name=last_name,
                username=f'{vk_id}_{screen_name}',
                gender=gender,
                date_of_birth=formatted_date,
                phone_number=phone,
                address=city,
                email=email
            )
        user.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
