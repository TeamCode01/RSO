import os
import re
from datetime import date

from dal import autocomplete
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.http import QueryDict
from django_filters.rest_framework import DjangoFilterBackend
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from api.mixins import (
    CreateListRetrieveUpdateViewSet, ListRetrieveDestroyViewSet,
    ListRetrieveCreateViewSet, UpdateDestroyViewSet
)
from api.permissions import (
    IsCommanderAndCompetitionParticipant,
    IsCommanderDetachmentInParameterOrRegionalCommander,
    IsCommanderDetachmentInParameterOrRegionalCommissioner,
    IsCompetitionParticipantAndCommander,
    IsRegionalCommanderOrAdmin, IsRegionalCommanderOrAdminOrAuthor,
    IsRegionalCommanderOrAuthor,
    IsRegionalCommissioner,
    IsRegionalCommissionerOrCommanderDetachmentWithVerif,
    IsQ13DetachmentReportAuthor, IsQ5DetachmentReportAuthor,
    IsQ15DetachmentReportAuthor, IsCentralEventMaster
)
from api.utils import get_detachment_start, get_detachment_tandem, get_events_data
from competitions.models import (
    Q10, Q11, Q12, Q7, Q8, Q9, CompetitionApplications,
    CompetitionParticipants, Competitions, Q10Report, Q11Report, Q12Report,
    Q13EventOrganization,
    Q13DetachmentReport, Q13Ranking, Q13TandemRanking, Q14Ranking, Q16Report,
    Q17DetachmentReport, Q17Link, Q17Ranking, Q19Report, Q1Ranking,
    Q1TandemRanking, Q20Report, Q2DetachmentReport, Q2Ranking,
    Q2TandemRanking, Q7Report, Q18DetachmentReport,
    Q18TandemRanking, Q18Ranking, Q8Report, Q9Report, Q19Ranking,
    Q19TandemRanking, Q4TandemRanking, Q4Ranking, Q3TandemRanking, Q3Ranking,
    Q5DetachmentReport, Q5TandemRanking, Q5Ranking, Q5EducatedParticipant,
    Q14LaborProject, Q14DetachmentReport, Q6DetachmentReport, Q6Ranking,
    Q15TandemRank, Q15Rank, Q15GrantWinner, Q6TandemRanking,
    Q15DetachmentReport, OverallRanking, OverallTandemRanking,
)
from competitions.q_calculations import (calculate_q13_place,
                                         calculate_q19_place)
from competitions.serializers import (
    CompetitionApplicationsObjectSerializer, CompetitionApplicationsSerializer,
    CompetitionParticipantsObjectSerializer, CompetitionParticipantsSerializer,
    CompetitionSerializer, CreateQ10Serializer, CreateQ11Serializer,
    CreateQ12Serializer, CreateQ7Serializer, CreateQ8Serializer,
    CreateQ9Serializer, Q10ReportSerializer, Q10Serializer,
    Q11ReportSerializer, Q11Serializer, Q12ReportSerializer, Q12Serializer,
    Q16ReportSerializer, Q17DetachmentReportSerializer,
    Q19DetachmenrtReportSerializer, Q20ReportSerializer,
    Q2DetachmentReportSerializer, Q7ReportSerializer, Q7Serializer,
    Q8ReportSerializer, Q8Serializer, Q9ReportSerializer, Q9Serializer,
    ShortDetachmentCompetitionSerializer, Q13EventOrganizationSerializer,
    Q18DetachmentReportSerializer, Q15GrantWinnerSerializer,
    Q5EducatedParticipantSerializer,
    Q14DetachmentReportSerializer, Q6DetachmentReportSerializer, Q5DetachmentReportReadSerializer,
    Q5DetachmentReportWriteSerializer, Q15DetachmentReportReadSerializer, Q15DetachmentReportWriteSerializer,
    Q13DetachmentReportWriteSerializer, Q13DetachmentReportReadSerializer,
)
from competitions.utils import get_place_q2, tandem_or_start
# сигналы ниже не удалять, иначе сломается
from competitions.signal_handlers import (
    create_score_q7, create_score_q8, create_score_q9, create_score_q10,
    create_score_q11, create_score_q12, create_score_q20
)
from api.mixins import ListRetrieveDestroyViewSet
from api.permissions import (IsRegionalCommanderOrAdmin,
                             IsRegionalCommanderOrAdminOrAuthor)
from competitions.filters import CompetitionParticipantsFilter
from competitions.models import (CompetitionApplications,
                                 CompetitionParticipants, Competitions)
from competitions.serializers import (CompetitionApplicationsObjectSerializer,
                                      CompetitionApplicationsSerializer,
                                      CompetitionParticipantsObjectSerializer,
                                      CompetitionParticipantsSerializer,
                                      CompetitionSerializer,
                                      ShortDetachmentCompetitionSerializer)
from competitions.swagger_schemas import (request_update_application,
                                          response_competitions_applications,
                                          response_competitions_participants,
                                          response_create_application,
                                          response_junior_detachments,
                                          q7schema_request, q9schema_request)
from headquarters.models import Detachment, RegionalHeadquarter, UserDetachmentPosition
from users.models import RSOUser
from headquarters.serializers import ShortDetachmentSerializer
from headquarters.models import (
    Detachment, RegionalHeadquarter, UserDetachmentPosition
)
from rso_backend.settings import BASE_DIR


class CompetitionViewSet(viewsets.ModelViewSet):
    """Представление конкурсов.

    Доступ:
        - чтение: все пользователи
        - запись/удаление/редактирование: только администраторы
    """
    queryset = Competitions.objects.all()
    serializer_class = CompetitionSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_detachment(self):
        """
        Возвращает отряд, созданный после 25 января 2024 года
        """
        return Detachment.objects.filter(
            Q(founding_date__lt=date(*settings.DATE_JUNIOR_SQUAD))
            & Q(commander=self.request.user)
        ).first()

    def get_free_junior_detachments_ids(self):
        """
        Возвращает список ID младших отрядов, которые
        не подали заявки или не участвуют в текущем конкурсе.
        """
        competition_id = self.get_object().id
        in_applications_junior_detachment_ids = list(
            CompetitionApplications.objects.filter(
                competition__id=competition_id
            ).values_list(
                'junior_detachment__id', flat=True
            )
        )
        participants_junior_detachment_ids = list(
            CompetitionParticipants.objects.filter(
                competition__id=competition_id
            ).values_list(
                'junior_detachment__id', flat=True
            )
        )
        return list(Detachment.objects.exclude(
            id__in=in_applications_junior_detachment_ids
                   + participants_junior_detachment_ids
        ).values_list('id', flat=True))

    def get_junior_detachments(self):
        """
        Возвращает экземпляры свободных младших отрядов.
        """
        user_detachment = self.get_detachment()
        if not user_detachment:
            return None
        free_junior_detachments_ids = (
            self.get_free_junior_detachments_ids()
        )
        detachments = Detachment.objects.filter(
            Q(founding_date__gte=date(*settings.DATE_JUNIOR_SQUAD)) &
            Q(region=user_detachment.region) &
            Q(id__in=free_junior_detachments_ids)
        )
        return detachments

    @action(detail=True,
            methods=['get'],
            url_path='junour_detachments',
            permission_classes=(permissions.IsAuthenticated,))
    @swagger_auto_schema(responses=response_junior_detachments)
    def junior_detachments(self, request, pk):
        """Action для получения списка младших отрядов.

        Выводит свободные младшие отряды этого региона доступные к
        подаче в тандем заявку.

        Доступ - только авторизированные пользователи.
        Если юзер не командир старшего отряда - возвращает пустой массив.
        """
        junior_detachments = self.get_junior_detachments()
        serializer = ShortDetachmentCompetitionSerializer(
            junior_detachments, many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True,
            methods=['get'],
            url_path='check_detachment_status',
            permission_classes=(permissions.IsAuthenticated,))
    def status(self, request, pk):
        """Action для получения статуса отряда пользователя в конкурсе.

        Доступ:
            - только командиры отрядов.

        Если отряд участвует в конкурсе - возвращает "Вы участник".
        Если отряд не участвует в конкурсе - возвращает "Еще не участвуете".
        Если отряд подал заявку на конкурс - возвращает
            "Заявка на рассмотрении".
        """
        detachment = Detachment.objects.filter(
            commander=request.user
        ).first()
        if not detachment:
            return Response(
                {'error': 'Пользователь не командир отряда'},
                status=status.HTTP_403_FORBIDDEN
            )
        if CompetitionApplications.objects.filter(
                Q(junior_detachment=detachment) |
                Q(detachment=detachment)
        ).exists():
            return Response(
                {'status': 'Заявка на рассмотрении'},
                status=status.HTTP_200_OK
            )
        if CompetitionParticipants.objects.filter(
                Q(junior_detachment=detachment) |
                Q(detachment=detachment)
        ).exists():
            return Response(
                {'status': 'Вы участник'},
                status=status.HTTP_200_OK
            )
        return Response(
            {'status': 'Еще не участвуете'},
            status=status.HTTP_200_OK
        )

    @staticmethod
    def download_file_competitions(filepath, filename):
        if os.path.exists(filepath):
            with open(filepath, 'rb') as file:
                response = HttpResponse(
                    file.read(), content_type='application/pdf'
                )
                response['Content-Disposition'] = (
                    f'attachment; filename="{filename}"'
                )
                return response
        else:
            return Response(
                {'detail': 'Файл не найден.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=False,
        methods=('get',),
        url_path='download_regulation_file',
        permission_classes=(permissions.AllowAny,)
    )
    def download_regulation_file(self, request):
        """Скачивание положения конкурса РСО.

        Доступ - все пользователи.
        """
        filename = 'Regulation_on_the_best_LSO_2024.pdf'
        filepath = str(settings.BASE_DIR) + '/templates/competitions/' + filename
        return self.download_file_competitions(filepath, filename)


class CompetitionApplicationsViewSet(viewsets.ModelViewSet):
    """Представление заявок на конкурс.

    Доступ:
        - чтение(list) - региональный командир или админ.
          В первом случае выводятся заявки этого региона,
          во втором - все заявки.
        - чтение(retrieve) - региональный командир, админ или
          один из отрядов этой заявки.
        - удаление - региональный командир, админ или один из
          отрядов этой заявки.
        - обновление - только командир младшего отряда,
          изменить можно только поле is_confirmed_by_junior
          (функционал подтверждения заявки младшим отрядом).
    """
    queryset = CompetitionApplications.objects.all()
    serializer_class = CompetitionApplicationsSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if self.action == 'list':
            regional_headquarter = RegionalHeadquarter.objects.filter(
                commander=self.request.user
            )
            if regional_headquarter:
                user_region = regional_headquarter.first().region
                return CompetitionApplications.objects.filter(
                    Q(junior_detachment__region=user_region) &
                    Q(competition_id=self.kwargs.get('competition_pk'))
                )
            return CompetitionApplications.objects.filter(
                competition_id=self.kwargs.get('competition_pk')
            )
        return CompetitionApplications.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'list':
            return CompetitionApplicationsObjectSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'destroy' or self.action == 'retrieve':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdminOrAuthor()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        return super().get_permissions()

    def get_detachment(self, user):
        """Возвращает отряд, в котором юзер командир.

        Если юзер не командир, то возвращает None
        """
        try:
            detachment = Detachment.objects.get(commander=user)
            return detachment
        # except Detachment.DoesNotExist:
        #     return None
        except Exception:
            return None

    def get_junior_detachment(self, request_data):
        if 'junior_detachment' in request_data:
            return get_object_or_404(Detachment,
                                     id=request_data['junior_detachment'])

    @swagger_auto_schema(
        request_body=response_create_application
    )
    def create(self, request, *args, **kwargs):
        """Создание заявки в конкурс

        Если передается junior_detachment: id, то создается заявка-тандем,
        если нет - индивидуальная заявка.

        Доступ - только командир отряда.
        """
        current_detachment = self.get_detachment(request.user)
        if current_detachment is None:
            return Response({'error': 'Пользователь не является командиром'},
                            status=status.HTTP_400_BAD_REQUEST)

        MIN_DATE = (f'{settings.DATE_JUNIOR_SQUAD[2]}'
                    f'.{settings.DATE_JUNIOR_SQUAD[1]}.'
                    f'{settings.DATE_JUNIOR_SQUAD[0]} года')
        if current_detachment.founding_date < date(
                *settings.DATE_JUNIOR_SQUAD
        ):
            detachment = current_detachment
            junior_detachment = self.get_junior_detachment(request.data)
        else:
            if 'junior_detachment' in request.data:
                return Response(
                    {'error': f'- дата основания отряда позднее {MIN_DATE}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            junior_detachment = current_detachment
            detachment = None
        competition = get_object_or_404(Competitions,
                                        pk=self.kwargs.get('competition_pk'))

        serializer = self.get_serializer(
            data=request.data,
            context={'detachment': detachment,
                     'junior_detachment': junior_detachment,
                     'competition': competition,
                     'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save(competition=competition,
                            detachment=detachment,
                            junior_detachment=junior_detachment,
                            is_confirmed_by_junior=False)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def is_commander_of_junior_detachment(self, user, instance):
        junior_detachment = instance.junior_detachment
        if not junior_detachment:
            return False
        return user == junior_detachment.commander

    def handle_junior_detachment_update(self, request, instance):
        if self.is_commander_of_junior_detachment(request.user, instance):
            data = {
                'is_confirmed_by_junior':
                    request.data.get('is_confirmed_by_junior')
            }
            serializer = self.get_serializer(instance,
                                             data=data,
                                             partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        else:
            return Response({'error': 'Доступ запрещен'},
                            status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        request_body=request_update_application
    )
    def update(self, request, *args, **kwargs):
        """Изменение заявки на мероприятие

        Изменить можно только поле is_confirmed_by_junior.
        Доступ - только командир младшего отряда.
        """
        instance = self.get_object()
        return self.handle_junior_detachment_update(request, instance)

    @swagger_auto_schema(
        request_body=request_update_application
    )
    def partial_update(self, request, *args, **kwargs):
        """Изменение заявки на мероприятие

        Изменить можно только поле is_confirmed_by_junior.
        Доступ - только командир младшего отряда.
        """
        instance = self.get_object()
        return self.handle_junior_detachment_update(request, instance)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=[permissions.IsAuthenticated])
    @swagger_auto_schema(responses=response_competitions_applications)
    def me(self, request, *args, **kwargs):
        """Получение заявки на мероприятие отряда текущего пользователя.

        Доступ - все авторизованные пользователи.
        Если пользователь не является командиром отряда, либо
        у его отряда нет заявки на участие - запрос вернет ошибку 404.
        """
        detachment = self.get_detachment(request.user)
        if detachment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        application = self.get_queryset().filter(
            Q(detachment=detachment) | Q(junior_detachment=detachment)
        ).first()
        if application is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CompetitionApplicationsObjectSerializer(
            application,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True,
            methods=['post'],
            url_path='confirm',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommanderOrAdmin,))
    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
    ))
    def confirm(self, request, *args, **kwargs):
        """Подтверждение заявки на участие в мероприятии и создание участника.

        После подтверждения заявка удаляется.
        Доступ: администраторы и командиры региональных штабов.
        """
        instance = self.get_object()
        serializer = CompetitionParticipantsSerializer(
            data=request.data,
            context={'request': request,
                     'application': instance}
        )
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save(detachment=instance.detachment,
                                junior_detachment=instance.junior_detachment,
                                competition=instance.competition)
                instance.delete()
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=False,
            methods=['get'],
            url_path='all',
            permission_classes=(permissions.AllowAny,))
    def all(self, request, *args, **kwargs):
        """Получение всех не верифицированных заявок на участие в конкурсе.

        Доступ: любой пользователь.
        """
        queryset = self.get_queryset()
        serializer = CompetitionApplicationsObjectSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompetitionParticipantsViewSet(ListRetrieveDestroyViewSet):
    """ Вью сет для участников мероприятия.

    Доступ:
        - чтение: все
        - удаление: только админы и командиры региональных штабов.
    Поиск:
        - ключ для поиска: ?search
        - поле для поиска: name младшего отряда и отряда-наставника.
    Фильтрация:
        - is_tandem: фильтр по типу участия (старт или тандем),
          принимает значения True и False (или true и false в нижнем регистре).
    Сортировка:
        - доступные поля для сортировки: junior_detachment__name,
                                         detachment__name,
                                         created_at.
        - порядок сортировки по дефолту: junior_detachment__name,
                                         detachment__name,
                                         created_at.
    """
    queryset = CompetitionParticipants.objects.all()
    serializer_class = CompetitionParticipantsSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = (DjangoFilterBackend,
                       filters.SearchFilter,
                       filters.OrderingFilter)
    filterset_class = CompetitionParticipantsFilter
    search_fields = (
        'detachment__name',
        'junior_detachment__name'
    )
    ordering_fields = ('detachment__name',
                       'junior_detachment__name',
                       'created_at')
    ordering = ('junior_detachment__name',
                'detachment__name',
                'created_at')

    def get_queryset(self):
        return CompetitionParticipants.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'list':
            return CompetitionParticipantsObjectSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        return super().get_permissions()

    def get_detachment(self, user):
        """Возвращает отряд, в котором юзер командир.

        Если юзер не командир, то возвращает None
        """
        try:
            detachment = Detachment.objects.get(commander=user)
            return detachment
        except Detachment.DoesNotExist:
            return None
        except Detachment.MultipleObjectsReturned:
            return Response({'error':
                                 'Пользователь командир нескольких отрядов'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    @swagger_auto_schema(responses=response_competitions_participants)
    def me(self, request, *args, **kwargs):
        """Action для получения всей информации по верифицированной заявке.

        Доступен всем авторизованным пользователям.

        Если текущий пользователь не является командиром,
        или его отряд не участвует в мероприятии -
        выводится HTTP_404_NOT_FOUND.
        """
        detachment = self.get_detachment(request.user)
        if detachment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        participant_unit = self.get_queryset().filter(
            Q(detachment=detachment) | Q(junior_detachment=detachment)
        ).first()
        if participant_unit is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CompetitionParticipantsObjectSerializer(participant_unit)
        return Response(serializer.data)

    @action(detail=False,
            methods=['get'],
            url_path='status',
            permission_classes=(permissions.IsAuthenticated,))
    @swagger_auto_schema(responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'is_commander_detachment': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    title='Является ли командиром отряда-участника конкурса',
                    read_only=True
                ),
                'is_commissar_detachment': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    title='Является ли комиссаром отряда-участника конкурса',
                    read_only=True
                )
            }
        )
    })
    def status(self, request, competition_pk, *args, **kwargs):
        """Action для получения статуса пользователя в конкурсе.

        Доступ: все пользователи.
        """
        if self.get_queryset().filter(
                Q(detachment__commander=request.user) |
                Q(junior_detachment__commander=request.user)
        ).exists():
            return Response({
                'is_commander_detachment': True,
                'is_commissar_detachment': False
            })
        try:
            position = request.user.userdetachmentposition.position
        except UserDetachmentPosition.DoesNotExist:
            return Response({
                'is_commander_detachment': False,
                'is_commissar_detachment': False
            })
        if position.name == 'Комиссар':
            return Response({
                'is_commander_detachment': False,
                'is_commissar_detachment': True
            })
        return Response({
            'is_commander_detachment': False,
            'is_commissar_detachment': False
        })


class CompetitionDetachmentAutoComplete(
    autocomplete.Select2QuerySetView
):
    def get_queryset(self):
        qs = Detachment.objects.filter(
            founding_date__lt=date(*settings.DATE_JUNIOR_SQUAD)
        )

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')


class CompetitionJuniorDetachmentAutoComplete(
    autocomplete.Select2QuerySetView
):
    def get_queryset(self):
        qs = Detachment.objects.filter(
            founding_date__gte=date(*settings.DATE_JUNIOR_SQUAD)
        )

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('name')

    @action(detail=False,
            methods=['get'],
            url_path='status',
            permission_classes=(permissions.IsAuthenticated,))
    @swagger_auto_schema(responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'is_commander_detachment': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    title='Является ли командиром отряда-участника конкурса',
                    read_only=True
                ),
                'is_commissar_detachment': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    title='Является ли комиссаром отряда-участника конкурса',
                    read_only=True
                )
            }
        )
    })
    def status(self, request, competition_pk, *args, **kwargs):
        """Action для получения статуса пользователя в конкурсе.

        Доступ: все пользователи.
        """
        if self.get_queryset().filter(
                Q(detachment__commander=request.user) |
                Q(junior_detachment__commander=request.user)
        ).exists():
            return Response({
                'is_commander_detachment': True,
                'is_commissar_detachment': False
            })
        try:
            position = request.user.userdetachmentposition.position
        except UserDetachmentPosition.DoesNotExist:
            return Response({
                'is_commander_detachment': False,
                'is_commissar_detachment': False
            })
        if position.name == 'Комиссар':
            return Response({
                'is_commander_detachment': False,
                'is_commissar_detachment': True
            })
        return Response({
            'is_commander_detachment': False,
            'is_commissar_detachment': False
        })


class Q2DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """
    Прохождение Командиром и Комиссаром студенческого отряда региональной
    школы командного состава.

    Пример POST-запроса:
    {
      "commander_achievement": true,
      "commissioner_achievement": true,
      "commander_link": "https://some-link.com",
      "commissioner_link": "https://some-link.com"
    }

    Поля “Региональная школа командного состава пройдена командиром отряда”
    и “Региональная школа командного состава пройдена комиссаром отряда”
    обязательные.
    При выборе “Да” обязательным также становится поле
    “Ссылка на публикацию о прохождении школы командного состава”,
    так как прохождение обучения засчитывается только
    при предоставлении ссылки на документ.

    Командир выбрал “Да” + Комиссар выбрал “Да” - 1 место
    Командир выбрал “Да” + Комиссар выбрал “Нет” - 2 место
    Командир выбрал “Нет” + Комиссар выбрал “Да” - 2 место
    Командир выбрал “Нет” + Комиссар выбрал “Нет” - 3 место
    """

    PLACE_FIRST = 1
    PLACE_SECOND = 2

    serializer_class = Q2DetachmentReportSerializer
    permission_classes = (permissions.IsAuthenticated,
                          IsCompetitionParticipantAndCommander)

    def get_queryset(self):
        return Q2DetachmentReport.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated(),
                    IsCommanderDetachmentInParameterOrRegionalCommander()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAuthor()]
        return super().get_permissions()

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    def create(self, request, *args, **kwargs):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        try:
            detachment = get_object_or_404(
                Detachment, id=request.user.detachment_commander.id
            )
        except Detachment.DoesNotExist:
            return Response(
                {'error': 'Заполнять данные может только командир отряда.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not CompetitionParticipants.objects.filter(
                competition=competition, detachment=detachment
        ).exists():
            if not CompetitionParticipants.objects.filter(
                    competition=competition, junior_detachment=detachment
            ).exists():
                return Response(
                    {
                        'error': 'Ваш отряд не зарегистрирован'
                                 ' как участник конкурса.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        if Q2DetachmentReport.objects.filter(
                competition=competition,
                detachment=detachment
        ).exists():
            return Response(
                {'error': 'Отчет уже был подан ранее.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        commander_achievement = request.data.get(
            'commander_achievement'
        )
        commissioner_achievement = request.data.get(
            'commissioner_achievement'
        )
        commander_link = request.data.get('commander_link')
        commissioner_link = request.data.get('commissioner_link')
        q2_data = {
            'commander_achievement': commander_achievement,
            'commissioner_achievement': commissioner_achievement,
            'commander_link': commander_link,
            'commissioner_link': commissioner_link
        }
        if (commander_achievement and not commander_link) or (
                commissioner_achievement and not commissioner_link
        ):
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'error': 'Не указана подтверждающая ссылка.'}
            )
        serializer = Q2DetachmentReportSerializer(
            data=q2_data,
            context={
                'request': request,
                'competition': competition,
                'detachment': detachment,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(
            competition=competition,
            detachment=detachment,
            is_verified=False
        )
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения списка отчетов отряда текущего пользователя.

        Доступ: все авторизованные пользователи.
        Если пользователь не командир отряда, и у его отряда нет
        поданных отчетов - вернется пустой список.
        """
        return super().list(request, *args, **kwargs)

    @action(
        detail=False,
        methods=['get'],
        url_path='get-place',
        serializer_class=None
    )
    def get_place(self, request, competition_pk, **kwargs):
        """Определение места по показателю.

        Возвращается место или статус показателя.
        Если показатель не был подан ранее, то возвращается код 400.
        """

        detachment = self.request.user.detachment_commander
        report = Q2DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=self.kwargs.get('competition_pk')
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        is_verified = report.is_verified
        is_tandem = tandem_or_start(
            competition=report.competition,
            detachment=report.detachment,
            competition_model=CompetitionParticipants
        )

        if not is_verified:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': 'Показатель в обработке.'}
            )
        tandem_ranking = getattr(
            detachment, 'q2tandemranking_main_detachment'
        ).filter(competition_id=competition_pk).first()
        if not tandem_ranking:
            tandem_ranking = getattr(
                detachment, 'q2tandemranking_junior_detachment'
            ).filter(competition_id=competition_pk).first()

        if is_tandem:
            if tandem_ranking and tandem_ranking.place is not None:
                return Response(
                    {'place': tandem_ranking.place},
                    status=status.HTTP_200_OK
                )
        else:
            ranking = Q2Ranking.objects.filter(
                detachment=report.detachment
            ).first()
            if ranking and ranking.place is not None:
                return Response(
                    {'place': ranking.place}, status=status.HTTP_200_OK
                )

        return Response(
            status=status.HTTP_404_NOT_FOUND,
            data={'detail': 'Показатель в обработке.'}
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        serializer_class=None,
        permission_classes=(permissions.IsAuthenticated,
                            IsRegionalCommanderOrAdmin),
    )
    def verify(self, *args, **kwargs):
        """Верификация отчета по показателю.

        Доступно только командиру РШ связанного с отрядом.
        Если отчет уже верифицирован, возвращается 400 Bad Request с описанием
        ошибки `{"detail": "Данный отчет уже верифицирован"}`.
        При удалении отчета удаляются записи из таблиц Rankin и TandemRankin.
        """

        detachment_report = self.get_object()
        competition = detachment_report.competition
        detachment = detachment_report.detachment

        if self.request.method == 'DELETE':
            if detachment_report.is_verified:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={'detail': 'Верифицированный отчет нельзя удалить.'}
                )
            detachment_report.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        with transaction.atomic():
            if detachment_report.is_verified:
                return Response({
                    'detail': 'Данный отчет уже верифицирован'
                }, status=status.HTTP_400_BAD_REQUEST)

            detachment_report.is_verified = True
            detachment_report.save()

            """Расчет мест по показателю и запись в таблицы Ranking."""

            is_tandem = tandem_or_start(
                competition=competition,
                detachment=detachment,
                competition_model=CompetitionParticipants
            )
            place_1 = get_place_q2(
                commander_achievment=(
                    detachment_report.commander_achievement
                ),
                commissioner_achievement=(
                    detachment_report.commissioner_achievement
                )
            )
            if is_tandem:
                try:
                    partner_detachment = CompetitionParticipants.objects.get(
                        competition=competition,
                        detachment=detachment
                    ).junior_detachment
                    partner_is_junior = True
                except CompetitionParticipants.DoesNotExist:
                    partner_detachment = (
                        CompetitionParticipants.objects.filter(
                            competition=competition,
                            junior_detachment=detachment
                        ).first().detachment
                    )
                    partner_is_junior = False
                try:
                    partner_detahcment_report = (
                        Q2DetachmentReport.objects.filter(
                            competition=competition,
                            detachment=partner_detachment
                        ).first()
                    )
                except Q2DetachmentReport.DoesNotExist:
                    return Response(
                        status=status.HTTP_404_NOT_FOUND,
                        data={
                            'detail': 'Отряд-напарник не подал отчет'
                                      ' по показателю.'
                        }
                    )
                place_2 = get_place_q2(
                    commander_achievment=(
                        partner_detahcment_report.commander_achievement
                    ),
                    commissioner_achievement=(
                        partner_detahcment_report.commissioner_achievement
                    )
                )
                result_place = round((place_1 + place_2) / 2, 2)
                if partner_is_junior:
                    tandem_ranking, _ = Q2TandemRanking.objects.get_or_create(
                        competition=competition,
                        detachment=detachment,
                        junior_detachment=partner_detachment,
                    )
                else:
                    tandem_ranking, _ = Q2TandemRanking.objects.get_or_create(
                        competition=competition,
                        detachment=partner_detachment,
                        junior_detachment=detachment,
                    )
                tandem_ranking.place = result_place
                tandem_ranking.save()
                return Response(
                    status=status.HTTP_201_CREATED,
                    data={
                        'detail': 'Отчет верифицирован, '
                                  f'место - {result_place}.'
                    }
                )
            else:
                ranking, _ = Q2Ranking.objects.get_or_create(
                    competition=competition,
                    detachment=detachment,
                )
                ranking.place = place_1
                ranking.save()
                return Response(
                    status=status.HTTP_201_CREATED,
                    data={
                        'detail': 'Отчет верифицирован, место - '
                                  f'{place_1}.'
                    }
                )


class Q7ViewSet(
    viewsets.ModelViewSet
):
    """Вью сет для показателя 'Участие членов студенческого отряда в
    окружных и межрегиональных мероприятиях.'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
        - удаление: Если заявка не подтверждена - командир отряда из
                    инстанса объекта который удаляют,
                    а также комиссары региональных штабов.
                    Если подтверждена - только комиссар регионального штаба.
    ! При редактировании нельзя изменять event_name.
    """
    serializer_class = Q7Serializer
    permission_classes = (
        permissions.IsAuthenticated,
        IsCommanderDetachmentInParameterOrRegionalCommissioner
    )

    def get_queryset(self):
        if self.action == 'list':
            regional_headquarter = (
                self.request.user.userregionalheadquarterposition.headquarter
            )
            return self.serializer_class.Meta.model.objects.filter(
                detachment_report__detachment__regional_headquarter=regional_headquarter,
                detachment_report__competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'me':
            return self.serializer_class.Meta.model.objects.filter(
                detachment_report__detachment__commander=self.request.user,
                detachment_report__competition_id=self.kwargs.get('competition_pk')
            )
        return self.serializer_class.Meta.model.objects.filter(
            detachment_report__competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(),
                    IsCommanderAndCompetitionParticipant()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(), IsRegionalCommissioner()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(),
                    IsRegionalCommissionerOrCommanderDetachmentWithVerif()]
        return super().get_permissions()

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment_report.detachment

    @swagger_auto_schema(
        # request_body=ListSerializer(child=CreateQ7Serializer()), # работает.
        request_body=q7schema_request,
        responses={201: Q7ReportSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Action для создания отчета.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        'event_name' к передаче обязателен.
        """
        competition = self.get_competitions()
        detachment = get_object_or_404(
            Detachment, id=request.user.detachment_commander.id
        )
        detachment_report, _ = Q7Report.objects.get_or_create(
            detachment=detachment,
            competition=competition
        )
        events_data = get_events_data(request)
        if not events_data:
            return Response(
                {
                    'non_field_errors': f'Присланный реквест: {request.data}'
                                        f'файлы: {request.FILES}',
                    'events_data': events_data
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        for event in events_data:
            serializer = CreateQ7Serializer(
                data=event,
                context={'request': request,
                         'competition': competition,
                         'event': event,
                         'detachment_report': detachment_report},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(detachment_report=detachment_report,
                            is_verified=False)
        return Response(Q7ReportSerializer(detachment_report).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q7Serializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        event = self.get_object()
        if event.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            event.is_verified = True
            event.save()
            return Response(Q7Serializer(event).data,
                            status=status.HTTP_200_OK)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения списка всех отчетов об участии
        в региональных и межрегиональных мероприятиях текущего пользователя.

        Доступ: все авторизованные пользователи.
        Если пользователь не командир отряда, и у его отряда нет
        поданных отчетов - вернется пустой список.
        """
        return super().list(request, *args, **kwargs)

    @action(detail=False,
            methods=['get'],
            url_path='get-place',
            permission_classes=(permissions.IsAuthenticated,
                                IsCommanderAndCompetitionParticipant))
    def get_place(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения рейтинга по данному показателю.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        Если отчета еще не подан, вернется ошибка 404. (данные не отправлены)
        Если отчет подан, но еще не верифицировн - вернется
        {"place": "Показатель в обработке"}.
        Если отчет подан и верифицирован - вернется место в рейтинге:
        {"place": int}
        """
        detachment = request.user.detachment_commander
        report = self.serializer_class.Meta.model.objects.filter(
            detachment_report__detachment=detachment,
            detachment_report__competition_id=competition_pk
        ).first()
        if not report:
            # Отряд участник, но еще не подал отчет по данному показателю.
            return Response(status=status.HTTP_404_NOT_FOUND)
        class_name = self.serializer_class.Meta.model.__name__  # Q7
        ranking_fk = f'{class_name.lower()}ranking'  # q7ranking
        # Если есть FK на стартовый рейтинг
        ranking = getattr(detachment, ranking_fk).filter(
            competition_id=competition_pk
        ).first()
        if ranking:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )
        #  Если нет, то ищем в тандем рейтингах
        tandem_ranking_fk = (
            f'{class_name.lower()}tandemranking_main_detachment'
        )
        # Если есть FK на наставника
        tandem_ranking = getattr(detachment, tandem_ranking_fk).filter(
            competition_id=competition_pk
        ).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        tandem_ranking_fk = (
            f'{class_name.lower()}tandemranking_junior_detachment'
        )
        # Если есть FK на junior
        tandem_ranking = getattr(
            detachment, tandem_ranking_fk
        ).filter(competition_id=competition_pk).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        # Отчет уже есть(проверяли в начале), значит еще не верифицировано ни одно мероприятие
        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_200_OK
        )


class Q8ViewSet(Q7ViewSet):
    """Вью сет для показателя 'Участие членов студенческого отряда во
    всероссийских мероприятиях.'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
        - удаление: Если заявка не подтверждена - командир отряда из
                    инстанса объекта который удаляют,
                    а также комиссары региональных штабов.
                    Если подтверждена - только комиссар регионального штаба.
    ! При редактировании нельзя изменять event_name.
    """
    queryset = Q8.objects.all()
    serializer_class = Q8Serializer

    @swagger_auto_schema(
        request_body=q7schema_request,
        responses={201: Q8ReportSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Action для создания отчета.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        'event_name' к передаче обязателен.
        """
        competition = self.get_competitions()
        detachment = get_object_or_404(
            Detachment, id=request.user.detachment_commander.id
        )
        detachment_report, _ = Q8Report.objects.get_or_create(
            detachment=detachment,
            competition=competition
        )
        events_data = get_events_data(request)
        for event in events_data:
            serializer = CreateQ8Serializer(
                data=event,
                context={'request': request,
                         'competition': competition,
                         'event': event,
                         'detachment_report': detachment_report},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(detachment_report=detachment_report,
                            is_verified=False)
        return Response(Q8ReportSerializer(detachment_report).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q8Serializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        event = self.get_object()
        if event.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            event.is_verified = True
            event.save()
            return Response(Q8Serializer(event).data,
                            status=status.HTTP_200_OK)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q9ViewSet(
    Q7ViewSet
):
    """Вью сет для показателя 'Призовые места отряда в
    окружных и межрегиональных мероприятиях и конкурсах РСО.'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
        - удаление: Если заявка не подтверждена - командир отряда из
                    инстанса объекта который удаляют,
                    а также комиссары региональных штабов.
                    Если подтверждена - только комиссар регионального штаба.
    ! При редактировании нельзя изменять event_name.
    """
    queryset = Q9.objects.all()
    serializer_class = Q9Serializer

    @swagger_auto_schema(
        request_body=q9schema_request,
        responses={201: Q9ReportSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Action для создания отчета.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        'event_name' к передаче обязателен.
        """
        competition = self.get_competitions()
        detachment = get_object_or_404(
            Detachment, id=request.user.detachment_commander.id
        )
        detachment_report, _ = Q9Report.objects.get_or_create(
            detachment=detachment,
            competition=competition
        )
        events_data = get_events_data(request)
        if not events_data:
            return Response({'error': 'Отчет пустой.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not events_data:
            return Response({'error': 'Отчет пустой.'},
                            status=status.HTTP_400_BAD_REQUEST)
        for event in events_data:
            serializer = CreateQ9Serializer(
                data=event,
                context={'request': request,
                         'competition': competition,
                         'event': event,
                         'detachment_report': detachment_report},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(detachment_report=detachment_report,
                            is_verified=False)
        return Response(Q9ReportSerializer(detachment_report).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q9Serializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        event = self.get_object()
        if event.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            event.is_verified = True
            event.save()
            return Response(Q9Serializer(event).data,
                            status=status.HTTP_200_OK)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q10ViewSet(
    Q7ViewSet
):
    """Вью сет для показателя 'Призовые места отряда во
    всероссийских мероприятиях и конкурсах РСО.'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
        - удаление: Если заявка не подтверждена - командир отряда из
                    инстанса объекта который удаляют,
                    а также комиссары региональных штабов.
                    Если подтверждена - только комиссар регионального штаба.
    ! При редактировании нельзя изменять event_name.
    """
    queryset = Q10.objects.all()
    serializer_class = Q10Serializer

    @swagger_auto_schema(
        request_body=q9schema_request,
        responses={201: Q10ReportSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Action для создания отчета.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        'event_name' к передаче обязателен.
        """
        competition = self.get_competitions()
        detachment = get_object_or_404(
            Detachment, id=request.user.detachment_commander.id
        )
        detachment_report, _ = Q10Report.objects.get_or_create(
            detachment=detachment,
            competition=competition
        )
        events_data = get_events_data(request)
        if not events_data:
            return Response({'error': 'Отчет пустой.'},
                            status=status.HTTP_400_BAD_REQUEST)
        for event in events_data:
            serializer = CreateQ10Serializer(
                data=event,
                context={'request': request,
                         'competition': competition,
                         'event': event,
                         'detachment_report': detachment_report},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(detachment_report=detachment_report,
                            is_verified=False)
        return Response(Q10ReportSerializer(detachment_report).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q10Serializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        event = self.get_object()
        if event.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            event.is_verified = True
            event.save()
            return Response(Q10Serializer(event).data,
                            status=status.HTTP_200_OK)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q11ViewSet(
    Q7ViewSet
):
    """Вью сет для показателя 'Призовые места отряда в
    окружных и межрегиональных трудовых проектах'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
        - удаление: Если заявка не подтверждена - командир отряда из
                    инстанса объекта который удаляют,
                    а также комиссары региональных штабов.
                    Если подтверждена - только комиссар регионального штаба.
    ! При редактировании нельзя изменять event_name.
    """
    queryset = Q11.objects.all()
    serializer_class = Q11Serializer

    @swagger_auto_schema(
        request_body=q9schema_request,
        responses={201: Q11ReportSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Action для создания отчета.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        'event_name' к передаче обязателен.
        """
        competition = self.get_competitions()
        detachment = get_object_or_404(
            Detachment, id=request.user.detachment_commander.id
        )
        detachment_report, _ = Q11Report.objects.get_or_create(
            detachment=detachment,
            competition=competition
        )
        if not request.data:
            return Response({'error': 'Отчет пустой.'},
                            status=status.HTTP_400_BAD_REQUEST)
        events_data = get_events_data(request)
        if not events_data:
            return Response({'error': 'Отчет пустой.'},
                            status=status.HTTP_400_BAD_REQUEST)
        for event in events_data:
            serializer = CreateQ11Serializer(
                data=event,
                context={'request': request,
                         'competition': competition,
                         'event': event,
                         'detachment_report': detachment_report},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(detachment_report=detachment_report,
                            is_verified=False)
        return Response(Q11ReportSerializer(detachment_report).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q11Serializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        event = self.get_object()
        if event.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            event.is_verified = True
            event.save()
            return Response(Q11Serializer(event).data,
                            status=status.HTTP_200_OK)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q12ViewSet(
    Q7ViewSet
):
    """Вью сет для показателя 'Призовые места отряда во
    всероссийских трудовых проектах'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
        - удаление: Если заявка не подтверждена - командир отряда из
                    инстанса объекта который удаляют,
                    а также комиссары региональных штабов.
                    Если подтверждена - только комиссар регионального штаба.
    ! При редактировании нельзя изменять event_name.
    """
    queryset = Q12.objects.all()
    serializer_class = Q12Serializer

    @swagger_auto_schema(
        request_body=q9schema_request,
        responses={201: Q12ReportSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Action для создания отчета.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        'event_name' к передаче обязателен.
        """
        competition = self.get_competitions()
        detachment = get_object_or_404(
            Detachment, id=request.user.detachment_commander.id
        )
        detachment_report, _ = Q12Report.objects.get_or_create(
            detachment=detachment,
            competition=competition
        )
        if not request.data:
            return Response({'error': 'Отчет пустой.'},
                            status=status.HTTP_400_BAD_REQUEST)
        events_data = get_events_data(request)
        if not events_data:
            return Response({'error': 'Отчет пустой.'},
                            status=status.HTTP_400_BAD_REQUEST)
        for event in events_data:
            serializer = CreateQ12Serializer(
                data=event,
                context={'request': request,
                         'competition': competition,
                         'event': event,
                         'detachment_report': detachment_report},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(detachment_report=detachment_report,
                            is_verified=False)
        return Response(Q12ReportSerializer(detachment_report).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q12Serializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        event = self.get_object()
        if event.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            event.is_verified = True
            event.save()
            return Response(Q12Serializer(event).data,
                            status=status.HTTP_200_OK)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q5DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """Показатель 5. Выводится полный список (т.к. верифицирующее лицо -
    сотрудник ЦШ).

    Пример POST-запроса:
    ```
    {
      "participants_data": [
        {
          "name": "Фамилия Имя Отчества",
          "document": <FILE>
        },
        {
          "name": "Фамилия Имя Отчества",
          "document": <FILE>
        }
      ]
    }

    Доступ:
        - GET: Всем пользователям;
        - POST: Командирам отрядов, принимающих участие в конкурсе;
        - VERIFY-EVENT (POST/DELETE): Комиссарам РШ подвластных отрядов;
        - GET-PLACE (GET): Всем пользователям

    Note:
        - 404 возвращается в случае, если не найден объект конкурса или отряд,
          в котором юзер является командиром
    ```
    """

    permission_classes = (
        permissions.IsAuthenticated, IsCompetitionParticipantAndCommander,
    )
    MAX_PLACE = 20

    def get_serializer_class(self):
        if self.action == 'create':
            return Q5DetachmentReportWriteSerializer
        return Q5DetachmentReportReadSerializer

    def get_queryset(self):
        if self.action == 'me':
            return self.serializer_class.Meta.model.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        return self.serializer_class.Meta.model.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        if isinstance(request.data, QueryDict):
            data_dict = {}
            for key, value in request.data.lists():
                match = re.match(r'participants_data\[(\d+)\]\[(\w+)\]', key)
                if match:
                    index, field_name = match.groups()
                    index = int(index)
                    if index not in data_dict:
                        data_dict[index] = {}
                    data_dict[index][field_name] = value[0] if len(value) == 1 else value

            participants_data = list(data_dict.values())

            for i, participant in enumerate(participants_data):
                file_key = f'participants_data[{i}][document]'
                if file_key in request.FILES:
                    participant['document'] = request.FILES[file_key]
        if not participants_data:
            return Response(
                {
                    'non_field_errors': f'participants_data '
                                        f'должно быть заполнено. Присланный реквест: {request.data}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            report, created = Q5DetachmentReport.objects.get_or_create(
                competition_id=competition.id,
                detachment_id=detachment.id
            )

            for participant_data in participants_data:
                event_serializer = Q5EducatedParticipantSerializer(
                    data=participant_data)
                if event_serializer.is_valid(raise_exception=True):
                    Q5EducatedParticipant.objects.create(
                        **event_serializer.validated_data,
                        detachment_report=report
                    )
                else:
                    return Response(event_serializer.errors,
                                    status=status.HTTP_400_BAD_REQUEST)

            return Response(
                self.get_serializer(report).data,
                status=(
                    status.HTTP_201_CREATED if created else status.HTTP_200_OK
                )
            )

    def perform_create(self, serializer):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer.save(competition=competition, detachment=detachment)

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    @action(detail=False, methods=['get'], url_path='get-place',
            permission_classes=(IsCompetitionParticipantAndCommander,))
    def get_place(self, request, **kwargs):
        detachment = self.request.user.detachment_commander
        competition_id = self.kwargs.get('competition_pk')
        report = Q5DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=competition_id
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tandem_ranking = Q5TandemRanking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if not tandem_ranking:
            tandem_ranking = Q5TandemRanking.objects.filter(
                junior_detachment=report.detachment,
                competition_id=competition_id
            ).first()

        if tandem_ranking and tandem_ranking.place is not None:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )

        ranking = Q5Ranking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if ranking and ranking.place is not None:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )

        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='verify-raw/(?P<participant_id>\d+)',
        permission_classes=[
            permissions.IsAuthenticated,
            IsCentralEventMaster
        ]
    )
    def verify_raw(self, request, competition_pk=None, pk=None,
                   participant_id=None):
        """
        Верифицирует конкретное мероприятие по его ID.
        """
        report = self.get_object()
        raw = get_object_or_404(
            Q5EducatedParticipant,
            pk=participant_id,
            detachment_report=report
        )
        if raw.is_verified:
            return Response({
                'detail': 'Данный отчет уже верифицирован'
            }, status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            raw.is_verified = True
            raw.save()
            return Response(
                {"status": "Данные по организации "
                           "мероприятия верифицированы"},
                status=status.HTTP_200_OK
            )
        raw.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q6DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """
    Список выводится только по региону комиссара!

    Доступ:
        - GET: Всем пользователям;
        - POST: Командирам отрядов, принимающих участие в конкурсе;
        - VERIFY (POST/DELETE): Комиссарам РШ подвластных отрядов;
        - GET-PLACE (GET): Всем пользователям
    """
    serializer_class = Q6DetachmentReportSerializer
    permission_classes = (IsCompetitionParticipantAndCommander,)

    def get_queryset(self):
        if self.action == 'list':
            regional_headquarter = (
                self.request.user.userregionalheadquarterposition.headquarter
            )
            return self.serializer_class.Meta.model.objects.filter(
                detachment__regional_headquarter=regional_headquarter,
                competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'me':
            return self.serializer_class.Meta.model.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        return self.serializer_class.Meta.model.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(), IsRegionalCommissioner()]
        return super().get_permissions()

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=Q6DetachmentReportSerializer)
    def create(self, request, *args, **kwargs):
        competition = get_object_or_404(Competitions, id=self.kwargs.get('competition_pk'))
        try:
            detachment_id = request.user.detachment_commander.id
        except Detachment.DoesNotExist:
            return Response({"detail": "У пользователя нет командируемого отряда."},
                            status=status.HTTP_400_BAD_REQUEST)

        report, created = Q6DetachmentReport.objects.get_or_create(
            competition=competition,
            detachment_id=detachment_id,
            defaults=request.data
        )

        # Если отчет уже существовал, обновляем его данными из запроса
        if not created:
            for field, value in request.data.items():
                setattr(report, field, value)
            report.save()

        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def perform_create(self, serializer):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer.save(competition=competition, detachment=detachment)

    @action(
        detail=True,
        url_path='verify',
        methods=(['POST', 'DELETE']),
        permission_classes=[
            permissions.IsAuthenticated
        ]
    )
    def verify(self, request, *args, **kwargs):
        """Верификация отчета по показателю.

        Доступно только командиру РШ связанного с отрядом.
        Если отчет уже верифицирован, возвращается 400 Bad Request с описанием
        ошибки `{"detail": "Данный отчет уже верифицирован"}`.
        """
        detachment_report = self.get_object()
        detachment = detachment_report.detachment
        if detachment.regional_headquarter.commander != request.user:
            return Response({
                'detail': 'Только командир РШ из иерархии может '
                          'верифицировать отчеты по данному показателю'
            }, status=status.HTTP_403_FORBIDDEN)
        if detachment_report.is_verified:
            return Response({
                'detail': 'Данный отчет уже верифицирован'
            }, status=status.HTTP_400_BAD_REQUEST)
        if self.request.method == 'POST':
            detachment_report.is_verified = True
            detachment_report.save()
            return Response(status=status.HTTP_201_CREATED)
        if self.request.method == 'DELETE':
            detachment_report.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    @action(detail=False, methods=['get'], url_path='get-place',
            permission_classes=(IsCompetitionParticipantAndCommander,))
    def get_place(self, request, **kwargs):
        detachment = self.request.user.detachment_commander
        competition_id = self.kwargs.get('competition_pk')
        report = Q6DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=self.kwargs.get('competition_pk')
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tandem_ranking = Q6TandemRanking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if not tandem_ranking:
            tandem_ranking = Q6TandemRanking.objects.filter(
                junior_detachment=report.detachment,
                competition_id=competition_id
            ).first()

        if tandem_ranking and tandem_ranking.place is not None:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )

        ranking = Q6Ranking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if ranking and ranking.place is not None:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )

        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_404_NOT_FOUND
        )


class Q5EducatedParticipantViewSet(UpdateDestroyViewSet):
    """
    Обеспечивает возможность редактирования и
    удаления объектов Q5EducatedParticipant.

    - `PUT/PATCH`: Обновляет объект Q5EducatedParticipant, если
                   он не был верифицирован.
                   Ограничено для объектов, принадлежащих отчету подразделения
                   пользователя (где является командиром).

    - `DELETE`: Удаляет объект Q5EducatedParticipant,
                если он не был верифицирован.
                Ограничено для объектов, принадлежащих отчету
                подразделения пользователя (где является командиром).

    Примечание: Операции обновления и удаления доступны только
                если `is_verified` объекта равно `False`
                и если подразделение пользователя  (где является командиром)
                соответствует подразделению в отчете.
    """

    serializer_class = Q5EducatedParticipantSerializer
    permission_classes = (IsQ5DetachmentReportAuthor,)

    def get_queryset(self):
        report_pk = self.kwargs.get('report_pk')
        return Q5EducatedParticipant.objects.filter(
            detachment_report_id=report_pk
        )

    def update(self, request, *args, **kwargs):
        event_org = self.get_object()
        if event_org.is_verified:
            return Response(
                {
                    'detail': 'Нельзя редактировать/удалять верифицированные '
                              'записи.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        event_org = self.get_object()
        if event_org.is_verified:
            return Response(
                {
                    'detail': 'Нельзя редактировать/удалять верифицированные '
                              'записи.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class Q15DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """Показатель 15.

    Доступ:
        - GET: Всем пользователям;
        - list (GET) командирам РШ, выводятся отчеты только его рег штаба;
        - POST: Командирам отрядов, принимающих участие в конкурсе;
        - VERIFY-EVENT (POST/DELETE): Комиссарам РШ подвластных отрядов;
        - GET-PLACE (GET): Всем пользователям

    Note:
        - 404 возвращается в случае, если не найден объект конкурса или отряд,
          в котором юзер является командиром
    ```
    """

    permission_classes = (
        permissions.IsAuthenticated, IsCompetitionParticipantAndCommander,
    )

    def get_serializer_class(self):
        if self.action == 'create':
            return Q15DetachmentReportWriteSerializer
        return Q15DetachmentReportReadSerializer

    def get_queryset(self):
        if self.action == 'me':
            return self.serializer_class.Meta.model.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'list':
            try:
                regional_headquarter = (
                    self.request.user.regionalheadquarter_commander
                )
            except ObjectDoesNotExist:
                return Q15DetachmentReport.objects.all()
            return Q15DetachmentReport.objects.filter(
                detachment__regional_headquarter=regional_headquarter,
                competition_id=self.kwargs.get('competition_pk')
            )
        return self.serializer_class.Meta.model.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        return super().get_permissions()

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        grants_data = request.data.get('grants_data', [])

        if not grants_data:
            return Response(
                {
                    'non_field_errors': 'grants_data '
                                        'должно быть заполнено'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            report, created = Q15DetachmentReport.objects.get_or_create(
                competition_id=competition.id,
                detachment_id=detachment.id
            )

            for grant_data in grants_data:
                event_serializer = Q15GrantWinnerSerializer(
                    data=grant_data)
                if event_serializer.is_valid(raise_exception=True):
                    Q15GrantWinner.objects.create(
                        **event_serializer.validated_data,
                        detachment_report=report
                    )
                else:
                    return Response(event_serializer.errors,
                                    status=status.HTTP_400_BAD_REQUEST)

            return Response(
                self.get_serializer(report).data,
                status=(
                    status.HTTP_201_CREATED if created else status.HTTP_200_OK
                )
            )

    def perform_create(self, serializer):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer.save(competition=competition, detachment=detachment)

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    @action(detail=False, methods=['get'], url_path='get-place',
            permission_classes=(IsCompetitionParticipantAndCommander,))
    def get_place(self, request, **kwargs):
        detachment = self.request.user.detachment_commander
        competition_id = self.kwargs.get('competition_pk')
        report = Q15DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=competition_id
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tandem_ranking = Q15TandemRank.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if not tandem_ranking:
            tandem_ranking = Q15Rank.objects.filter(
                junior_detachment=report.detachment,
                competition_id=competition_id
            ).first()

        if tandem_ranking and tandem_ranking.place is not None:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )

        ranking = Q15Rank.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if ranking and ranking.place is not None:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )

        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='verify-raw/(?P<grant_id>\d+)',
        permission_classes=[
            permissions.IsAuthenticated
        ]
    )
    def verify_raw(self, request, competition_pk=None, pk=None,
                   grant_id=None):
        """
        Верифицирует конкретное мероприятие по его ID.
        """
        report = self.get_object()
        detachment = report.detachment
        if detachment.regional_headquarter.commander != request.user:
            return Response({
                'detail': 'Только командир РШ из иерархии может '
                          'верифицировать отчеты по данному показателю'
            }, status=status.HTTP_403_FORBIDDEN)
        raw = get_object_or_404(
            Q15GrantWinner,
            pk=grant_id,
            detachment_report=report
        )
        if raw.is_verified:
            return Response({
                'detail': 'Данный отчет уже верифицирован'
            }, status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            raw.is_verified = True
            raw.save()
            return Response(
                {"status": "Данные по организации "
                           "мероприятия верифицированы"},
                status=status.HTTP_200_OK
            )
        raw.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q15GrantDataViewSet(UpdateDestroyViewSet):
    """
    Обеспечивает возможность редактирования и
    удаления объектов Q15GrantData.

    - `PUT/PATCH`: Обновляет объект Q15, если
                   он не был верифицирован.
                   Ограничено для объектов, принадлежащих отчету подразделения
                   пользователя (где является командиром).

    - `DELETE`: Удаляет объект Q15,
                если он не был верифицирован.
                Ограничено для объектов, принадлежащих отчету
                подразделения пользователя (где является командиром).

    Примечание: Операции обновления и удаления доступны только
                если `is_verified` объекта равно `False`
                и если подразделение пользователя (где является командиром)
                соответствует подразделению в отчете.
    """

    serializer_class = Q15GrantWinnerSerializer
    permission_classes = (IsQ15DetachmentReportAuthor,)

    def get_queryset(self):
        report_pk = self.kwargs.get('report_pk')
        return Q15GrantWinner.objects.filter(
            detachment_report_id=report_pk
        )

    def update(self, request, *args, **kwargs):
        event_org = self.get_object()
        if event_org.is_verified:
            return Response(
                {
                    'detail': 'Нельзя редактировать/удалять верифицированные '
                              'записи.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        event_org = self.get_object()
        if event_org.is_verified:
            return Response(
                {
                    'detail': 'Нельзя редактировать/удалять верифицированные '
                              'записи.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class Q13DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """Показатель "Организация собственных мероприятий отряда".

    Выводятся записи только по РШ комиссара!

    Пример POST-запроса:
    ```
    {
      "organization_data": [
        {
          "event_type": "Спортивное",
          "event_link": "https://some-link.com"
        },
        {
          "event_type": "Волонтерское",
          "event_link": "https://some-link.com"
        }
      ]
    }

    Доступ:
        - GET: Всем пользователям;
        - POST: Командирам отрядов, принимающих участие в конкурсе;
        - VERIFY-EVENT (POST/DELETE): Комиссарам РШ подвластных отрядов;
        - GET-PLACE (GET): Всем пользователям

    Note:
        - 404 возвращается в случае, если не найден объект конкурса или отряд,
          в котором юзер является командиром
    ```
    """

    permission_classes = (IsCompetitionParticipantAndCommander,)

    MAX_PLACE = 6

    def get_serializer_class(self):
        if self.action == 'create':
            return Q13DetachmentReportWriteSerializer
        return Q13DetachmentReportReadSerializer

    def get_queryset(self):
        if self.action == 'list':
            regional_headquarter = (
                self.request.user.userregionalheadquarterposition.headquarter
            )
            return self.serializer_class.Meta.model.objects.filter(
                detachment__regional_headquarter=regional_headquarter,
                competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'me':
            return self.serializer_class.Meta.model.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        return self.serializer_class.Meta.model.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(), IsRegionalCommissioner()]
        return super().get_permissions()

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['organization_data'],
            properties={
                'organization_data': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="Список организованных мероприятий",
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'event_type': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description="Тип мероприятия",
                                enum=[
                                    "Спортивное",
                                    "Волонтерское",
                                    "Интеллектуальное",
                                    "Творческое",
                                    "Внутреннее"
                                ]
                            ),
                            'event_link': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description="Ссылка на публикацию "
                                            "о мероприятии",
                                format='url'
                            )
                        }
                    )
                )
            }
        ),
    )
    def create(self, request, *args, **kwargs):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        organization_data = request.data.get('organization_data', [])

        if not CompetitionParticipants.objects.filter(
                competition=competition,
                junior_detachment=detachment
        ).exists() and not CompetitionParticipants.objects.filter(
            competition=competition,
            detachment=detachment
        ).exists():
            return Response(
                {
                    'error': 'Отряд подающего пользователя не '
                             'участвует в конкурсе.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not organization_data:
            return Response(
                {
                    'non_field_errors': 'organization_data '
                                        'должно быть заполнено'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            report, created = Q13DetachmentReport.objects.get_or_create(
                competition_id=competition.id,
                detachment_id=detachment.id
            )

            for event_data in organization_data:
                event_serializer = Q13EventOrganizationSerializer(
                    data=event_data)
                if event_serializer.is_valid(raise_exception=True):
                    Q13EventOrganization.objects.create(
                        **event_serializer.validated_data,
                        detachment_report=report
                    )
                else:
                    return Response(event_serializer.errors,
                                    status=status.HTTP_400_BAD_REQUEST)

            return Response(
                self.get_serializer(report).data,
                status=(
                    status.HTTP_201_CREATED if created else status.HTTP_200_OK
                )
            )

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    def perform_create(self, serializer):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer.save(competition=competition, detachment=detachment)

    @action(detail=False, methods=['get'], url_path='get-place',
            permission_classes=(IsCompetitionParticipantAndCommander,))
    def get_place(self, request, **kwargs):
        detachment = self.request.user.detachment_commander
        competition_id = self.kwargs.get('competition_pk')
        report = Q13DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=competition_id
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tandem_ranking = Q13TandemRanking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id

        ).first()
        if not tandem_ranking:
            tandem_ranking = Q13TandemRanking.objects.filter(
                junior_detachment=report.detachment,
                competition_id=competition_id
            ).first()

        # Пытаемся найти place в Q13TandemRanking
        if tandem_ranking and tandem_ranking.place is not None:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )

        # Если не найдено в Q13TandemRanking, ищем в Q13Ranking
        ranking = Q13Ranking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if ranking and ranking.place is not None:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )

        # Если не найдено ни в одной из моделей
        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='verify-event/(?P<event_id>\d+)',
        permission_classes=[
            permissions.IsAuthenticated, IsRegionalCommissioner,
        ]
    )
    def verify_event(self, request, competition_pk=None, pk=None,
                     event_id=None):
        """
        Верифицирует конкретное мероприятие по его ID.
        """
        report = self.get_object()
        competition_id = self.kwargs.get('competition_pk')
        event = get_object_or_404(
            Q13EventOrganization,
            pk=event_id,
            detachment_report=report
        )
        if event.is_verified:
            return Response({
                'detail': 'Данный отчет уже верифицирован'
            }, status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            event.is_verified = True
            event.save()
            participants_entry = CompetitionParticipants.objects.filter(
                junior_detachment=report.detachment,
                competition_id=competition_id
            ).first()

            # Подсчет места для индивидуальных и тандем участников:
            if participants_entry and not participants_entry.detachment:
                Q13Ranking.objects.get_or_create(
                    competition_id=competition_id,
                    detachment=report.detachment,
                    place=calculate_q13_place(
                        Q13EventOrganization.objects.filter(
                            detachment_report=report,
                            is_verified=True
                        )
                    )
                )
            else:
                if participants_entry:
                    tandem_ranking, _ = Q13TandemRanking.objects.get_or_create(
                        competition_id=competition_id,
                        junior_detachment=report.detachment,
                        detachment=participants_entry.detachment
                    )
                    tandem_ranking.place = calculate_q13_place(
                        Q13EventOrganization.objects.filter(
                            competition_id=competition_id,
                            detachment_report=report,
                            is_verified=True
                        )
                    )
                    elder_detachment_report = None
                    try:
                        elder_detachment_report = Q13DetachmentReport.objects.get(
                            competition_id=competition_id,
                            detachment=tandem_ranking.detachment
                        )
                    except Q13DetachmentReport.DoesNotExist:
                        tandem_ranking.place += self.MAX_PLACE
                    if elder_detachment_report:
                        tandem_ranking.place += calculate_q13_place(
                            Q13EventOrganization.objects.filter(
                                competition_id=competition_id,
                                detachment_report=elder_detachment_report,
                                is_verified=True
                            )
                        )
                else:
                    participants_entry = CompetitionParticipants.objects.filter(
                        competition_id=competition_id,
                        detachment=report.detachment
                    ).first()
                    if not participants_entry:
                        return Response(
                            {'error': 'отряд не найден в участниках'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    tandem_ranking, _ = Q13TandemRanking.objects.get_or_create(
                        competition_id=competition_id,
                        junior_detachment=participants_entry.junior_detachment,
                        detachment=report.detachment
                    )
                    tandem_ranking.place = calculate_q13_place(
                        Q13EventOrganization.objects.filter(
                            competition_id=competition_id,
                            detachment_report=report,
                            is_verified=True
                        )
                    )
                    junior_detachment_report = None
                    try:
                        junior_detachment_report = Q13DetachmentReport.objects.get(
                            competition_id=competition_id,
                            detachment=tandem_ranking.junior_detachment
                        )
                    except Q13DetachmentReport.DoesNotExist:
                        tandem_ranking.place += self.MAX_PLACE
                    if junior_detachment_report:
                        tandem_ranking.place += calculate_q13_place(
                            Q13EventOrganization.objects.filter(
                                competition_id=competition_id,
                                detachment_report=junior_detachment_report,
                                is_verified=True
                            )
                        )
                tandem_ranking.place = round(tandem_ranking.place / 2, 2)
                tandem_ranking.save()
            return Response(
                {"status": "Данные по организации "
                           "мероприятия верифицированы"},
                status=status.HTTP_200_OK
            )
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Q13EventOrganizationViewSet(UpdateDestroyViewSet):
    """
    Обеспечивает возможность редактирования и
    удаления объектов Q13EventOrganization.

    - `PUT/PATCH`: Обновляет объект Q13EventOrganization, если
                   он не был верифицирован.
                   Ограничено для объектов, принадлежащих отчету подразделения
                   пользователя (где является командиром).

    - `DELETE`: Удаляет объект Q13EventOrganization,
                если он не был верифицирован.
                Ограничено для объектов, принадлежащих отчету
                подразделения пользователя (где является командиром).

    Примечание: Операции обновления и удаления доступны только
                если `is_verified` объекта равно `False`
                и если подразделение пользователя  (где является командиром)
                соответствует подразделению в отчете.
    """

    serializer_class = Q13EventOrganizationSerializer
    permission_classes = (IsQ13DetachmentReportAuthor,)

    def get_queryset(self):
        report_pk = self.kwargs.get('report_pk')
        return Q13EventOrganization.objects.filter(
            detachment_report_id=report_pk
        )

    def update(self, request, *args, **kwargs):
        event_org = self.get_object()
        if event_org.is_verified:
            return Response(
                {
                    'detail': 'Нельзя редактировать/удалять верифицированные '
                              'записи.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        event_org = self.get_object()
        if event_org.is_verified:
            return Response(
                {
                    'detail': 'Нельзя редактировать/удалять верифицированные '
                              'записи.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class Q14DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """
    Отношение количества бойцов, отработавших в летнем трудовом семестре
    к общему числу членов отряда.

    Пример POST-запроса:
    {
      "q14_labor_project": {
        "lab_project_name": "string",
        "amount": 5
      }
    }

    Оба поля ввода обязательные. При нажатии на “Добавить проект”
    подгружается новый блок с полями:“Наименование трудового проекта” и
    “Количество бойцов, отработавших в летнем трудовом семестре”.
    Количество подгружаемых блоков не ограничено. В поле “Количество бойцов,
    отработавших в летнем трудовом семестре” водятся цифры от 1 до 1000
    включительно.

    Программа должна посчитать сумму всех чисел в полях “Количества бойцов,
    отработавших в летнем трудовом семестре” и разделить ее на количество
    участников отряда на дату 15 июня 2024 года. Полученную цифру сравнить
    с цифрами из ответов других отрядов и определить место.
    Чем ближе цифра к единице - тем выше место
    (1 раз до 30 сентября отправка показателя).

    """
    serializer_class = Q14DetachmentReportSerializer

    def get_queryset(self):
        return Q14DetachmentReport.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated(),
                    IsCommanderDetachmentInParameterOrRegionalCommander()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAuthor()]
        return super().get_permissions()

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    def create(self, request, *args, **kwargs):

        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        q14_amount = request.data.get(
            'q14_labor_project'
        ).get('amount')
        q14_lp_name = request.data.get(
            'q14_labor_project'
        ).get('lab_project_name')
        if not q14_amount:
            return Response(
                {'error': 'Не введено количество бойцов.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            detachment = get_object_or_404(
                Detachment, id=request.user.detachment_commander.id
            )
        except Detachment.DoesNotExist:
            return Response(
                {'error': 'Заполнять данные может только командир отряда.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # TODO заменить на фильтрацию с Q ->
        if not CompetitionParticipants.objects.filter(
                competition=competition, detachment=detachment
        ).exists():
            if not CompetitionParticipants.objects.filter(
                    competition=competition, junior_detachment=detachment
            ).exists():
                return Response(
                    {
                        'error': 'Отряд не зарегистрирован'
                                 ' как участник конкурса.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        detachment_lab_projects = Q14DetachmentReport.objects.filter(
            detachment=detachment.id
        ).values_list('q14_labor_project', flat=True)
        if not len(detachment_lab_projects) == 0:
            for id in detachment_lab_projects:
                lab_project_name = Q14LaborProject.objects.get(
                    id=id
                ).lab_project_name
                if (q14_lp_name == lab_project_name):
                    return Response(
                        {
                            'error': (
                                'Отчет для этого трудового проекта '
                                'у данного отряда уже существует.'
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
        return super().create(request, *args, **kwargs)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения списка отчетов отряда текущего пользователя.

        Доступ: все авторизованные пользователи.
        Если пользователь не командир отряда, и у его отряда нет
        поданных отчетов - вернется пустой список.
        """
        return super().list(request, *args, **kwargs)

    @action(
        detail=False,
        methods=['get'],
        url_path='get-place',
        serializer_class=None,
        permission_classes=[permissions.IsAuthenticated, ]
    )
    def get_place(self, request, competition_pk, **kwargs):
        """Определение места по показателю.

        Возвращается место или статус показателя.
        Если показатель не был подан ранее, то возвращается код 400.
        """

        detachment = self.request.user.detachment_commander
        report = Q14DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=self.kwargs.get('competition_pk')
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        is_verified = report.is_verified
        is_tandem = tandem_or_start(
            competition=report.competition,
            detachment=report.detachment,
            competition_model=CompetitionParticipants
        )

        if not is_verified:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': 'Показатель в обработке.'}
            )
        tandem_ranking = getattr(
            detachment, 'q14tandemranking_main_detachment'
        ).filter(competition_id=competition_pk).first()
        if not tandem_ranking:
            tandem_ranking = getattr(
                detachment, 'q14tandemranking_junior_detachment'
            ).filter(competition_id=competition_pk).first()

        if is_tandem:
            if tandem_ranking and tandem_ranking.place is not None:
                return Response(
                    {'place': tandem_ranking.place},
                    status=status.HTTP_200_OK
                )
        else:
            ranking = Q14Ranking.objects.filter(
                detachment=report.detachment
            ).first()
            if ranking and ranking.place is not None:
                return Response(
                    {'place': ranking.place}, status=status.HTTP_200_OK
                )

        return Response(
            status=status.HTTP_404_NOT_FOUND,
            data={'detail': 'Показатель в обработке.'}
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        serializer_class=None,
    )
    def verify(self, *args, **kwargs):
        """Верификация отчета по показателю.

        Доступно только командиру РШ связанного с отрядом.
        Если отчет уже верифицирован, возвращается 400 Bad Request с описанием
        ошибки `{"detail": "Данный отчет уже верифицирован"}`.
        При удалении отчета удаляются записи из таблиц Rankin и TandemRankin.
        """

        detachment_report = self.get_object()

        if self.request.method == 'DELETE':
            if detachment_report.is_verified:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={'detail': 'Верифицированный отчет нельзя удалить.'}
                )
            detachment_report.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        with transaction.atomic():
            if detachment_report.is_verified:
                return Response({
                    'detail': 'Данный отчет уже верифицирован'
                }, status=status.HTTP_400_BAD_REQUEST)

            detachment_report.is_verified = True
            detachment_report.save()
            return Response(status=status.HTTP_200_OK)


class Q17DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """
    Количество упоминаний в СМИ о прошедших творческих, добровольческих
    и патриотических мероприятиях отряда.

    Пример POST-запроса:
    {
      "q17_event": {
        "source_name": "string2"
      },
      "q17_link": {
        "link": "http://127.0.0.1:8000/swagger/"
      }
    }

    Оба поля ввода обязательные. При нажатии на “Добавить источник”
    подгружается новый блок с полями: “Наименование источника”,
    “Ссылка на публикацию”. Количество подгружаемых блоков не ограничено.

    Программа должна посчитать количество заполненных блоков.
    Итоговую цифру сравнить с цифрами из ответов других отрядов,
    присвоить место. 1 место - самая большая цифра.

    """

    serializer_class = Q17DetachmentReportSerializer

    def get_queryset(self):
        return Q17DetachmentReport.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated(),
                    IsCommanderDetachmentInParameterOrRegionalCommander()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAuthor()]
        return super().get_permissions()

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    def create(self, request, *args, **kwargs):

        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        q17_link = request.data.get(
            'q17_link'
        ).get('link')
        if not q17_link:
            return Response(
                {'error': 'Не заполнена ссылка.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            detachment = get_object_or_404(
                Detachment, id=request.user.detachment_commander.id
            )
        except Detachment.DoesNotExist:
            return Response(
                {'error': 'Заполнять данные может только командир отряда.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # TODO заменить на фильтрацию с Q ->
        if not CompetitionParticipants.objects.filter(
                competition=competition, detachment=detachment
        ).exists():
            if not CompetitionParticipants.objects.filter(
                    competition=competition, junior_detachment=detachment
            ).exists():
                return Response(
                    {
                        'error': 'Отряд не зарегистрирован'
                                 ' как участник конкурса.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        detachment_links = Q17DetachmentReport.objects.filter(
            detachment=detachment.id
        ).values_list('q17_link', flat=True)
        if not len(detachment_links) == 0:
            for id in detachment_links:
                link_url = Q17Link.objects.get(id=id).link
                if q17_link == link_url:
                    return Response(
                        {
                            'error': (
                                'Отчет с этой ссылкой и отрядом уже существует.'
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

        return super().create(request, *args, **kwargs)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения списка отчетов отряда текущего пользователя.

        Доступ: все авторизованные пользователи.
        Если пользователь не командир отряда, и у его отряда нет
        поданных отчетов - вернется пустой список.
        """
        return super().list(request, *args, **kwargs)

    @action(
        detail=False,
        methods=['get'],
        url_path='get-place',
        serializer_class=None,
        permission_classes=[permissions.IsAuthenticated, ]
    )
    def get_place(self, request, competition_pk, **kwargs):
        """Определение места по показателю.

        Возвращается место или статус показателя.
        Если показатель не был подан ранее, то возвращается код 400.
        """

        detachment = self.request.user.detachment_commander
        report = Q17DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=self.kwargs.get('competition_pk')
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        is_verified = report.is_verified
        is_tandem = tandem_or_start(
            competition=report.competition,
            detachment=report.detachment,
            competition_model=CompetitionParticipants
        )

        if not is_verified:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': 'Показатель в обработке.'}
            )
        tandem_ranking = getattr(
            detachment, 'q17tandemranking_main_detachment'
        ).filter(competition_id=competition_pk).first()
        if not tandem_ranking:
            tandem_ranking = getattr(
                detachment, 'q17tandemranking_junior_detachment'
            ).filter(competition_id=competition_pk).first()

        if is_tandem:
            if tandem_ranking and tandem_ranking.place is not None:
                return Response(
                    {'place': tandem_ranking.place},
                    status=status.HTTP_200_OK
                )
        else:
            ranking = Q17Ranking.objects.filter(
                detachment=report.detachment
            ).first()
            if ranking and ranking.place is not None:
                return Response(
                    {'place': ranking.place}, status=status.HTTP_200_OK
                )

        return Response(
            status=status.HTTP_404_NOT_FOUND,
            data={'detail': 'Показатель в обработке.'}
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        serializer_class=None,
    )
    def verify(self, *args, **kwargs):
        """Верификация отчета по показателю.

        Доступно только командиру РШ связанного с отрядом.
        Если отчет уже верифицирован, возвращается 400 Bad Request с описанием
        ошибки `{"detail": "Данный отчет уже верифицирован"}`.
        При удалении отчета удаляются записи из таблиц Rankin и TandemRankin.
        """

        detachment_report = self.get_object()

        if self.request.method == 'DELETE':
            if detachment_report.is_verified:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={'detail': 'Верифицированный отчет нельзя удалить.'}
                )
            detachment_report.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        with transaction.atomic():
            if detachment_report.is_verified:
                return Response({
                    'detail': 'Данный отчет уже верифицирован'
                }, status=status.HTTP_400_BAD_REQUEST)

            detachment_report.is_verified = True
            detachment_report.save()
            return Response(status=status.HTTP_200_OK)


class Q18DetachmentReportViewSet(ListRetrieveCreateViewSet):
    """
    Показатель "Охват бойцов, принявших участие во Всероссийском
    дне Ударного труда."

    Доступ:
        - list (GET) командирам РШ, выводятся отчеты только его рег штаба;
        - retrieve (GET): Всем пользователям;
        - POST: Командирам отрядов, принимающих участие в конкурсе;
        - VERIFY (POST/DELETE): Комиссарам РШ подвластных отрядов;
        - GET-PLACE (GET): Всем пользователям
    """
    serializer_class = Q18DetachmentReportSerializer
    permission_classes = (IsCompetitionParticipantAndCommander,)

    def get_queryset(self):
        if self.action == 'list':
            try:
                regional_headquarter = (
                    self.request.user.regionalheadquarter_commander
                )
            except ObjectDoesNotExist:
                return Q18DetachmentReport.objects.all()
            return Q18DetachmentReport.objects.filter(
                detachment__regional_headquarter=regional_headquarter,
                competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'me':
            return self.serializer_class.Meta.model.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        return self.serializer_class.Meta.model.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        return super().get_permissions()

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=Q18DetachmentReportSerializer)
    def create(self, request, *args, **kwargs):
        context = super().get_serializer_context()
        competition_id = self.kwargs.get('competition_pk')
        try:
            detachment_id = self.request.user.detachment_commander.id
        except Detachment.DoesNotExist:
            detachment_id = None
        context['competition'] = get_object_or_404(
            Competitions, id=competition_id
        )
        context['detachment'] = get_object_or_404(
            Detachment, id=detachment_id
        )
        serializer = self.get_serializer(
            data=request.data, context=context
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        competition = get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer.save(competition=competition, detachment=detachment)

    @action(
        detail=True,
        url_path='verify',
        methods=(['POST', 'DELETE']),
        permission_classes=[
            permissions.IsAuthenticated
        ]
    )
    def verify(self, request, *args, **kwargs):
        """Верификация отчета по показателю.

        Доступно только командиру РШ связанного с отрядом.
        Если отчет уже верифицирован, возвращается 400 Bad Request с описанием
        ошибки `{"detail": "Данный отчет уже верифицирован"}`.
        """
        detachment_report = self.get_object()
        detachment = detachment_report.detachment
        if detachment.regional_headquarter.commander != request.user:
            return Response({
                'detail': 'Только командир РШ из иерархии может '
                          'верифицировать отчеты по данному показателю'
            }, status=status.HTTP_403_FORBIDDEN)
        if detachment_report.is_verified:
            return Response({
                'detail': 'Данный отчет уже верифицирован'
            }, status=status.HTTP_400_BAD_REQUEST)
        if self.request.method == 'POST':
            detachment_report.is_verified = True
            detachment_report.save()
            return Response(status=status.HTTP_201_CREATED)
        if self.request.method == 'DELETE':
            detachment_report.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    @action(detail=False, methods=['get'], url_path='get-place',
            permission_classes=(IsCompetitionParticipantAndCommander,))
    def get_place(self, request, **kwargs):
        detachment = self.request.user.detachment_commander
        competition_id = self.kwargs.get('competition_pk')
        report = Q18DetachmentReport.objects.filter(
            detachment=detachment,
            competition_id=competition_id
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tandem_ranking = Q18TandemRanking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if not tandem_ranking:
            tandem_ranking = Q18TandemRanking.objects.filter(
                junior_detachment=report.detachment,
                competition_id=competition_id
            ).first()

        # Пытаемся найти place в Q18TandemRanking
        if tandem_ranking and tandem_ranking.place is not None:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )

        # Если не найдено в Q18TandemRanking, ищем в Q18Ranking
        ranking = Q18Ranking.objects.filter(
            detachment=report.detachment,
            competition_id=competition_id
        ).first()
        if ranking and ranking.place is not None:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )

        # Если не найдено ни в одной из моделей
        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_404_NOT_FOUND
        )


class Q19DetachmentReportViewset(CreateListRetrieveUpdateViewSet):
    """Вьюсет по показателю 'Отсутствие нарушений техники безопасности,
    охраны труда и противопожарной безопасности в трудовом семестре'.

    Доступ:
        - retrieve (GET) авторам отчета;
        - list (GET) командирам РШ, выводятся отчеты только его рег штаба;
        - create командирам отрядов-участников конкурса;
        - update командирам отрядов-участников конкурса;
    """
    serializer_class = Q19DetachmenrtReportSerializer
    permission_classes = (
        permissions.IsAuthenticated, IsCompetitionParticipantAndCommander
    )

    MAX_PLACE = 2

    def get_queryset(self):
        if self.action == 'list':
            try:
                regional_headquarter = (
                    self.request.user.regionalheadquarter_commander
                )
            except ObjectDoesNotExist:
                return Q19Report.objects.all()
            return Q19Report.objects.filter(
                detachment__regional_headquarter=regional_headquarter,
                competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'me':
            return Q19Report.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        return Q19Report.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated(),
                    IsCommanderDetachmentInParameterOrRegionalCommander()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAdmin()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(),
                    IsRegionalCommanderOrAuthor()]
        return super().get_permissions()

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения своего отчета по параметру 19
        для текущего пользователя.

        Доступ: все авторизованные пользователи.
        Если пользователь не командир отряда, или у его отряда нет
        поданного отчета - вернется пустой список.
        """
        return super().list(request, *args, **kwargs)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='verify',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommanderOrAdmin,)
            )
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: "Данные успешно верифицированы"}
    )
    def verify(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.

        Доступ: рег. командиры или админ
        """
        report = self.get_object()
        if report.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            report.is_verified = True
            report.save()
            participants_entry = CompetitionParticipants.objects.filter(
                competition_id=settings.COMPETITION_ID,
                junior_detachment=report.detachment
            ).first()

            # Подсчет места для индивидуальных и тандем участников:
            if participants_entry and not participants_entry.detachment:
                Q19Ranking.objects.get_or_create(
                    competition_id=settings.COMPETITION_ID,
                    detachment=report.detachment,
                    place=calculate_q19_place(report)
                )
            else:
                if participants_entry:
                    tandem_ranking, _ = Q19TandemRanking.objects.get_or_create(
                        competition_id=settings.COMPETITION_ID,
                        junior_detachment=report.detachment,
                        detachment=participants_entry.detachment
                    )
                    tandem_ranking.place = calculate_q19_place(report)
                    elder_detachment_report = None
                    try:
                        elder_detachment_report = Q19Report.objects.get(
                            competition_id=settings.COMPETITION_ID,
                            detachment=tandem_ranking.detachment
                        )
                    except Q19Report.DoesNotExist:
                        tandem_ranking.place += self.MAX_PLACE
                    if elder_detachment_report:
                        tandem_ranking.place += calculate_q19_place(elder_detachment_report)
                else:
                    participants_entry = CompetitionParticipants.objects.filter(
                        competition_id=settings.COMPETITION_ID,
                        detachment=report.detachment
                    ).first()
                    if not participants_entry:
                        return Response(
                            {'error': 'отряд не найден в участниках'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    tandem_ranking, _ = Q19TandemRanking.objects.get_or_create(
                        competition_id=settings.COMPETITION_ID,
                        junior_detachment=participants_entry.junior_detachment,
                        detachment=report.detachment
                    )
                    tandem_ranking.place = calculate_q19_place(report)
                    junior_detachment_report = None
                    try:
                        junior_detachment_report = Q19Report.objects.get(
                            competition_id=settings.COMPETITION_ID,
                            detachment=tandem_ranking.junior_detachment
                        )
                    except Q19Report.DoesNotExist:
                        tandem_ranking.place += self.MAX_PLACE
                    if junior_detachment_report:
                        tandem_ranking.place += calculate_q19_place(report)
                tandem_ranking.place = round(tandem_ranking.place / 2, 2)
                tandem_ranking.save()
            return Response(
                {"status": "Данные "
                           "Успешно верифицированы"},
                status=status.HTTP_200_OK
            )
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            url_path='get-place',
            permission_classes=(permissions.IsAuthenticated,
                                IsCompetitionParticipantAndCommander))
    def get_place(self, request, competition_pk, **kwargs):
        """
        Action для получения рейтинга по данному показателю.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        Если отчета еще не подан, вернется ошибка 404. (данные не отправлены)
        Если отчет подан, но еще не верифицировн - вернется
        {"place": "Показатель в обработке"}.
        Если отчет подан и верифицирован - вернется место в рейтинге:
        {"place": int}
        """
        detachment = self.request.user.detachment_commander
        report = Q19Report.objects.filter(
            detachment=detachment,
            competition_id=competition_pk
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ranking = getattr(
            detachment, 'q19ranking'
        ).filter(competition_id=competition_pk).first()
        if ranking:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )
        tandem_ranking = getattr(
            detachment, 'q19tandemranking_main_detachment'
        ).filter(competition_id=competition_pk).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        tandem_ranking = getattr(
            detachment, 'q19tandemranking_junior_detachment'
        ).filter(competition_id=competition_pk).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_200_OK
        )

    def create(self, request, competition_pk, *args, **kwargs):
        """
        Action для создания отчета по параметру 19
        для текущего пользователя.

        Доступ: командиры отрядов-участников конкурса.
        """
        competition = get_object_or_404(
            Competitions, id=competition_pk
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer = Q19DetachmenrtReportSerializer(data=request.data,
                                                    context={'request': request,
                                                             'competition': competition,
                                                             'detachment': detachment})
        serializer.is_valid(raise_exception=True)
        serializer.save(competition=competition, detachment=detachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class Q20ViewSet(CreateListRetrieveUpdateViewSet):
    """Вьюсет для показателя 'Соответствие требованиями положения символики
    и атрибутике форменной одежды и символики отрядов.'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
    """
    queryset = Q20Report.objects.all()
    serializer_class = Q20ReportSerializer
    permission_classes = (
        permissions.IsAuthenticated,
        IsCommanderDetachmentInParameterOrRegionalCommissioner
    )

    def get_queryset(self):
        if self.action == 'list':
            regional_headquarter = (
                self.request.user.userregionalheadquarterposition.headquarter
            )
            return Q20Report.objects.filter(
                detachment__regional_headquarter=regional_headquarter,
                competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'me':
            return Q20Report.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        return Q20Report.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(),
                    IsCommanderAndCompetitionParticipant()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(), IsRegionalCommissioner()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(),
                    IsRegionalCommissionerOrCommanderDetachmentWithVerif()]
        return super().get_permissions()

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения своего отчета по параметру 20
        для текущего пользователя.

        Доступ: все авторизованные пользователи.
        Если пользователь не командир отряда, или у его отряда нет
        поданного отчета - вернется пустой список.
        """
        return super().list(request, *args, **kwargs)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q20ReportSerializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации мероприятия рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        report = self.get_object()
        if report.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            report.is_verified = True
            report.save()
            return Response(Q20ReportSerializer(report).data,
                            status=status.HTTP_200_OK)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            url_path='get-place',
            permission_classes=(permissions.IsAuthenticated,
                                IsCompetitionParticipantAndCommander))
    def get_place(self, request, competition_pk, **kwargs):
        """
        Action для получения рейтинга по данному показателю.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        Если отчета еще не подан, вернется ошибка 404. (данные не отправлены)
        Если отчет подан, но еще не верифицировн - вернется
        {"place": "Показатель в обработке"}.
        Если отчет подан и верифицирован - вернется место в рейтинге:
        {"place": int}
        """
        detachment = self.request.user.detachment_commander
        report = Q20Report.objects.filter(
            detachment=detachment,
            competition_id=competition_pk
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ranking = getattr(
            detachment, 'q20ranking'
        ).filter(competition_id=competition_pk).first()
        if ranking:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )
        tandem_ranking = getattr(
            detachment, 'q20tandemranking_main_detachment'
        ).filter(competition_id=competition_pk).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        tandem_ranking = getattr(
            detachment, 'q20tandemranking_junior_detachment'
        ).filter(competition_id=competition_pk).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_200_OK
        )

    def create(self, request, competition_pk, *args, **kwargs):
        """
        Action для создания отчета по параметру 20
        для текущего пользователя.

        Доступ: командиры отрядов-участников конкурса.
        """
        competition = get_object_or_404(
            Competitions, id=competition_pk
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer = Q20ReportSerializer(data=request.data,
                                         context={'request': request,
                                                  'competition': competition,
                                                  'detachment': detachment})
        serializer.is_valid(raise_exception=True)
        serializer.save(competition=competition, detachment=detachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_place_q1(request, competition_pk):
    """Вью для показателя 'Численность членов линейного студенческого
    отряда в соответствии с объемом уплаченных членских взносов'.

    Место в рейтинге автоматически рассчитается 15 апреля 2024 года,
    до этого дня для участников будет выводится ошибка 400
    {'error': 'Рейтинг еще не сформирован'}.

    После 15 апреля, при запросе участником мероприятия будет
    возвращаться место в формате {'place': int}

    Для тандем заявки место для обоих участников будет одинаковым.

    Доступ: все авторизованные пользователи.
    Если пользователь не командир, либо не участвует в мероприятии -
    выводится ошибка 404.
    """
    detachment_start = get_detachment_start(
        request.user, competition_pk
    )
    if detachment_start is None:
        detachment_tandem = get_detachment_tandem(
            request.user, competition_pk
        )
        # Если командир, но не участник старт и не участник тандем
        if detachment_tandem is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ranking_tandem = Q1TandemRanking.objects.filter(
            Q(competition_id=competition_pk) &
            Q(junior_detachment=detachment_tandem) |
            Q(detachment=detachment_tandem)
        ).first()
        if ranking_tandem:
            return Response({'place': ranking_tandem.place})
        return Response({'error': 'Рейтинг еще не сформирован'},
                        status=status.HTTP_400_BAD_REQUEST)

    if detachment_start:
        ranking_start = Q1Ranking.objects.filter(
            competition_id=competition_pk,
            detachment=detachment_start
        ).first()
        if ranking_start:
            return Response({'place': ranking_start.place})

    # Если отряд является участником конкурса, но нет рейтинга
    return Response({'error': 'Рейтинг еще не сформирован'},
                    status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_place_q3(request, competition_pk=None):
    """
    Action для получения рейтинга по данному показателю.

    Возвращает место в формате {'place': int}

    Для тандем заявки место для обоих участников будет одинаковым.

    Доступ: все авторизованные пользователи.
    Если пользователь не командир, либо не участвует в мероприятии -
    выводится ошибка 404.
    """
    detachment = get_object_or_404(Detachment, commander=request.user)
    competition = get_object_or_404(Competitions, pk=competition_pk)
    tandem_ranking = Q3TandemRanking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if not tandem_ranking:
        tandem_ranking = Q3TandemRanking.objects.filter(
            junior_detachment=detachment,
            competition=competition
        ).first()

    if tandem_ranking and tandem_ranking.place is not None:
        return Response(
            {"place": tandem_ranking.place},
            status=status.HTTP_200_OK
        )
    elif tandem_ranking:
        return Response(
            {"error": "Рейтинг еще не сформирован"},
            status=status.HTTP_404_NOT_FOUND
        )
    ranking = Q3Ranking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if ranking and ranking.place is not None:
        return Response(
            {"place": ranking.place}, status=status.HTTP_200_OK
        )

    return Response(
        {"place": "Рейтинг еще не сформирован"},
        status=status.HTTP_404_NOT_FOUND
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_place_q4(request, competition_pk=None):
    """
    Action для получения рейтинга по данному показателю.

    Возвращает место в формате {'place': int}

    Для тандем заявки место для обоих участников будет одинаковым.

    Доступ: все авторизованные пользователи.
    Если пользователь не командир, либо не участвует в мероприятии -
    выводится ошибка 404.
    """
    detachment = get_object_or_404(Detachment, commander=request.user)
    competition = get_object_or_404(Competitions, pk=competition_pk)
    tandem_ranking = Q4TandemRanking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if not tandem_ranking:
        tandem_ranking = Q4TandemRanking.objects.filter(
            junior_detachment=detachment,
            competition=competition
        ).first()

    if tandem_ranking and tandem_ranking.place is not None:
        return Response(
            {"place": tandem_ranking.place},
            status=status.HTTP_200_OK
        )
    elif tandem_ranking:
        return Response(
            {"error": "Рейтинг еще не сформирован"},
            status=status.HTTP_404_NOT_FOUND
        )
    ranking = Q4Ranking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if ranking and ranking.place is not None:
        return Response(
            {"place": ranking.place}, status=status.HTTP_200_OK
        )

    return Response(
        {"place": "Рейтинг еще не сформирован"},
        status=status.HTTP_404_NOT_FOUND
    )


class Q16ViewSet(CreateListRetrieveUpdateViewSet):
    """Вьюсет для показателя 'Активность отряда в социальных сетях.'.

    Доступ:
        - чтение: Командир отряда из инстанса объекта к которому
                  нужен доступ, а также комиссары региональных штабов.
        - чтение(list): только комиссары региональных штабов.
                        Выводятся заявки только его рег штаба.
        - изменение: Если заявка не подтверждена - командир отряда из
                     инстанса объекта который изменяют,
                     а также комиссары региональных штабов.
                     Если подтверждена - только комиссар регионального штаба.
    """
    queryset = Q16Report.objects.all()
    serializer_class = Q16ReportSerializer
    permission_classes = (
        permissions.IsAuthenticated,
        IsCommanderDetachmentInParameterOrRegionalCommissioner
    )

    def get_queryset(self):
        if self.action == 'list':
            regional_headquarter = (
                self.request.user.userregionalheadquarterposition.headquarter
            )
            return Q16Report.objects.filter(
                detachment__regional_headquarter=regional_headquarter,
                competition_id=self.kwargs.get('competition_pk')
            )
        if self.action == 'me':
            return Q16Report.objects.filter(
                detachment__commander=self.request.user,
                competition_id=self.kwargs.get('competition_pk')
            )
        return Q16Report.objects.filter(
            competition_id=self.kwargs.get('competition_pk')
        )

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(),
                    IsCommanderAndCompetitionParticipant()]
        if self.action == 'list':
            return [permissions.IsAuthenticated(), IsRegionalCommissioner()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(),
                    IsRegionalCommissionerOrCommanderDetachmentWithVerif()]
        return super().get_permissions()

    def get_competitions(self):
        return get_object_or_404(
            Competitions, id=self.kwargs.get('competition_pk')
        )

    def get_detachment(self, obj):
        return obj.detachment

    @action(detail=False,
            methods=['get'],
            url_path='me',
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, competition_pk, *args, **kwargs):
        """
        Action для получения своего отчета по параметру 16
        для текущего пользователя.

        Доступ: все авторизованные пользователи.
        Если пользователь не командир отряда, или у его отряда нет
        поданного отчета - вернется пустой список.
        """
        return super().list(request, *args, **kwargs)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='accept',
            permission_classes=(permissions.IsAuthenticated,
                                IsRegionalCommissioner,))
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, ),
        responses={200: Q16ReportSerializer}
    )
    def accept_report(self, request, competition_pk, pk, *args, **kwargs):
        """
        Action для верификации отчета рег. комиссаром.

        Принимает пустой POST запрос.
        Доступ: комиссары региональных штабов.
        """
        report = self.get_object()
        if report.is_verified:
            return Response({'error': 'Отчет уже подтвержден.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            report.is_verified = True
            report.save()
            return Response(Q16ReportSerializer(report).data,
                            status=status.HTTP_200_OK)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            url_path='get-place',
            permission_classes=(permissions.IsAuthenticated,
                                IsCompetitionParticipantAndCommander))
    def get_place(self, request, competition_pk, **kwargs):
        """
        Action для получения рейтинга по данному показателю.

        Доступ: командиры отрядов, которые участвуют в конкурсе.
        Если отчета еще не подан, вернется ошибка 404. (данные не отправлены)
        Если отчет подан, но еще не верифицировн - вернется
        {"place": "Показатель в обработке"}.
        Если отчет подан и верифицирован - вернется место в рейтинге:
        {"place": int}
        """
        detachment = self.request.user.detachment_commander
        report = Q16Report.objects.filter(
            detachment=detachment,
            competition_id=competition_pk
        ).first()
        if not report:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ranking = getattr(
            detachment, 'q16ranking'
        ).filter(competition_id=competition_pk).first()
        if ranking:
            return Response(
                {"place": ranking.place}, status=status.HTTP_200_OK
            )
        tandem_ranking = getattr(
            detachment, 'q16tandemranking_main_detachment'
        ).filter(competition_id=competition_pk).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        tandem_ranking = getattr(
            detachment, 'q16tandemranking_junior_detachment'
        ).filter(competition_id=competition_pk).first()
        if tandem_ranking:
            return Response(
                {"place": tandem_ranking.place},
                status=status.HTTP_200_OK
            )
        return Response(
            {"place": "Показатель в обработке"},
            status=status.HTTP_200_OK
        )

    def create(self, request, competition_pk, *args, **kwargs):
        """
        Action для создания отчета по параметру 16
        для текущего пользователя.

        Доступ: командиры отрядов-участников конкурса.
        """
        competition = get_object_or_404(
            Competitions, id=competition_pk
        )
        detachment = get_object_or_404(
            Detachment, id=self.request.user.detachment_commander.id
        )
        serializer = Q16ReportSerializer(data=request.data,
                                         context={'request': request,
                                                  'competition': competition,
                                                  'detachment': detachment})
        serializer.is_valid(raise_exception=True)
        serializer.save(competition=competition, detachment=detachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_place_overall(request, competition_pk=None):
    """
    Получение общего места.

    Возвращает финальное место и сумму всех мест в формате

    ```
    {'place': 10, 'places_sum': 547}
    ```

    Для тандем заявки место для обоих участников будет одинаковым.

    Доступ: все авторизованные пользователи.
    Если пользователь не командир, либо не участвует в мероприятии -
    выводится ошибка 404.
    """
    detachment = get_object_or_404(Detachment, commander=request.user)
    competition = get_object_or_404(Competitions, pk=competition_pk)
    tandem_ranking = OverallTandemRanking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if not tandem_ranking:
        tandem_ranking = OverallTandemRanking.objects.filter(
            junior_detachment=detachment,
            competition=competition
        ).first()

    if tandem_ranking and tandem_ranking.place is not None:
        return Response(
            {"place": tandem_ranking.place},
            status=status.HTTP_200_OK
        )
    elif tandem_ranking:
        return Response(
            {"error": "Рейтинг еще не сформирован"},
            status=status.HTTP_404_NOT_FOUND
        )
    ranking = OverallRanking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if ranking and ranking.place is not None:
        return Response(
            {"place": ranking.place}, status=status.HTTP_200_OK
        )

    return Response(
        {"place": "Рейтинг еще не сформирован"},
        status=status.HTTP_404_NOT_FOUND
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_detachment_place(request, detachment_pk=None, competition_pk=None):
    detachment = get_object_or_404(Detachment, pk=detachment_pk)
    competition = get_object_or_404(Competitions, pk=competition_pk)
    tandem_ranking = OverallTandemRanking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if not tandem_ranking:
        tandem_ranking = OverallTandemRanking.objects.filter(
            junior_detachment=detachment,
            competition=competition
        ).first()

    if tandem_ranking and tandem_ranking.place is not None:
        return Response(
            {"place": tandem_ranking.place},
            status=status.HTTP_200_OK
        )
    elif tandem_ranking:
        return Response(
            {"error": "Рейтинг еще не сформирован"},
            status=status.HTTP_404_NOT_FOUND
        )
    ranking = OverallRanking.objects.filter(
        detachment=detachment,
        competition=competition
    ).first()
    if ranking and ranking.place is not None:
        return Response(
            {"place": ranking.place}, status=status.HTTP_200_OK
        )

    return Response(
        {"place": "Рейтинг еще не сформирован"},
        status=status.HTTP_404_NOT_FOUND
    )
