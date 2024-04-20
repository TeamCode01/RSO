import mimetypes
import os
import zipfile
import io

from dal import autocomplete
from django.db.models import Q
from django.conf import settings
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from openpyxl import Workbook
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from api.mixins import RetrieveUpdateViewSet, RetrieveViewSet
from api.permissions import (IsCommanderOrTrustedAnywhere, IsStuffOrAuthor,
                             PersonalDataPermission,
                             IsForeignAdditionalDocsAuthor,
                             OnlyStuffOrCentralCommander,)
from api.tasks import send_reset_password_email_without_user
from api.utils import download_file, get_user
from users.filters import RSOUserFilter
from users.models import (AdditionalForeignDocs, RSOUser, UserDocuments,
                          UserForeignDocuments, UserForeignParentDocs,
                          UserPrivacySettings, UserProfessionalEducation,
                          UserRegion, UserStatementDocuments, UserEducation,
                          UserVerificationRequest, UserMedia, UserParent)
from users.serializers import (EmailSerializer, ForeignUserDocumentsSerializer,
                               ProfessionalEductionSerializer,
                               RSOUserSerializer, SafeUserSerializer,
                               UserCommanderSerializer,
                               UserDocumentsSerializer,
                               UserEducationSerializer,
                               UserHeadquarterPositionSerializer,
                               UserMediaSerializer,
                               UserNotificationsCountSerializer,
                               UserPrivacySettingsSerializer,
                               UserProfessionalEducationSerializer,
                               UserRegionSerializer, UsersParentSerializer,
                               UserStatementDocumentsSerializer,
                               UserTrustedSerializer,
                               AdditionalForeignDocsSerializer,
                               UserForeignParentDocsSerializer,
                               UserIdRegionSerializer,)


class CustomUserViewSet(UserViewSet):
    """Кастомный вьюсет юзера.
    Доступно изменение метода сброса пароля reset_password
    на новом эндпоинте api/v1/reset_password/.
    Эндпоинт списка юзеров /api/v1/rsousers/.
    Доступен поиск по username, first_name, last_name, patronymic_name
    при передаче search query-параметра.
    По умолчанию сортируются по last_name.
    Доступна фильтрация по полям:
    - district_headquarter__name - имя ОШ,
    - regional_headquarter__name - имя РШ,
    - local_headquarter__name - имя МШ,
    - educational_headquarter__name - имя СО ОО,
    - detachment__name - имя отряда,
    - gender - male/female,
    - is_verified - true/false,
    - membership_fee - true/false,
    - date_of_birth - поиск по конкретной дате в формате дд.мм.гггг,
    - date_of_birth_lte - поиск по датам до указанной,
    - date_of_birth_gte - поиск по дата после указанной,
    - region - имя региона.
    """

    filter_backends = (
        filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter
    )
    search_fields = ('username', 'first_name', 'last_name', 'patronymic_name')
    filterset_class = RSOUserFilter
    ordering_fields = ('last_name', 'date_of_birth')

    @method_decorator(cache_page(settings.RSOUSERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(
            methods=['post'],
            detail=False,
            permission_classes=(permissions.AllowAny,),
            serializer_class=EmailSerializer,
    )
    def reset_password(self, request, *args, **kwargs):
        """
        POST-запрос с адресом почты в json`е
        высылает ссылку на почту на подтвеждение смены пароля.
        Вид ссылки в письме:
        'https://лк.трудкрут.рф/password/reset/confirm/{uid}/{token}'
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        try:
            RSOUser.objects.get(email__iexact=data.get('email'))
            send_reset_password_email_without_user.delay(data=data)
            return Response(status=status.HTTP_200_OK)
        except (RSOUser.DoesNotExist, AttributeError):
            return Response(
                {'detail': (
                    'Нет пользователя с введенным email или опечатка в адресе.'
                )},
                status=status.HTTP_204_NO_CONTENT
            )
        except RSOUser.MultipleObjectsReturned:
            return Response(
                {'detail': (
                    'В БД несколько юзеров с одним адресом почты.'
                    ' Отредактируйте дубликаты и повторите попытку.'
                )},
                status=status.HTTP_409_CONFLICT
            )


class RSOUserViewSet(RetrieveUpdateViewSet):
    """
    Представляет пользователей. Доступны операции чтения.
    Пользователь имеет возможность изменять собственные данные
    по id или по эндпоинту /users/me.
    """
    queryset = RSOUser.objects.all()
    serializer_class = RSOUserSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            permission_classes = (
                permissions.IsAuthenticated,
                PersonalDataPermission,
            )
        else:
            permission_classes = (
                permissions.IsAuthenticated, IsCommanderOrTrustedAnywhere,
            )
        return [permission() for permission in permission_classes]

    @action(
        detail=False,
        methods=['get', 'patch'],
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=RSOUserSerializer,
    )
    def me(self, request, pk=None):
        """Представляет текущего авторизованного пользователя."""
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                request.user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(self.get_serializer(request.user).data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=RSOUserSerializer,
    )
    def me_notifications_count(self, request, pk=None):
        """
        Возвращает количество активных заявок для текущего пользователя в
        формате {"count": <integer>}.
        """
        return Response(UserNotificationsCountSerializer(request.user).data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=UserCommanderSerializer
    )
    def me_commander(self, request, pk=None):
        """
        Представляет айди структурных единиц, в которых пользователь
        является командиром.
        """
        if request.method == 'GET':
            serializer = UserCommanderSerializer(request.user)
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=UserCommanderSerializer
    )
    def me_trusted(self, request, pk=None):
        """
        Представляет айди структурных единиц, в которых пользователь
        является доверенным.
        """
        if request.method == 'GET':
            serializer = UserTrustedSerializer(request.user)
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=UserCommanderSerializer
    )
    def me_positions(self, request, pk=None):
        """
        Представляет должности текущего юзера на каждом структурном уровне.
        """
        if request.method == 'GET':
            serializer = UserHeadquarterPositionSerializer(request.user)
            return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=UserCommanderSerializer
    )
    def positions(self, request, pk=None):
        """
        Представляет должности юзера по pk на каждом структурном уровне.
        """
        if request.method == 'GET':
            user = get_object_or_404(RSOUser, id=pk)
            serializer = UserHeadquarterPositionSerializer(user)
            return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=UserCommanderSerializer
    )
    def commander(self, request, pk=None):
        """
        Представляет айди структурных единиц, в которых пользователь
        является командиром.
        """
        if request.method == 'GET':
            user = get_object_or_404(RSOUser, id=pk)
            serializer = UserCommanderSerializer(user)
            return Response(serializer.data)


class SafeUserViewSet(RetrieveViewSet):
    """Безопасные для чтения данные пользователя по id.

    Доступно авторизованным пользователям.
    """
    queryset = RSOUser.objects.all()
    serializer_class = SafeUserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class BaseUserViewSet(viewsets.ModelViewSet):
    """
    Базовый класс ViewSet для работы с моделями,
    связанными с пользователем (RSOUser).

    Этот класс предназначен для расширения и создания специализированных
    ViewSets для различных пользовательских моделей. Он обеспечивает полный
    набор CRUD-операций (создание, чтение, обновление, удаление) для моделей,
    связанных с пользователем.

    Атрибуты:
    - permission_classes: используется permissions. IsAuthenticated для
    проверки, что пользователь аутентифицирован.

    Методы:
    - create(request, *args, **kwargs): Обрабатывает POST-запросы для создания
    новой записи. Вызывает описанный ниже perform_create метод.

    - perform_create(serializer): Позволяет связать создаваемую запись с
    текущим (авторизованным) пользователем.

    - retrieve(request, *args, **kwargs): Обрабатывает GET-запросы
    для получения записи текущего пользователя без явного указания ID в урле

    - update(request, *args, **kwargs): Обрабатывает PUT/PATCH-запросы для
    обновления существующей записи текущего пользователя без
    явного указания ID в урле

    - destroy(request, *args, **kwargs): Обрабатывает DELETE-запросы для
    удаления существующей записи текущего пользователя без
    явного указания ID в урле

    Параметры:
    - request: Объект HttpRequest, содержащий данные запроса.
    - args, kwargs: Дополнительные аргументы и ключевые аргументы, переданные
    в метод.

    Возвращаемое значение:
    - Ответ HttpResponse или Response, содержащий данные записи
    (для create, retrieve, update) или пустой ответ (для destroy).
    """

    permission_classes = [permissions.IsAuthenticated,]

    def perform_create(self, serializer):
        user = get_user(self)
        serializer.save(user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserEducationViewSet(BaseUserViewSet):
    """Представляет образовательную информацию пользователя."""

    queryset = UserEducation.objects.all()
    serializer_class = UserEducationSerializer
    permission_classes = (permissions.IsAuthenticated, IsStuffOrAuthor,)
    ordering_fields = ('study_specialty',)

    def get_object(self):
        """Определяет instance для операций с объектом (get, upd, del)."""
        return get_object_or_404(UserEducation, user=self.request.user)


class UserProfessionalEducationViewSet(BaseUserViewSet):
    """Представляет профессиональную информацию пользователя.

    Дополнительные профобразования пользователя доступны по ключу
    'users_prof_educations'.
    """

    queryset = UserProfessionalEducation.objects.all()
    permission_classes = [IsStuffOrAuthor, permissions.IsAuthenticated]
    ordering = ('qualification',)

    def get_object(self):
        return UserProfessionalEducation.objects.filter(
            user_id=self.request.user.id
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserProfessionalEducationSerializer
        return ProfessionalEductionSerializer

    def destroy(self, request, *args, **kwargs):
        """Удаляет профессиональное образование пользователя."""

        queryset = self.get_queryset()
        if not queryset.filter(pk=kwargs['pk']).exists():
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={'detail': 'Нет записи с таким ID.'}
            )
        instance = self.get_queryset().get(pk=kwargs['pk'])
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """Обновляет профессиональное образование пользователя."""

        queryset = self.get_queryset()
        if not queryset.filter(pk=kwargs['pk']).exists():
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={'detail': 'Нет записи с таким ID.'}
            )
        instance = self.get_queryset().get(pk=kwargs['pk'])
        if instance.user_id != self.request.user.id:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
                data={'detail': 'У вас нет прав на изменение этой записи.'}
            )
        if self.action == 'partial_update':
            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=True
            )
        else:
            serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if queryset.filter(user=self.request.user).count() < 5:
            return super().create(request, *args, **kwargs)
        return Response(
            status=status.HTTP_403_FORBIDDEN,
            data={
                'detail': (
                    'Нельзя ввести больше 5 записей о доп. проф. образовании.'
                )
            }
        )


class UserDocumentsViewSet(BaseUserViewSet):
    """Представляет документы пользователя."""

    queryset = UserDocuments.objects.all()
    serializer_class = UserDocumentsSerializer
    permission_classes = (permissions.IsAuthenticated, IsStuffOrAuthor,)

    def get_object(self):
        return get_object_or_404(UserDocuments, user=self.request.user)


class UserForeignParentDocsViewSet(BaseUserViewSet):
    """Документы опекуна иностранного юзера.

        Поддерживаются только GET, POST и DELETE запросы.
        Если запись у данного юзера уже существует, то вызывается
        PATCH-запрос самостоятельно на бэке.
        Если записи нет, то создается новая.
        Таким образом фронт всегда отправляет POST-запрос при создании
        и POST-запрос при обновлении записей.

        DELETE-запрос на этот эндпоинт удаляет и все дополнительные документы.
        Удаление отдельных записей о дополнительных документах реализовано
        на эндпоинте /rsousers/me/foreign_parent_additional_documents/{id}/.

        Пример POST-запроса:
        {
        "name": "foo",
        "foreign_pass_num": "bar",
        "foreign_pass_date": "1970-01-01",
        "foreign_pass_whom": "string",
        "snils": "string",
        "inn": "string",
        "work_book_num": "string",
        "additional_docs": [
            {
            "foreign_doc_name": "string",
            "foreign_doc_num": "string"
            }
        ]
        }

    """

    queryset = UserForeignParentDocs.objects.all()
    serializer_class = UserForeignParentDocsSerializer
    permission_classes = (permissions.IsAuthenticated, IsStuffOrAuthor,)

    def get_object(self):
        return get_object_or_404(UserForeignParentDocs, user=self.request.user)

    @swagger_auto_schema(
                request_body=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=[],
                    properties={
                        'name': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            default='foobar'
                        ),
                        'foreign_pass_num': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            default='XII X IV'
                        ),
                        'foreign_pass_date': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            default='1970-01-01'
                        ),
                        'foreign_pass_whom': openapi.Schema(
                            type=openapi.TYPE_STRING
                        ),
                        'snils': openapi.Schema(
                            type=openapi.TYPE_STRING
                        ),
                        'inn': openapi.Schema(
                            type=openapi.TYPE_STRING
                        ),
                        'work_book_num': openapi.Schema(
                            type=openapi.TYPE_STRING
                        ),
                        'additional_docs': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'foreign_doc_name': openapi.Schema(
                                        type=openapi.TYPE_STRING
                                    ),
                                    'foreign_doc_num': openapi.Schema(
                                        type=openapi.TYPE_STRING
                                    )
                                }
                            )
                        )
                    }
                )
            )
    def create(self, request, *args, **kwargs):
        """
        В методе реализована проверка на наличие записей.
        Если запись у данного юзера уже существует, то вызывается
        partial_update.
        Если записи нет, то создается новая.
        """

        user = self.request.user
        additional_docs = request.data.get('additional_docs', [])
        name = request.data.get('name', None)
        foreign_pass_num = request.data.get('foreign_pass_num', None)
        foreign_pass_date = request.data.get('foreign_pass_date', None)
        foreign_pass_whom = request.data.get('foreign_pass_whom', None)
        snils = request.data.get('snils', None)
        inn = request.data.get('inn', None)
        work_book_num = request.data.get('work_book_num', None)

        try:
            UserForeignParentDocs.objects.get(
                user=user,
            )
            return self.partial_update(request, *args, **kwargs)
        except UserForeignParentDocs.DoesNotExist:
            with transaction.atomic():
                instance = UserForeignParentDocs.objects.create(
                    user=user,
                    name=name,
                    foreign_pass_num=foreign_pass_num,
                    foreign_pass_date=foreign_pass_date,
                    foreign_pass_whom=foreign_pass_whom,
                    snils=snils,
                    inn=inn,
                    work_book_num=work_book_num
                )

                add_docs_serilaizer = AdditionalForeignDocsSerializer(
                    data=additional_docs, many=True)
                add_docs_serilaizer.is_valid(raise_exception=True)
                add_docs_serilaizer.save(foreign_docs=instance)

                return Response(
                    self.get_serializer(instance).data,
                    status=(
                        status.HTTP_201_CREATED
                    )
                )

    def partial_update(self, request, *args, **kwargs):
        """
        Добавление в метод сохранения записей о дополнительных документах.
        """
        user = self.request.user
        instance = UserForeignParentDocs.objects.get(
                user=user,
            )
        additional_docs = request.data.get('additional_docs', [])
        add_docs_serilaizer = AdditionalForeignDocsSerializer(
            data=additional_docs, many=True)
        add_docs_serilaizer.is_valid(raise_exception=True)
        add_docs_serilaizer.save(foreign_docs=instance)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Удаляет документы родительского пользователя
        вместе со всеми дополнительными документами.
        """
        instance = UserForeignParentDocs.objects.get(
                user=self.request.user,
            )
        AdditionalForeignDocs.objects.filter(foreign_docs=instance).delete()
        return super().destroy(request, *args, **kwargs)


class AdditionalForeignDocsViewSet(BaseUserViewSet):
    """Дополнительные документы иностранного пользователя.

    DELETE-запрос при передаче id удаляет отдельные записи.
    """

    queryset = AdditionalForeignDocs.objects.all()
    serializer_class = AdditionalForeignDocsSerializer
    permission_classes = (
        permissions.IsAuthenticated, IsForeignAdditionalDocsAuthor,
    )


class ForeignUserDocumentsViewSet(BaseUserViewSet):
    """Представляет документы иностранного пользователя."""

    # queryset = UserForeignDocuments.objects.all()
    serializer_class = ForeignUserDocumentsSerializer
    permission_classes = (permissions.IsAuthenticated, IsStuffOrAuthor,)

    def get_object(self):
        return get_object_or_404(UserForeignDocuments, user=self.request.user)


class UserRegionViewSet(BaseUserViewSet):
    """Представляет информацию о проживании пользователя.

    GET-запрос на /regions/users_list выдает пагинированный ответ
    с личной информацией всех пользователей сайта.
    GET-запрос на /regions/download_xlsx_users_data выгружает
    таблицу с личной информацией всех пользователей в формате xlsx.
    Доступ - админ или командир ЦШ.
    """

    FIRST_ROW = 1
    FIRST_ROW_HEIGHT = 55
    ROW_FILTER_CELLS = 'A1:BZ1'
    FREEZE_HEADERS_ROW = 'D2'
    ZOOM_SCALE = 80
    EXCEL_HEADERS = [
            'Код региона прописки',
            'Регион прописки',
            'ID юзера',
            'Имя',
            'Фамилия',
            'Отчество',
            'Username',
            'Дата рождения',
            'Наличие паспорта РФ',
            'Серия и номер паспорта',
            'Кем выдан паспорт',
            'Дата выдачи паспорта',
            'Код подразделения',
            'ИНН',
            'СНИЛС',
            'Город прописки',
            'Адрес прописки',
            'Совпадает с фактическим адресом проживания',
            'Фактический регион ID',
            'Регион фактического проживания',
            'Город фактического проживания',
            'Адрес фактического проживания',
            'Название ОО',
            'Факультет',
            'Специальность',
            'Курс',
            'Телефон',
            'Email',
            'Ссылка на ВК',
            'Ссылка на Telegram',
            'Статус членства в РСО',
            'Статус верификации',
            'Статус оплаты членского взноса',
            'Член ЦШ',
            'Должность в ЦШ',
            'Командир ЦШ',
            'Член окружного штаба',
            'Должность в окр. штабе',
            'Командир окр.штаба',
            'Член регионального штаба',
            'Должность в рег. штабе',
            'Командир рег.штаба',
            'Член местного штаба',
            'Должность в мест. штабе',
            'Командир местного штаба',
            'Член образ. штаба',
            'Должность в образ. штабе',
            'Командир образ. штаба',
            'Член отряда',
            'Направление отряда(участник)',
            'Должность в отряде',
            'Командир отряда',
            'Направление отряда(командир)',
        ]
    data_for_excel = []
    queryset = UserRegion.objects.all()

    @staticmethod
    def get_objects_data(cls, request):
        """Отсортированный кверисет для вывода на лист Excel."""

        queryset = cls.filter_queryset(cls.get_queryset())
        queryset = queryset.order_by('reg_region')
        serializer = cls.get_serializer(queryset, many=True)
        return serializer.data

    def get_permissions(self):
        if self.action == 'list' or self.action == 'get_xlsx_users_data':
            permission_classes = (
                permissions.IsAuthenticated(), OnlyStuffOrCentralCommander(),
            )
            return permission_classes
        else:
            permission_classes = (
                permissions.IsAuthenticated(), IsStuffOrAuthor(),
            )
        return permission_classes

    @method_decorator(cache_page(settings.RSOUSERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        return get_object_or_404(UserRegion, user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'get_xlsx_users_data':
            serializer_class = UserIdRegionSerializer
        else:
            serializer_class = UserRegionSerializer
        return serializer_class

    @action(
            methods=['get'],
            detail=False,
            permission_classes=(permissions.IsAdminUser,),
    )
    def get_xlsx_users_data(self, request):
        # file_path = os.path.join(
        #     str(settings.BASE_DIR),
        #     'media',
        #     'users_data.xlsx'
        # )

        file_stream = io.BytesIO()
        workbook = Workbook()

        worksheet = workbook.active

        """Настройка формата отображения листа."""
        worksheet.auto_filter.ref = self.ROW_FILTER_CELLS
        worksheet.append(self.EXCEL_HEADERS)
        worksheet.row_dimensions[self.FIRST_ROW].height = self.FIRST_ROW_HEIGHT
        worksheet.sheet_view.zoomScale = self.ZOOM_SCALE
        worksheet.freeze_panes = self.FREEZE_HEADERS_ROW

        self.data_for_excel = self.get_objects_data(
            self, request
        )
        for item in self.data_for_excel:
            worksheet.append(list(dict(item).values()))
        workbook.save(file_stream)
        self.data_for_excel.clear()
        # return download_file(
        #     file_stream.getvalue(), 'users_data.xlsx', reading_mode='rb'
        # )
        response = HttpResponse(
            file_stream.getvalue(),
            content_type=(
                'application/'
                'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        )
        response['Content-Disposition'] = (
            'attachment; filename="%s.xlsx"' % 'users_data'
        )

        return response


class UserPrivacySettingsViewSet(BaseUserViewSet):
    """Представляет настройки приватности пользователя."""

    queryset = UserPrivacySettings.objects.all()
    serializer_class = UserPrivacySettingsSerializer
    permission_classes = (permissions.IsAuthenticated, IsStuffOrAuthor,)

    def get_object(self):
        return get_object_or_404(UserPrivacySettings, user=self.request.user)


class UserMediaViewSet(BaseUserViewSet):
    """Представляет медиа-данные пользователя."""

    queryset = UserMedia.objects.all()
    serializer_class = UserMediaSerializer
    permission_classes = (permissions.IsAuthenticated, IsStuffOrAuthor,)

    def get_object(self):
        return get_object_or_404(UserMedia, user=self.request.user)


class UserStatementDocumentsViewSet(BaseUserViewSet):
    """Представляет заявление на вступление в РСО пользователя."""

    queryset = UserStatementDocuments.objects.all()
    serializer_class = UserStatementDocumentsSerializer

    def get_object(self):
        return get_object_or_404(
            UserStatementDocuments,
            user=self.request.user
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_membership_file(self, request):
        """Скачивание бланка заявления на вступление в РСО.

        Эндпоинт для скачивания
        /users/me/statement/download_membership_statement_file/
        """

        filename = 'rso_membership_statement.rtf'
        filepath = settings.BASE_DIR.joinpath(
            'templates', 'membership', filename
        )
        return download_file(filepath, filename)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_consent_personal_data(self, request):
        """Скачивание бланка согласия на обработку персональных данных.

        Эндпоинт для скачивания
        /users/me/statement/download_consent_to_the_processing_of_personal_data/
        """

        filename = 'consent_to_the_processing_of_personal_data.rtf'
        filepath = settings.BASE_DIR.joinpath(
            'templates',  'membership', filename
        )
        return download_file(filepath, filename)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_parent_consent_personal_data(self, request):
        """
        Скачивание бланка согласия законного представителя
        на обработку персональных данных несовершеннолетнего.
        Эндпоинт для скачивания
        /users/me/statement/download_parent_consent_to_the_processing_of_personal_data/
        """

        filename = (
            'download_parent_consent_to_the_processing_of_personal_data.rtf'
        )
        filepath = settings.BASE_DIR.joinpath(
            'templates', 'membership', filename
        )
        return download_file(filepath, filename)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_all_forms(self, _):
        """Скачивание архива с бланками.

        В архиве все три бланка для подачи заявления на вступление в РСО.
        Архив доступен по эндпоинту /users/me/statement/download_all_forms/
        """

        filepath = settings.BASE_DIR.joinpath('templates', 'membership')
        zip_filename = settings.BASE_DIR.joinpath(
            'templates', 'entry_forms.zip'
        )
        file_dir = os.listdir(filepath)
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in file_dir:
                zipf.write(os.path.join(filepath, file), file)
        zipf.close()
        filepath = settings.BASE_DIR.joinpath('templates', 'entry_forms.zip')
        path = open(filepath, 'rb')
        mime_type, _ = mimetypes.guess_type(filepath)
        response = HttpResponse(path, content_type=mime_type)
        response['Content-Disposition'] = (
                'attachment; filename=%s' % 'entry_forms.zip'
        )
        os.remove(filepath)
        return response


class UsersParentViewSet(BaseUserViewSet):
    """Представляет законного представителя пользователя."""

    queryset = UserParent.objects.all()
    serializer_class = UsersParentSerializer
    permission_classes = (permissions.IsAuthenticated, IsStuffOrAuthor,)

    def get_object(self):
        return get_object_or_404(UserParent, user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def apply_for_verification(request):
    """Подать заявку на верификацию."""
    if request.method == 'POST':
        user = request.user
        try:
            UserVerificationRequest.objects.get(user=user)
            return Response(
                {'error': 'Вы уже подали заявку на верификацию'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except UserVerificationRequest.DoesNotExist:
            pass
        if user.is_verified:
            return Response(
                {'error': 'Пользователь уже верифицирован'},
                status=status.HTTP_400_BAD_REQUEST
            )
        UserVerificationRequest.objects.create(
            user=user
        )
        return Response(status=status.HTTP_201_CREATED)


class UserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = RSOUser.objects.all()

        if self.q:
            qs = qs.filter(
                Q(username__icontains=self.q) |
                Q(first_name__icontains=self.q) |
                Q(last_name__icontains=self.q) |
                Q(patronymic_name__icontains=self.q)
            )
        return qs.order_by('last_name')
