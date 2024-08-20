from dal import autocomplete
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, status, viewsets, mixins
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from api.mixins import (CreateDeleteViewSet, ListRetrieveUpdateViewSet,
                        ListRetrieveViewSet)
from api.permissions import (IsDetachmentCommander, IsDistrictCommander,
                             IsEducationalCommander, IsLocalCommander,
                             IsRegionalCommander, IsStuffOrCentralCommander,
                             IsStuffOrCentralCommanderOrTrusted,
                             IsUserModelPositionCommander)
from api.utils import get_headquarter_users_positions_queryset
from headquarters.filters import (DetachmentFilter,
                                  EducationalHeadquarterFilter,
                                  LocalHeadquarterFilter,
                                  RegionalHeadquarterFilter,
                                  DetachmentListFilter,
                                  )

from headquarters.mixins import (ApplicationsMixin, VerificationsMixin, SubRegionalHqsMixin,
                                 SubDistrictHqsMixin, SubLocalHqsMixin, SubEducationalHqsMixin,
                                 DetachmentLeadershipMixin, BaseLeadershipMixin, CentralSubCommanderMixin,
                                 RegionalSubCommanderMixin, LocalSubCommanderMixin, EducationalSubCommanderMixin,
                                 DistrictSubCommanderMixin)
from headquarters.models import (CentralHeadquarter, Detachment,
                                 DistrictHeadquarter, EducationalHeadquarter,
                                 EducationalInstitution, LocalHeadquarter,
                                 Position, Region, RegionalHeadquarter,
                                 UserCentralHeadquarterPosition,
                                 UserDetachmentApplication,
                                 UserDetachmentPosition,
                                 UserDistrictHeadquarterPosition,
                                 UserEducationalHeadquarterPosition,
                                 UserLocalHeadquarterPosition,
                                 UserRegionalHeadquarterPosition,
                                 UserCentralApplication,
                                 UserDistrictApplication,
                                 UserEducationalApplication,
                                 UserLocalApplication,
                                 UserRegionalApplication)
from headquarters.registry_serializers import (
    DetachmentRegistrySerializer, DistrictHeadquarterRegistrySerializer,
    EducationalHeadquarterRegistrySerializer,
    LocalHeadquarterRegistrySerializer, RegionalHeadquarterRegistrySerializer)
from headquarters.serializers import (
    CentralHeadquarterSerializer, CentralPositionSerializer,
    DetachmentPositionSerializer, DetachmentSerializer,
    DistrictHeadquarterSerializer, DistrictPositionSerializer,
    EducationalHeadquarterSerializer, EducationalPositionSerializer,
    LocalHeadquarterSerializer, LocalPositionSerializer, PositionSerializer,
    RegionalHeadquarterSerializer, RegionalPositionSerializer,
    ShortDetachmentListSerializer, ShortDetachmentSerializer,
    ShortDistrictHeadquarterListSerializer, ShortDistrictHeadquarterSerializer,
    ShortEducationalHeadquarterListSerializer,
    ShortEducationalHeadquarterSerializer, ShortLocalHeadquarterListSerializer,
    ShortLocalHeadquarterSerializer, ShortRegionalHeadquarterListSerializer,
    ShortRegionalHeadquarterSerializer, UserCentralApplicationReadSerializer,
    UserDetachmentApplicationReadSerializer,
    UserDetachmentApplicationSerializer,
    UserEducationalApplicationSerializer,
    UserLocalApplicationSerializer, UserLocalApplicationShortReadSerializer,
    UserRegionalApplicationSerializer, DetachmentListSerializer,
    UserCentralApplicationSerializer,
    UserDetachmentApplicationShortReadSerializer,
    UserDistrictApplicationReadSerializer, UserDistrictApplicationSerializer,
    UserDistrictApplicationShortReadSerializer,
    UserEducationalApplicationReadSerializer,
    UserEducationalApplicationShortReadSerializer,
    UserLocalApplicationReadSerializer,
    UserRegionalApplicationReadSerializer,
    UserRegionalApplicationShortReadSerializer,
    UserCentralApplicationShortReadSerializer,)
from headquarters.swagger_schemas import applications_response
from headquarters.utils import (create_central_hq_member,
                                get_regional_hq_members_to_verify,
                                get_detachment_members_to_verify,)
from users.serializers import UserVerificationReadSerializer


class PositionViewSet(ListRetrieveViewSet):
    """Представляет должности для юзеров.

    Доступны только операции чтения.
    """

    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    ordering = ('name',)

    @method_decorator(cache_page(settings.POSITIONS_LIST_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CentralViewSet(ApplicationsMixin, 
                     BaseLeadershipMixin, 
                     CentralSubCommanderMixin, 
                     ListRetrieveUpdateViewSet):
    """Представляет центральные штабы.

    При операции чтения доступно число количества участников в структурной
    единице по ключу members_count, а также список всех участников по ключу
    members.
    Доступен поиск по name при передаче ?search=<value> query-параметра.
    Доступна фильтрация по ключу user_id для applications.
    """

    queryset = CentralHeadquarter.objects.all()
    serializer_class = CentralHeadquarterSerializer
    permission_classes = (IsStuffOrCentralCommander,)
    ordering = ('name',)

    @method_decorator(cache_page(settings.CENTRAL_OBJECT_CACHE_TTL))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = (permissions.IsAdminUser,)
        else:
            permission_classes = (IsStuffOrCentralCommanderOrTrusted,)
        return [permission() for permission in permission_classes]

    def get_application_model(self):
        return UserCentralApplication

    def get_application_serializer(self):
        return UserCentralApplicationReadSerializer

    def get_application_short_serializer(self):
        return UserCentralApplicationShortReadSerializer


class DistrictViewSet(ApplicationsMixin, 
                      SubDistrictHqsMixin, 
                      BaseLeadershipMixin, 
                      DistrictSubCommanderMixin, 
                      viewsets.ModelViewSet):
    """Представляет окружные штабы.

    Привязывается к центральному штабу по ключу central_headquarter.
    При операции чтения доступно число количества участников в структурной
    единице по ключу members_count, а также список всех участников по ключу
    members.
    Доступен поиск по name при передаче ?search=<value> query-параметра.
    Сортировка по умолчанию - количество участников
    Доступна сортировка по ключу ordering по полям name и founding_date.
    При указании registry=True в качестве query_param, выводит список объектов,
    адаптированный под блок "Реестр участников".
    Доступна фильтрация по ключу user_id для applications.
    """

    queryset = DistrictHeadquarter.objects.all()
    serializer_class = DistrictHeadquarterSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ('name', 'founding_date')
    ordering_fields = ('name', 'founding_date')
    ordering = ('name', 'founding_date')

    def get_serializer_class(self):
        if (
                self.request.query_params.get('registry') == 'true' and
                self.action == 'list'
        ):
            return DistrictHeadquarterRegistrySerializer
        if self.action == 'list':
            return ShortDistrictHeadquarterListSerializer
        return DistrictHeadquarterSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = (IsStuffOrCentralCommanderOrTrusted,)
        else:
            permission_classes = (IsDistrictCommander,)
        return [permission() for permission in permission_classes]

    @method_decorator(cache_page(settings.DISTR_OBJECT_CACHE_TTL))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_application_model(self):
        return UserDistrictApplication

    def get_application_serializer(self):
        return UserDistrictApplicationReadSerializer

    def get_application_short_serializer(self):
        return UserDistrictApplicationShortReadSerializer
    
    

class RegionalViewSet(ApplicationsMixin, 
                      VerificationsMixin, 
                      SubRegionalHqsMixin, 
                      BaseLeadershipMixin,
                      RegionalSubCommanderMixin, 
                      viewsets.ModelViewSet):
    """Представляет региональные штабы.

    Привязывается к окружному штабу по ключу district_headquarter (id).
    Привязывается к региону по ключу region (id).
    При операции чтения доступно число количества участников в структурной
    единице по ключу members_count, а также список всех участников по ключу
    members.
    При операции чтения доступен список пользователей, подавших заявку на
    верификацию и относящихся к тому же региону, что и текущий региональный
    штаб, по ключу users_for_verification.
    Доступен поиск по name при передаче ?search=<value> query-параметра.
    Доступна сортировка по ключам name, founding_date, count_related.
    Сортировка по умолчанию - количество участников.
    Доступна фильтрация по Окружным Штабам. Ключ - district_headquarter__name.
    Доступна фильтрация по имени региона. Ключ - region.
    Доступна сортировка по ключу ordering по полям name и founding_date.
    При указании registry=True в качестве query_param, выводит список объектов,
    адаптированный под блок "Реестр участников".
    Доступна фильтрация для applications и verifications по ключу user_id.
    """

    queryset = RegionalHeadquarter.objects.all()
    filter_backends = (
        filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter
    )
    search_fields = ('name', 'region__name',)
    ordering_fields = ('name', 'founding_date',)
    filterset_class = RegionalHeadquarterFilter

    @method_decorator(cache_page(settings.REGIONALS_LIST_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if (
                self.request.query_params.get('registry') == 'true' and
                self.action == 'list'
        ):
            return RegionalHeadquarterRegistrySerializer
        if self.action == 'list':
            return ShortRegionalHeadquarterListSerializer
        return RegionalHeadquarterSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = (IsDistrictCommander,)
        else:
            permission_classes = (IsRegionalCommander,)
        return [permission() for permission in permission_classes]

    @method_decorator(cache_page(settings.REG_OBJECT_CACHE_TTL))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_application_model(self):
        return UserRegionalApplication

    def get_application_serializer(self):
        return UserRegionalApplicationReadSerializer

    def get_application_short_serializer(self):
        return UserRegionalApplicationShortReadSerializer

    def get_verification_serializer(self):
        return UserVerificationReadSerializer

    def get_func_members_to_verify(self):
        return get_regional_hq_members_to_verify


class LocalViewSet(ApplicationsMixin, 
                   VerificationsMixin, 
                   SubLocalHqsMixin, 
                   BaseLeadershipMixin,
                   LocalSubCommanderMixin, 
                   viewsets.ModelViewSet):
    """Представляет местные штабы.

    Привязывается к региональному штабу по ключу regional_headquarter (id).
    При операции чтения доступно число количества участников в структурной
    единице по ключу members_count, а также список всех участников по ключу
    members.
    Доступен поиск по name при передаче ?search=<value> query-параметра.
    Доступна сортировка по ключам name, founding_date, count_related.
    Доступна фильтрация по РШ и ОШ. Ключи - regional_headquarter__name,
    district_headquarter__name.
    Доступна сортировка по ключу ordering по полям name и founding_date.
    При указании registry=True в качестве query_param, выводит список объектов,
    адаптированный под блок "Реестр участников".
    Доступна фильтрация по ключу user_id для applications.
    """

    queryset = LocalHeadquarter.objects.all()
    filter_backends = (
        filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter
    )
    search_fields = ('name',)
    ordering_fields = ('name', 'founding_date',)
    filterset_class = LocalHeadquarterFilter

    @method_decorator(cache_page(settings.LOCALS_LIST_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if (
                self.request.query_params.get('registry') == 'true' and
                self.action == 'list'
        ):
            return LocalHeadquarterRegistrySerializer
        if self.action == 'list':
            return ShortLocalHeadquarterListSerializer
        return LocalHeadquarterSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = (IsRegionalCommander,)
        else:
            permission_classes = (IsLocalCommander,)
        return [permission() for permission in permission_classes]

    def get_application_model(self):
        return UserLocalApplication

    def get_application_serializer(self):
        return UserLocalApplicationReadSerializer

    def get_application_short_serializer(self):
        return UserLocalApplicationShortReadSerializer


class EducationalViewSet(ApplicationsMixin, 
                         SubEducationalHqsMixin, 
                         BaseLeadershipMixin, 
                         EducationalSubCommanderMixin, 
                         viewsets.ModelViewSet):
    """Представляет образовательные штабы.

    Может привязываться к местному штабу по ключу local_headquarter (id).
    Привязывается к региональному штабу по ключу regional_headquarter (id).
    Привязывается к образовательному институту по ключу educational_institution
    (id).
    Установлена валидация соответствия всех связанных штабов на наличие
    связи между собой.
    При операции чтения доступно число количества участников в структурной
    единице по ключу members_count, а также список всех участников по ключу
    members.
    Доступен поиск по name при передаче ?search=<value> query-параметра.
    Доступна сортировка по ключам name, founding_date, count_related.
    Доступна фильтрация по РШ, ОШ и ОИ. Ключи - regional_headquarter__name,
    district_headquarter__name, local_headquarter__name.
    Доступна сортировка по ключу ordering по полям name и founding_date.
    При указании registry=True в качестве query_param, выводит список объектов,
    адаптированный под блок "Реестр участников".
    Доступна фильтрация по ключу user_id для applications.
    """

    queryset = EducationalHeadquarter.objects.all()
    filter_backends = (
        filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter
    )
    search_fields = ('name',)
    filterset_class = EducationalHeadquarterFilter
    ordering_fields = ('name', 'founding_date',)

    @method_decorator(cache_page(settings.EDUCATIONALS_LIST_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if (
                self.request.query_params.get('registry') == 'true' and
                self.action == 'list'
        ):
            return EducationalHeadquarterRegistrySerializer
        if self.action == 'list':
            return ShortEducationalHeadquarterListSerializer
        return EducationalHeadquarterSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = (IsLocalCommander,)
        else:
            permission_classes = (IsEducationalCommander,)
        return [permission() for permission in permission_classes]

    def get_application_model(self):
        return UserEducationalApplication

    def get_application_serializer(self):
        return UserEducationalApplicationReadSerializer

    def get_application_short_serializer(self):
        return UserEducationalApplicationShortReadSerializer


class DetachmentViewSet(ApplicationsMixin, 
                        VerificationsMixin, 
                        DetachmentLeadershipMixin, 
                        viewsets.ModelViewSet):
    """Представляет информацию об отряде.

    Может привязываться к местному штабу по ключу local_headquarter (id).
    Может привязываться к образовательному штабу по ключу
    educational_headquarter (id).
    Привязывается к региональному штабу по ключу regional_headquarter (id).
    Привязывается к направлению по ключу area (id).
    Установлена валидация соответствия всех связанных штабов на наличие
    связи между собой.
    При операции чтения доступно число количества участников в структурной
    единице по ключу members_count, а также список всех участников по эндпоинту
    /members/.
    При операции чтения доступен список пользователей, подавших заявку на
    верификацию и относящихся к текущему отряду по
    эндпоинту /verifications/.
    При операции чтения доступен список пользователей, подавших заявку на
    вступление в отряд по эндпоинту /applications/.
    Доступен поиск по name при передаче ?search=<value> query-параметра.
    Доступны фильтры по ключам name, founding_date, count_related.
    Доступна фильтрация по ключам area__name, educational_institution__name.
    Доступна сортировка по ключу ordering по полям name и founding_date.
    При указании registry=True в качестве query_param, выводит список объектов,
    адаптированный под блок "Реестр участников".
    Доступна фильтрация для applications и verifications по ключу user_id.
    """

    queryset = Detachment.objects.all()
    filter_backends = (
        filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter
    )
    search_fields = ('name',)
    filterset_class = DetachmentFilter
    ordering_fields = ('name', 'founding_date',)

    @method_decorator(cache_page(settings.DETACHMENT_LIST_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if (
                self.request.query_params.get('registry') == 'true' and
                self.action == 'list'
        ):
            return DetachmentRegistrySerializer
        if self.action == 'list':
            return ShortDetachmentListSerializer
        return DetachmentSerializer

    def get_permissions(self):
        if self.action == 'create':
            #TODO: вернуть обратно после запрета юзерам создавать отряды
            # permission_classes = (IsEducationalCommander,)
            permission_classes = (permissions.IsAuthenticated,)
            return [permission() for permission in permission_classes]
        permission_classes = (IsDetachmentCommander, )
        return [permission() for permission in permission_classes]

    def get_application_model(self):
        return UserDetachmentApplication

    def get_application_serializer(self):
        return UserDetachmentApplicationReadSerializer

    def get_verification_serializer(self):
        return UserVerificationReadSerializer

    def get_application_short_serializer(self):
        return UserDetachmentApplicationShortReadSerializer

    def get_func_members_to_verify(self):
        return get_detachment_members_to_verify


class BasePositionViewSet(viewsets.ModelViewSet):
    """Базовый вьюсет для просмотра/изменения участников штабов.

    Необходимо переопределять метод get_queryset и атрибут serializer_class.
    """

    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    ordering_fields = ('user__last_name', 'user__date_of_birth')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__patronymic_name'
    )
    permission_classes = (IsUserModelPositionCommander,)
    serializer_class = None

    @method_decorator(cache_page(settings.HEADQUARTERS_MEMBERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def filter_by_user_id(self, queryset):
        """Фильтрация участников структурной единицы по user_id."""
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset

    def filter_by_trusted_user_id(self, queryset):
        """Фильтрация участников структурной единицы по user_id."""
        user_id = self.request.query_params.get('trusted_user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id, is_trusted=True)
        return queryset

    def filter_by_name(self, queryset):
        """Фильтрация участников структурной единицы по имени (first_name)."""
        search_by_name = self.request.query_params.get('search', None)
        if search_by_name:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_by_name) |
                Q(user__last_name__icontains=search_by_name)
            )
        return queryset

    def get_object(self):
        queryset = self.get_queryset()
        member_pk = self.kwargs.get('membership_pk')
        try:
            obj = queryset.get(pk=member_pk)
        # TODO: не лучшая практика, но пока не вижу более правильного решения
        # TODO: в действительности мы ловим DoesNotExist для дочерних классов
        # TODO: edit - можно добавить маппинг. Сделать позднее.
        except Exception:
            raise Http404('Не найден участник по заданному id членства.')
        return obj

    def get_queryset(self):
        """К переопределению."""
        pass


class CentralPositionViewSet(BasePositionViewSet):
    """Просмотреть участников и изменить уровень доверенности/позиции.

    Доступно только командиру.

    Доступен поиск по username, first_name, last_name, patronymic_name
    Доступен фильтр по user_id: `?user_id=<int>`
    Доступен фильтр по trusted_user_id: `?trusted_user_id=<int>`
    Доступна сортировка по ключу ordering по следующим полям:
    user__last_name, user__date_of_birth
    """

    permission_classes = (IsStuffOrCentralCommander,)
    serializer_class = CentralPositionSerializer
    ordering_fields = ('user__last_name', 'user__date_of_birth',)

    def get_queryset(self):
        return self.filter_by_user_id(self.filter_by_trusted_user_id(get_headquarter_users_positions_queryset(
            self,
            CentralHeadquarter,
            UserCentralHeadquarterPosition
        )))

    @method_decorator(cache_page(settings.CENTRALHQ_MEMBERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class DistrictPositionViewSet(BasePositionViewSet):
    """Просмотреть участников и изменить уровень доверенности/позиции.

    Доступно только командиру.

    Доступен поиск по username, first_name, last_name, patronymic_name
    Доступен фильтр по user_id: `?user_id=<int>`
    Доступен фильтр по trusted_user_id: `?trusted_user_id=<int>`
    Доступна сортировка по ключу ordering по следующим полям:
    user__last_name, user__date_of_birth

    """

    serializer_class = DistrictPositionSerializer

    def get_queryset(self):
        return self.filter_by_user_id(self.filter_by_trusted_user_id(get_headquarter_users_positions_queryset(
            self,
            DistrictHeadquarter,
            UserDistrictHeadquarterPosition
        )))

    @method_decorator(cache_page(settings.DISTRCICTHQ_MEMBERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RegionalPositionViewSet(BasePositionViewSet):
    """Просмотреть участников и изменить уровень доверенности/позиции.

    Доступно только командиру.

    Доступен поиск по username, first_name, last_name, patronymic_name
    Доступен фильтр по user_id: `?user_id=<int>`
    Доступен фильтр по trusted_user_id: `?trusted_user_id=<int>`
    Доступна сортировка по ключу ordering по следующим полям:
    user__last_name, user__date_of_birth
    """

    serializer_class = RegionalPositionSerializer

    @method_decorator(cache_page(settings.HEADQUARTERS_MEMBERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return self.filter_by_user_id(self.filter_by_trusted_user_id(get_headquarter_users_positions_queryset(
            self,
            RegionalHeadquarter,
            UserRegionalHeadquarterPosition
        )))


class LocalPositionViewSet(BasePositionViewSet):
    """Просмотреть участников и изменить уровень доверенности/позиции.

    Доступно только командиру.

    Доступен поиск по username, first_name, last_name, patronymic_name
    Доступен фильтр по user_id: `?user_id=<int>`
    Доступен фильтр по trusted_user_id: `?trusted_user_id=<int>`
    Доступна сортировка по ключу ordering по следующим полям:
    user__last_name, user__date_of_birth
    """

    serializer_class = LocalPositionSerializer

    @method_decorator(cache_page(settings.HEADQUARTERS_MEMBERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return self.filter_by_user_id(self.filter_by_trusted_user_id(get_headquarter_users_positions_queryset(
            self,
            LocalHeadquarter,
            UserLocalHeadquarterPosition
        )))


class EducationalPositionViewSet(BasePositionViewSet):
    """Просмотреть участников и изменить уровень доверенности/позиции.

    Доступно только командиру.

    Доступен поиск по username, first_name, last_name, patronymic_name
    Доступен фильтр по user_id: `?user_id=<int>`
    Доступен фильтр по trusted_user_id: `?trusted_user_id=<int>`
    Доступна сортировка по ключу ordering по следующим полям:
    user__last_name, user__date_of_birth
    """

    serializer_class = EducationalPositionSerializer

    @method_decorator(cache_page(settings.HEADQUARTERS_MEMBERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return self.filter_by_user_id(self.filter_by_trusted_user_id(get_headquarter_users_positions_queryset(
            self,
            EducationalHeadquarter,
            UserEducationalHeadquarterPosition
        )))


class DetachmentPositionViewSet(BasePositionViewSet):
    """Просмотреть участников и изменить уровень доверенности/позиции.

    Доступно только командиру.

    Доступен поиск по username, first_name, last_name, patronymic_name.
    Доступен фильтр по user_id: `?user_id=<int>`
    Доступен фильтр по trusted_user_id: `?trusted_user_id=<int>`
    Доступна сортировка по ключу ordering по следующим полям:
    user__last_name, user__date_of_birth.
    """

    serializer_class = DetachmentPositionSerializer

    @method_decorator(cache_page(settings.HEADQUARTERS_MEMBERS_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return self.filter_by_user_id(self.filter_by_trusted_user_id(get_headquarter_users_positions_queryset(
            self,
            Detachment,
            UserDetachmentPosition
        )))


class BaseAcceptRejectViewSet(CreateDeleteViewSet):
    """Базовый вьюсет для принятия и отклонения заявок."""

    application_model = None
    position_model = None
    serializer_class = None
    headquarter_model = None
    permission_classes = ()

    def perform_create(self, serializer):

        headquarter_id = self.kwargs.get('pk')
        application_id = self.kwargs.get('application_pk')
        application = get_object_or_404(
            self.application_model, id=application_id
        )
        user = application.user
        headquarter = get_object_or_404(
            self.headquarter_model, id=headquarter_id
        )
        application.delete()
        serializer.save(user=user, headquarter=headquarter)

    @swagger_auto_schema(
                request_body=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=[],
                    properties={}
                            )
                        )
    def create(self, request, *args, **kwargs):
        """Добавляет пользователя в отряд/штаб, удаляя заявку.

        id - pk отряда/штаба.
        application_id - pk заявки.
        """
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'detail': e}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Отклоняет (удаляет) заявку пользователя."""
        application_id = self.kwargs.get('application_pk')
        application = get_object_or_404(
            self.application_model, id=application_id
        )
        application.delete()
        return Response(
            {'success': 'Заявка отклонена'}, status=status.HTTP_204_NO_CONTENT
        )


class DetachmentAcceptViewSet(BaseAcceptRejectViewSet):
    """Принять/отклонить заявку участника в отряд по ID заявки.

    Доступ - командир отряда.
    id - pk отряда
    application_id - pk заявки.
    """

    application_model = UserDetachmentApplication
    position_model = UserDetachmentPosition
    headquarter_model = Detachment
    serializer_class = DetachmentPositionSerializer
    permission_classes = (IsDetachmentCommander,)


class EducationalAcceptViewSet(BaseAcceptRejectViewSet):
    """Принять/отклонить заявку участника в СО ОО по ID заявки.

    Доступ - командир образовательного штаба.
    id - pk штаба.
    application_id - pk заявки.
    """

    application_model = UserEducationalApplication
    position_model = UserEducationalHeadquarterPosition
    headquarter_model = EducationalHeadquarter
    serializer_class = EducationalPositionSerializer
    permission_classes = (IsEducationalCommander,)


class LocalAcceptViewSet(BaseAcceptRejectViewSet):
    """Принять/отклонить заявку участника в МШ по ID заявки.

    Доступ - командир местного штаба.
    id - pk штаба.
    application_id - pk заявки.
    """

    application_model = UserLocalApplication
    position_model = UserLocalHeadquarterPosition
    headquarter_model = LocalHeadquarter
    serializer_class = LocalPositionSerializer
    permission_classes = (IsLocalCommander,)


class RegionalAcceptViewSet(BaseAcceptRejectViewSet):
    """Принять/отклонить заявку участника в РШ по ID заявки.

    Доступ - командир регионального штаба.
    id - pk штаба.
    application_id - pk заявки.
    """

    application_model = UserRegionalApplication
    position_model = UserRegionalHeadquarterPosition
    headquarter_model = RegionalHeadquarter
    serializer_class = RegionalPositionSerializer
    permission_classes = (IsRegionalCommander,)


class DistrictAcceptViewSet(BaseAcceptRejectViewSet):
    """Принять/отклонить заявку участника в Окружной штаб по ID заявки.

    Доступ - командир окружного штаба.
    id - pk штаба.
    application_id - pk заявки.
    """

    application_model = UserDistrictApplication
    position_model = UserDistrictHeadquarterPosition
    headquarter_model = DistrictHeadquarter
    serializer_class = DistrictPositionSerializer
    permission_classes = (IsDistrictCommander,)


class CentralAcceptViewSet(CreateDeleteViewSet):
    """Принять/отклонить заявку участника в Центральной штаб по ID заявки.

    Доступ - командир центрального штаба.
    id - pk штаба.
    application_id - pk заявки.
    """

    application_model = UserCentralApplication
    position_model = UserCentralHeadquarterPosition
    headquarter_model = CentralHeadquarter
    serializer_class = CentralPositionSerializer
    pagination_class = IsStuffOrCentralCommander

    @swagger_auto_schema(
                request_body=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=[],
                    properties={}
                            )
                        )
    def create(self, request, *args, **kwargs):

        application_pk = self.kwargs.get('application_pk')
        user_id = get_object_or_404(
            UserCentralApplication,
            pk=application_pk
        ).user_id
        headquarter_id = self.kwargs.get('pk')
        if headquarter_id != settings.CENTRAL_HEADQUARTER_ID:
            return Response(status=status.HTTP_404_NOT_FOUND)
        application = get_object_or_404(
            self.application_model, id=application_pk
        )
        with transaction.atomic():
            create_central_hq_member(
                headquarter_id=headquarter_id,
                user_id=user_id,
            )
            application.delete()
        return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Отклоняет (удаляет) заявку пользователя."""
        application_id = self.kwargs.get('application_pk')
        application = get_object_or_404(
            self.application_model, id=application_id
        )
        application.delete()
        return Response(
            {'success': 'Заявка отклонена'}, status=status.HTTP_204_NO_CONTENT
        )


class BaseApplicationViewSet(viewsets.ModelViewSet):
    """Базовый вьюсет для подачи и отмены заявок."""

    application_model = None
    serializer_class = None
    position_model = None
    target_model = None
    permission_classes = ()

    def get_queryset(self):
        headquarter_id = self.kwargs.get('pk')
        headquarter = get_object_or_404(self.target_model, id=headquarter_id)
        return self.application_model.objects.filter(headquarter=headquarter)

    def perform_create(self, serializer):
        user = self.request.user
        target_id = self.kwargs.get('pk')
        target = get_object_or_404(self.target_model, id=target_id)
        serializer.save(user=user, headquarter=target)

    def create(self, request, *args, **kwargs):
        """Подает заявку на вступление, переданный URL-параметром."""

        if self.position_model.objects.filter(
            user_id=self.request.user.id
        ).exists():
            return Response(
                {'detail': 'Пользователь уже в отряде/штабе на этом уровне.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Отклоняет заявку на вступление."""
        target_id = self.kwargs.get('pk')
        try:
            application = self.application_model.objects.get(
                user=self.request.user,
                headquarter=self.target_model.objects.get(id=target_id)
            )
            application.delete()
        except self.application_model.DoesNotExist:
            return Response(
                {'error': 'Не найдена существующая заявка'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {'success': 'Заявка отклонена'},
            status=status.HTTP_204_NO_CONTENT
        )


class DetachmentApplicationViewSet(BaseApplicationViewSet):
    """Подать/отменить заявку в отряд. URL-параметры обязательны."""

    application_model = UserDetachmentApplication
    serializer_class = UserDetachmentApplicationSerializer
    position_model = UserDetachmentPosition
    permission_classes = (permissions.IsAuthenticated,)
    target_model = Detachment

    def get_queryset(self):
        detachment_id = self.kwargs.get('pk')
        detachment = get_object_or_404(self.target_model, id=detachment_id)
        return self.application_model.objects.filter(detachment=detachment)

    def perform_create(self, serializer):
        user = self.request.user
        target_id = self.kwargs.get('pk')
        target = get_object_or_404(self.target_model, id=target_id)
        serializer.save(user=user, detachment=target)

    def destroy(self, request, *args, **kwargs):
        """Отклоняет заявку на вступление."""
        target_id = self.kwargs.get('pk')
        try:
            application = self.application_model.objects.get(
                user=self.request.user,
                detachment=self.target_model.objects.get(id=target_id)
            )
            application.delete()
        except self.application_model.DoesNotExist:
            return Response(
                {'error': 'Не найдена существующая заявка'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {'success': 'Заявка отклонена'},
            status=status.HTTP_204_NO_CONTENT
        )


class EducationalApplicationViewSet(BaseApplicationViewSet):
    """Подать/отменить заявку в СО ОО. URL-параметры обязательны."""

    application_model = UserEducationalApplication
    serializer_class = UserEducationalApplicationSerializer
    position_model = UserEducationalHeadquarterPosition
    permission_classes = (permissions.IsAuthenticated,)
    target_model = EducationalHeadquarter


class LocalApplicationViewSet(BaseApplicationViewSet):
    """Подать/отменить заявку в МШ. URL-параметры обязательны."""

    application_model = UserLocalApplication
    serializer_class = UserLocalApplicationSerializer
    position_model = UserLocalHeadquarterPosition
    permission_classes = (permissions.IsAuthenticated,)
    target_model = LocalHeadquarter


class RegionalApplicationViewSet(BaseApplicationViewSet):
    """Подать/отменить заявку в РШ. URL-параметры обязательны."""

    application_model = UserRegionalApplication
    serializer_class = UserRegionalApplicationSerializer
    position_model = UserRegionalHeadquarterPosition
    permission_classes = (permissions.IsAuthenticated,)
    target_model = RegionalHeadquarter


class DistrictApplicationViewSet(BaseApplicationViewSet):
    """Подать/отменить заявку в окружной штаб. URL-параметры обязательны."""

    application_model = UserDistrictApplication
    serializer_class = UserDistrictApplicationSerializer
    position_model = UserDistrictHeadquarterPosition
    permission_classes = (permissions.IsAuthenticated,)
    target_model = DistrictHeadquarter


class CentralApplicationViewSet(BaseApplicationViewSet):
    """Подать/отменить заявку в центральной штаб. URL-параметры обязательны."""

    application_model = UserCentralApplication
    serializer_class = UserCentralApplicationSerializer
    position_model = UserCentralHeadquarterPosition
    permission_classes = (permissions.IsAuthenticated,)
    target_model = CentralHeadquarter


@api_view(['GET'])
def get_structural_units(request):
    """
    Представление для агрегации и возврата списка всех
    структурных подразделений.

    Объединяет данные из различных типов штабов и отрядов,
    включая центральные, региональные, окружные, местные и
    образовательные штабы, а также отряды. Каждый тип подразделения
    сериализуется с использованием соответствующего сериализатора и
    возвращается в едином совокупном JSON-ответе.
    """
    central_headquarters = CentralHeadquarter.objects.all()
    regional_headquarters = RegionalHeadquarter.objects.all()
    district_headquarters = DistrictHeadquarter.objects.all()
    local_headquarters = LocalHeadquarter.objects.all()
    educational_headquarters = EducationalHeadquarter.objects.all()
    detachments = Detachment.objects.all()

    response = {
        'central_headquarters': CentralHeadquarterSerializer(
            central_headquarters, many=True
        ).data,
        'regional_headquarters': ShortRegionalHeadquarterSerializer(
            regional_headquarters, many=True
        ).data,
        'district_headquarters': ShortDistrictHeadquarterSerializer(
            district_headquarters, many=True
        ).data,
        'local_headquarters': ShortLocalHeadquarterSerializer(
            local_headquarters, many=True
        ).data,
        'educational_headquarters': ShortEducationalHeadquarterSerializer(
            educational_headquarters, many=True
        ).data,
        'detachments': ShortDetachmentSerializer(detachments, many=True).data
    }

    return Response(response)


class CentralAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = CentralHeadquarter.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class DistrictAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = DistrictHeadquarter.objects.all()
        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class RegionAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Region.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs.order_by('name')


class EducationalAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = EducationalHeadquarter.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class LocalAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = LocalHeadquarter.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class RegionalAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = RegionalHeadquarter.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class EducationalInstitutionAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = EducationalInstitution.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class DetachmentAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Detachment.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class PositionAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Position.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class DetachmentListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Detachment.objects.all()
    serializer_class = DetachmentListSerializer
    filter_backends = (
        filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter
    )
    filterset_class = DetachmentListFilter
    search_fields = ('name',)
    ordering = ('name',)

    @method_decorator(cache_page(settings.DETANCHMENT_LIST_CACHE_TTL))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        regional_headquarter = self.request.query_params.get(
            'regional_headquarter'
        )
        local_headquarter = self.request.query_params.get('local_headquarter')
        educational_headquarter = self.request.query_params.get(
            'educational_headquarter'
        )

        if regional_headquarter:
            queryset = queryset.filter(
                regional_headquarter=regional_headquarter
            )
        if local_headquarter:
            queryset = queryset.filter(local_headquarter=local_headquarter)
        if educational_headquarter:
            queryset = queryset.filter(
                educational_headquarter=educational_headquarter
            )

        return queryset
