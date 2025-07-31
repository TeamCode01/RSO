import json

from django.conf import settings
from django.db import transaction
from django.db.models import Value, IntegerField, Max, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

import pandas as pd
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, status
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser


from api.mixins import SendMixin
from api.utils import get_calculation
from headquarters.serializers import ShortRegionalHeadquarterSerializer
from headquarters.models import (CentralHeadquarter, RegionalHeadquarter,
                                 UserDistrictHeadquarterPosition, DistrictHeadquarter)
from regional_competitions.constants import (R6_DATA, R7_DATA, R9_EVENTS_NAMES, 
                                             EMAIL_REPORT_DECLINED_MESSAGE)
from regional_competitions.factories import RViewSetFactory
from regional_competitions.filters import StatisticalRegionalReportFilter
from regional_competitions.mixins import (FormDataNestedFileParser, RegionalRMeMixin, 
                                          RegionalRMixin, ListRetrieveCreateMixin, DownloadReportXlsxMixin)
from regional_competitions.models import (CHqRejectingLog, DumpStatisticalRegionalReport, ExpertRole, Ranking,
                                          RegionalR1, RegionalR15, RegionalR18, RegionalR2,
                                          RegionalR4, RegionalR5, RegionalR11,
                                          RegionalR12, RegionalR13,
                                          RegionalR16, RegionalR17,
                                          RegionalR19, RegionalR101,
                                          RegionalR102, RVerificationLog, RegionalR8,
                                          StatisticalRegionalReport,
                                          r6_models_factory,
                                          r9_models_factory, REPORTS_IS_SENT_MODELS)
from regional_competitions.permissions import (IsCentralHeadquarterExpert, IsCentralOrDistrictHeadquarterExpert, IsDistrictHeadquarterExpert,
                                               IsRegionalCommander, IsRegionalCommanderAuthorOrCentralHeadquarterExpert)
from regional_competitions.serializers import (
    DumpStatisticalRegionalReportSerializer, EventNameSerializer, FileUploadSerializer, MassSendSerializer, RankingSerializer, RegionalR15Serializer, RegionalR18Serializer,
    RegionalR1Serializer, RegionalR2Serializer, RegionalR4Serializer, RegionalR5Serializer,
    RegionalR11Serializer, RegionalR12Serializer, RegionalR13Serializer,
    RegionalR16Serializer, RegionalR17Serializer, RegionalR19Serializer,
    RegionalR101Serializer, RegionalR102Serializer,
    StatisticalRegionalReportSerializer, r6_serializers_factory,
    r9_serializers_factory)
from regional_competitions.tasks import send_email_report_part_1, send_mail
from regional_competitions.utils import (
    get_all_reports_from_competition, get_report_number_by_class_name, get_reports_from_mass_competitions, swagger_schema_for_central_review,
    swagger_schema_for_create_and_update_methods,
    swagger_schema_for_district_review, swagger_schema_for_retrieve_method, get_emails)


class StatisticalRegionalViewSet(ListRetrieveCreateMixin):
    """Отчет 1 ч.

    Фильтрация:
        - district_id: поиск по id окружного штаба
        - district_name: поиск по названию окружного штаба, полное совпадение
        - regional_headquarter_name: поиск по названию регионального штаба, частичное совпадение
    Сортировка:
        - доступные поля для сортировки:
            - regional_headquarter_name: сортировка по названию регионального штаба
          Можно сортировать в обратном порядке добавив признак '-' перед названием поля
    """
    queryset = StatisticalRegionalReport.objects.all().select_related(
        'regional_headquarter'
    ).prefetch_related('additional_statistics')
    serializer_class = StatisticalRegionalReportSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = StatisticalRegionalReportFilter
    ordering_fields = ('regional_headquarter__name',)

    def get_permissions(self):
        if self.action == 'retrieve':
            return (IsRegionalCommanderAuthorOrCentralHeadquarterExpert(),)
        if self.action == 'list':
            return (IsCentralHeadquarterExpert(),)
        return permissions.IsAuthenticated(), IsRegionalCommander()

    @action(
        detail=False,
        methods=['GET', 'PUT'],
        url_path='me',
    )
    def my_statistical_report(self, request, pk=None):
        """Эндпоинт для получения своего первого отчета во 2-й части."""
        regional_headquarter = get_object_or_404(RegionalHeadquarter, commander=self.request.user)
        statistical_report = get_object_or_404(StatisticalRegionalReport, regional_headquarter=regional_headquarter)

        if request.method == "GET":
            return Response(
                data=self.get_serializer(statistical_report).data,
                status=status.HTTP_200_OK
            )

        # если put и нет дампа, то сначала сохраняем текущую версию в модель дампа
        if not DumpStatisticalRegionalReport.objects.filter(regional_headquarter=regional_headquarter).exists():
            serializer = DumpStatisticalRegionalReportSerializer(
                data=StatisticalRegionalReportSerializer(statistical_report).data)
            serializer.is_valid(raise_exception=True)
            serializer.save(regional_headquarter=regional_headquarter)

        serializer = self.get_serializer(
            statistical_report,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['GET'],
        url_path='me_first',
    )
    def me_first(self, request, pk=None):
        """Эндпоинт для получения своего первого отчета в 1-й части."""
        regional_headquarter = get_object_or_404(RegionalHeadquarter, commander=self.request.user)
        if DumpStatisticalRegionalReport.objects.filter(regional_headquarter=regional_headquarter).exists():
            statistical_report = DumpStatisticalRegionalReport.objects.get(regional_headquarter=regional_headquarter)
            return Response(
                data=DumpStatisticalRegionalReportSerializer(statistical_report).data,
                status=status.HTTP_200_OK
            )
        statistical_report = get_object_or_404(StatisticalRegionalReport, regional_headquarter=regional_headquarter)
        return Response(
            data=self.get_serializer(statistical_report).data,
            status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=['GET'],
        url_path=r'old_first/(?P<pk>\d+)',
        permission_classes=(IsRegionalCommanderAuthorOrCentralHeadquarterExpert(),),
    )
    def old_first(self, request, pk):
        """Эндпоинт для получения отчета 1-й части, версии до редактирования во 2-й части.

        Параметр пути id - pk регионального штаба.
        Доступ: автор отчета или эксперт ЦШ.
        """
        regional_headquarter = get_object_or_404(RegionalHeadquarter, pk=pk)
        if DumpStatisticalRegionalReport.objects.filter(regional_headquarter=regional_headquarter).exists():
            statistical_report = DumpStatisticalRegionalReport.objects.get(regional_headquarter=regional_headquarter)
            return Response(
                data=DumpStatisticalRegionalReportSerializer(statistical_report).data,
                status=status.HTTP_200_OK
            )
        statistical_report = get_object_or_404(StatisticalRegionalReport, regional_headquarter=regional_headquarter)
        return Response(
            data=self.get_serializer(statistical_report).data,
            status=status.HTTP_200_OK
        )

    def perform_create(self, serializer):
        user = self.request.user
        regional_headquarter = RegionalHeadquarter.objects.get(commander=user)

        should_send = True
        if StatisticalRegionalReport.objects.filter(regional_headquarter=regional_headquarter).exists():
            should_send = False

        report = serializer.save(regional_headquarter=regional_headquarter)
        if should_send:
            send_email_report_part_1.delay(report.id)


class BaseRegionalRViewSet(RegionalRMixin):
    """Базовый класс для вьюсетов шаблона RegionalR<int>ViewSet."""
    serializer_class = None
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.DEBUG:
            self.district_review = swagger_schema_for_district_review(self.serializer_class)(self.district_review)
            self.central_review = swagger_schema_for_central_review(self.serializer_class)(self.central_review)
            self.create = swagger_schema_for_create_and_update_methods(self.serializer_class)(self.create)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'action': self.action})
        if self.action == 'create':
            context.update(
                {
                    'regional_hq': RegionalHeadquarter.objects.get(commander=self.request.user),
                }
            )
        return context

    @action(
        methods=['PUT'],
        detail=True,
        url_path='district_review',
        permission_classes=(IsDistrictHeadquarterExpert,),
    )
    def district_review(self, request, pk=None):
        """Верифицирует отчет РШ Окружным Штабом.

        В теле запроса можно передать:
        - `action`: с любым значением. Необязательное поле, указывающее на то, что Окружной Штаб верифицирует отчет
          без изменений. В таком случае нет необходимости передавать остальные поля отчета.
        - Стандартные поля отчета - будут использоваться для обновления отчета при отсутствии поля `action`.

        Возвращает ошибку HTTP 400 Bad Request в случаях:
        - Если отчет еще не был отправлен на верификацию - `Отчет еще не был отправлен на верификацию`.
        - Если отчет уже был верифицирован Окружным Штабом - `Отчет уже верифицирован Окружным Штабом`.

        Доступ: эксперт ОШ.
        """
        parser = FormDataNestedFileParser()
        data = parser.parse_querydict(request.data)
        verification_action = data.pop('action', None)
        report = self.get_object()

        if not report.is_sent:
            return Response({
                'non_field_errors': 'Отчет еще не был отправлен на верификацию'
            }, status=status.HTTP_400_BAD_REQUEST)
        if report.verified_by_dhq:
            return Response({
                'non_field_errors': 'Отчет уже верифицирован Окружным Штабом'
            }, status=status.HTTP_400_BAD_REQUEST)

        initial_serializer = self.get_serializer(report)
        serialized_data = initial_serializer.data
        for key in ('regional_version', 'district_version', 'central_version'):
            serialized_data.pop(key, None)
        serialized_json = json.dumps(serialized_data, ensure_ascii=False, default=str)

        user = request.user
        try:
            district_headquarter = UserDistrictHeadquarterPosition.objects.get(user=request.user).headquarter
        except UserDistrictHeadquarterPosition.DoesNotExist:
            try:
                district_headquarter = DistrictHeadquarter.objects.get(commander=user)
            except:
                district_headquarter = None

        if not verification_action:
            update_serializer = self.get_serializer(report, data=data)

            if update_serializer.is_valid():
                update_serializer.save()

        RVerificationLog.objects.create(
            user=user,
            district_headquarter=district_headquarter,
            regional_headquarter=report.regional_headquarter,
            is_regional_data=True,
            report_id=report.id,
            report_number=self.get_report_number(),
            data=serialized_json
        )

        report.verified_by_dhq = True
        report.save()
        return Response({
            'detail': 'Отчет успешно верифицирован и/или отредактирован'
        }, status=status.HTTP_200_OK)

    @action(
        methods=['PUT', 'DELETE'],
        detail=True,
        url_path='central_review',
        permission_classes=(IsCentralHeadquarterExpert,),
    )
    def central_review(self, request, pk=None):
        """Обрабатывает верификацию или отклонение отчета Центральным Штабом.

        Метод поддерживает обработку запросов PUT и DELETE.
        - PUT для верификации отчета.
        - DELETE для отклонения отчета с указанием причин.

        В теле запроса необходимо передать:
        - `action`: с любым значением. Необязательное поле, указывающее на то, что Центральный Штаб верифицирует отчет
           без изменений. В таком случае нет необходимости передавать остальные поля отчета.
        - Стандартные поля отчета - будут использоваться для обновления отчета при отсутствии поля `action`.
        - `reasons`: словарь, обязательное поле для DELETE, содержащий причины отклонения, где ключи
           соответствуют полям отчета, а значения являются строками.

        При успешной обработке возвращает:
        - `HTTP 200 OK` для PUT.
        - `HTTP 204 No Content` для DELETE.

        Возвращает ошибку `HTTP 400 Bad Request` в случаях:
        - Если отчет еще не был отправлен на верификацию или не был проверен Окружным Штабом -
          `Отчет еще не был отправлен на верификацию или не был проверен Окружным Штабом`.
        - Если отчет уже был рассмотрен Центральным Штабом - `Отчет рассмотрен Центральным Штабом`.
        - Если для DELETE не указаны причины отклонения - `Необходимо указать причины отклонения отчета.`.
        - Если ключи в `reasons` не соответствуют полям отчета или значения не являются строками.

        Доступ: эксперт ЦШ или командир ЦШ.
        """
        parser = FormDataNestedFileParser()
        data = parser.parse_querydict(request.data)
        verification_action = data.pop('action', None)
        reasons = data.pop('reasons', {})
        report = self.get_object()

        if not report.is_sent or not report.verified_by_dhq:
            return Response({
                'non_field_errors': 'Отчет еще не был отправлен на верификацию или не был проверен Окружным Штабом'
            }, status=status.HTTP_400_BAD_REQUEST)
        if report.verified_by_chq in (True, False):
            return Response({
                'non_field_errors': 'Отчет рассмотрен Центральным Штабом'
            }, status=status.HTTP_400_BAD_REQUEST)

        initial_serializer = self.get_serializer(report)
        serialized_data = initial_serializer.data
        for key in ('regional_version', 'district_version', 'central_version'):
            serialized_data.pop(key, None)
        serialized_json = json.dumps(serialized_data, ensure_ascii=False, default=str)

        user = request.user

        # Определяем наличие лога от РШ за этот отчет (что будет означать, что была проверка от ОШ)
        last_regional_log = RVerificationLog.objects.filter(
            regional_headquarter=report.regional_headquarter,
            is_regional_data=True,
            report_number=self.get_report_number(),
            report_id=report.id
        ).last()

        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get('pk')
        objects = queryset.filter(regional_headquarter_id=pk)

        if not last_regional_log:
            # если проверки нет, значит это итерация после отклонения со стороны ЦШ
            is_central_data, is_district_data, is_regional_data = False, False, True
            if objects.count() == 1:
                is_district_data = True
        else:
            # если проверка есть, значит данные в отчете надо перенести в district_version
            is_central_data, is_district_data, is_regional_data = False, True, False

        if not verification_action:
            update_serializer = self.get_serializer(report, data=data)
            if update_serializer.is_valid():
                update_serializer.save()

        if request.method == 'PUT':

            report.verified_by_chq = True
            with transaction.atomic():
                report.save()

                # Вызываем функцию подсчета очков
                get_calculation(report=report, report_number=self.get_report_number())

            RVerificationLog.objects.create(
                user=user,
                central_headquarter=CentralHeadquarter.objects.first(),
                regional_headquarter=report.regional_headquarter,
                is_regional_data=is_regional_data,
                is_district_data=is_district_data,
                is_central_data=is_central_data,
                report_id=report.id,
                report_number=self.get_report_number(),
                data=serialized_json
            )

            return Response({
                'detail': 'Отчет успешно верифицирован и/или отредактирован'
            }, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if not reasons:
                return Response({
                    'reasons': 'Необходимо указать причины отклонения отчета.'
                }, status=status.HTTP_400_BAD_REQUEST)

            valid_keys = set(self.get_serializer().get_fields().keys())
            reasons_keys = set(reasons.keys())

            if not reasons_keys.issubset(valid_keys):
                return Response({
                    'non_field_errors': 'Ключи причин отклонения должны соответствовать полям сериализатора'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not all(isinstance(value, str) for value in reasons.values()):
                return Response({
                    'non_field_errors': 'Все значения причин отклонения должны быть строками'
                }, status=status.HTTP_400_BAD_REQUEST)

            report.verified_by_chq = False
            report.save()

            RVerificationLog.objects.create(
                user=user,
                central_headquarter=CentralHeadquarter.objects.first(),
                regional_headquarter=report.regional_headquarter,
                is_regional_data=is_regional_data,
                is_district_data=is_district_data,
                is_central_data=is_central_data,
                report_id=report.id,
                report_number=self.get_report_number(),
                data=serialized_json
            )
            CHqRejectingLog.objects.create(
                user=user,
                regional_headquarter=report.regional_headquarter,
                report_number=self.get_report_number(),
                report_id=report.id,
                reasons=json.dumps(reasons, ensure_ascii=False)
            )

            # Отправляем email сообщение о необходимости внести изменения в отчет
            send_mail.delay(
                subject='Конкурсная комиссия Центрального штаба РСО внесла комментарии '
                        'по 2 части отчета за 2024 год. Необходимо внести корректировки.',
                message=EMAIL_REPORT_DECLINED_MESSAGE,
                recipients=get_emails(report),
                file_path=''
            )

            return Response({
                'detail': 'Отчет успешно отклонен с указанием причин'
            }, status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['GET',],
        url_path='download_all_reports_data',
    )
    def download_all_reports_data(self, request, pk=None):
        """Скачивание данных отчета в формате XLSX."""
        return get_all_reports_from_competition(self.get_report_number())

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated,])
def download_mass_reports_xlsx(_, pk):
    """Скачивание заполненных массовых отчетов конкурса РО (6, 9, 10) в одном xlsx файле.

    Доступно только авторизованному пользователю.
    pk - первая цифра номера показателя(указываем только 6, 9 или 10).
    """
    return get_reports_from_mass_competitions(main_report_number=pk)


class RegionalRNoVerifViewSet(RegionalRMixin):
    """
    Базовый класс для вьюсетов шаблона RegionalR<int>ViewSet,
    которые не требуют верификации.
    """
    model = None
    serializer_class = None
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create':
            context.update(
                {
                    'regional_hq': RegionalHeadquarter.objects.get(commander=self.request.user),
                    'action': self.action
                }
            )
        return context


class BaseRegionalRMeViewSet(RegionalRMeMixin):
    """Базовый класс для вьюсетов шаблона RegionalR<int>MeViewSet."""
    model = None
    serializer_class = None
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.DEBUG:
            self.retrieve = swagger_schema_for_retrieve_method(self.serializer_class)(self.retrieve)
            self.update = swagger_schema_for_create_and_update_methods(self.serializer_class)(self.update)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(
            {
                'regional_hq': RegionalHeadquarter.objects.get(commander=self.request.user),
                'action': self.action
            }
        )
        return context

    def get_object(self):
        regional_headquarter = get_object_or_404(
            RegionalHeadquarter,
            commander=self.request.user
        )
        report = self.model.objects.filter(regional_headquarter=regional_headquarter).last()
        if report is None:
            raise Http404('Отчет по данному показателю не найден')
        return report

    def update(self, *args, **kwargs):
        """Редактирует актуальную версию отчета для командира регионального штаба.

        Метод идемпотентен. Поддерживается динамическое обновление
        """
        serializer = self.get_serializer(
            self.get_object(), data=self.request.data, partial=kwargs.get('partial', False)
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Возвращает актуальную версию отчета для командира регионального штаба.

        Ответ, включает в себя версии отчета и возможные причины его отклонения:

        - `regional_version`: Данные последней версии отчета, отправленного региональным штабом.
        - `district_version`: Данные последней версии отчета, отправленные (измененные) окружным штабом.
        - `central_version`: Данные последней версии отчета, отправленные (измененные) центральным штабом.
        - `rejecting_reasons`: Причины отклонения отчета центральным штабом, если таковые имеются.

        Возвращает:
        - 200 OK и данные отчета в случае успеха.
        - 404 Not Found, если отчет не найден.
        """
        return Response(self.get_serializer(self.get_object()).data)

    def perform_create(self, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))

    def get_report_number(self):
        return get_report_number_by_class_name(self)


class MassSendViewSet(GenericViewSet):
    serializer_class = MassSendSerializer

    def send_reports(self, request, factory):
        current_regional_headquarter = get_object_or_404(RegionalHeadquarter, commander=request.user)
        models = factory.models
        events_to_update = []
        for name, model in models.items():
            if name[-4:] == 'Link':
                continue
            event_obj = model.objects.filter(
                regional_headquarter=current_regional_headquarter, is_sent=False
            ).last()
            if event_obj:
                events_to_update.append(event_obj)
        if events_to_update:
            try:
                with transaction.atomic():
                    for event_obj in events_to_update:
                        event_obj.is_sent = True
                        event_obj.save()
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
                {'detail': 'Данные отправлены на верификацию окружному штабу'},
                status=status.HTTP_200_OK
            )

    @action(
        detail=False,
        methods=['POST'],
        url_path='6/send',
    )
    def r6_mass_send_for_verification(self, request):
        """Отправляет все отчеты по 6 показателю на верификацию.

        Метод идемпотентен. В случае успешной отправки возвращает `HTTP 200 OK`.
        """
        return self.send_reports(request, r6_models_factory)

    # @action(
    #     detail=False,
    #     methods=['POST'],
    #     url_path='7/send',
    # )
    # def r7_mass_send_for_verification(self, request):
    #     """Отправляет все отчеты по 7 показателю на верификацию.
    #
    #     Метод идемпотентен. В случае успешной отправки возвращает `HTTP 200 OK`.
    #     """
    #     return self.send_reports(request, r7_models_factory)

    @action(
        detail=False,
        methods=['POST'],
        url_path='9/send',
    )
    def r9_mass_send_for_verification(self, request):
        """Отправляет отчеты по 9 показателю на верификацию.

        Метод идемпотентен. В случае успешной отправки возвращает `HTTP 200 OK`.
        """
        return self.send_reports(request, r9_models_factory)


class RegionalEventNamesRViewSet(GenericViewSet):
    """
    Вьюсет для получения списка названий событий по показателям.

    Доступ: все пользователи.
    """
    serializer_class = EventNameSerializer

    @action(
        detail=False,
        methods=['GET'],
        url_path='r6-event-names',
    )
    def get_event_names_r6(self, request):
        event_data = [
            {
                'id': list(tup[0].keys())[0],
                'name': list(tup[0].values())[0],
                'month': list(tup[1].values())[0],
                'city': list(tup[2].values())[0]
            } for tup in R6_DATA
        ]
        return Response(event_data)

    @action(
        detail=False,
        methods=['GET'],
        url_path='r7-event-names',
    )
    def get_event_names_r7(self, request):
        event_data = [
            {
                'id': list(tup[0].keys())[0],
                'name': list(tup[0].values())[0],
                'month': list(tup[1].values())[0],
                'city': list(tup[2].values())[0]
            } for tup in R7_DATA
        ]
        return Response(event_data)

    @action(
        detail=False,
        methods=['GET'],
        url_path='r9-event-names',
    )
    def get_event_names_r9(self, request):
        event_data = [{'id': id, 'name': name} for id, name in R9_EVENTS_NAMES.items()]
        return Response(event_data)


class BaseRegionalRAutoViewSet(DownloadReportXlsxMixin, GenericViewSet):
    """Базовый вьюсет для выгрузки автоматических отчетов."""


class RegionalR1ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR1.objects.all()
    serializer_class = RegionalR1Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR1MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR1
    queryset = RegionalR1.objects.all()
    serializer_class = RegionalR1Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)

class RegionalR2AutoViewSet(BaseRegionalRAutoViewSet):
    """Вьюсет для выгрузки автоматических отчетов по 2 показателю."""


class RegionalR3AutoViewSet(BaseRegionalRAutoViewSet):
    """Вьюсет для выгрузки автоматических отчетов по 3 показателю."""


class RegionalR4ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR4.objects.all()
    serializer_class = RegionalR4Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR4MeViewSet(FormDataNestedFileParser, SendMixin, BaseRegionalRMeViewSet):
    model = RegionalR4
    queryset = RegionalR4.objects.all()
    serializer_class = RegionalR4Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR5ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    """
    Организация всероссийских (международных) (организатор – региональное отделение РСО),
    окружных и межрегиональных трудовых проектов в соответствии с Положением об организации
    трудовых проектов РСО.

    Принимает JSON:
    ```{
    "comment": "комментарий согласующего",
    "events": [ - проекты передаются в списке
        {
        "participants_number": 10 - Общее количество участников,
        "start_date": "ГГГГ-ММ-ДД", - Дата начала проекта
        "end_date": "ГГГГ-ММ-ДД", - Дата окончания проекта
        "links": [
            {
            "link": "https://your.site.com", - URL-адрес
            }
        ],
        "ro_participants_number": 5 - Количество участников РО
        }
    ]
    }```
    """

    queryset = RegionalR5.objects.all()
    serializer_class = RegionalR5Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR5MeViewSet(FormDataNestedFileParser, SendMixin, BaseRegionalRMeViewSet):
    model = RegionalR5
    queryset = RegionalR5.objects.all()
    serializer_class = RegionalR5Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


r6_view_sets_factory = RViewSetFactory(
    models=r6_models_factory.models,
    serializers=r6_serializers_factory.serializers,
    base_r_view_set=BaseRegionalRViewSet,
    base_r_me_view_set=BaseRegionalRMeViewSet,
    additional_parental_class=FormDataNestedFileParser
)
r6_view_sets_factory.create_view_sets()


class RegionalR7AutoViewSet(BaseRegionalRAutoViewSet):
    """Вьюсет для выгрузки автоматических отчетов по 7 показателю."""

# r7_view_sets_factory = RViewSetFactory(
#     models=r7_models_factory.models,
#     serializers=r7_serializers_factory.serializers,
#     base_r_view_set=BaseRegionalRViewSet,
#     base_r_me_view_set=BaseRegionalRMeViewSet,
#     additional_parental_class=FormDataNestedFileParser
# )
# r7_view_sets_factory.create_view_sets()


class RegionalR8AutoViewSet(BaseRegionalRAutoViewSet):
    """Вьюсет для выгрузки автоматических отчетов по 8 показателю."""


r9_view_sets_factory = RViewSetFactory(
    models=r9_models_factory.models,
    serializers=r9_serializers_factory.serializers,
    base_r_view_set=BaseRegionalRViewSet,
    base_r_me_view_set=BaseRegionalRMeViewSet,
    additional_parental_class=FormDataNestedFileParser
)
r9_view_sets_factory.create_view_sets()


@swagger_auto_schema(method='POST', request_body=FileUploadSerializer)
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
@parser_classes([MultiPartParser, FormParser])
def upload_r8_data(request):
    """
    Метод для загрузки данных по 8 показателю.

    Требуется, чтобы в файле были три колонки:
        - 'Id' - ID рег штаба
        - 'место' - место в рейтинге

    Доступ: только администратор.

    Удаляет все предыдущие записи в модели и загружает новые из файла.
    """
    serializer = FileUploadSerializer(data=request.data)
    if serializer.is_valid():
        file = serializer.validated_data['file']
        hq_ids = set(RegionalHeadquarter.objects.values_list('id', flat=True))
        try:
            df = pd.read_excel(file)
            reports_to_create = []
            for index, row in df.iterrows():
                if row['Id'] not in hq_ids:
                    continue
                reports_to_create.append(
                    RegionalR8(
                        regional_headquarter_id=row['Id'],
                        score=row['место']
                    )
                )
            try:
                with transaction.atomic():
                    RegionalR8.objects.all().delete()
                    # не булком, т.к. в методе сейв модели создаются записи рейтинга.
                    for report in reports_to_create:
                        report.save()
            except Exception as e:
                return Response(
                    {'error': f'Ошибка при обработке файлов. {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST)

            return Response(status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Ошибка при чтении файла. {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegionalR101ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR101.objects.all()
    serializer_class = RegionalR101Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR101MeViewSet(FormDataNestedFileParser, SendMixin, BaseRegionalRMeViewSet):
    model = RegionalR101
    queryset = RegionalR101.objects.all()
    serializer_class = RegionalR101Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR102ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR102.objects.all()
    serializer_class = RegionalR102Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR102MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR102
    queryset = RegionalR102.objects.all()
    serializer_class = RegionalR102Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR11ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR11.objects.all()
    serializer_class = RegionalR11Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR11MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR11
    queryset = RegionalR11.objects.all()
    serializer_class = RegionalR11Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR12ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR12.objects.all()
    serializer_class = RegionalR12Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR12MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR12
    queryset = RegionalR12.objects.all()
    serializer_class = RegionalR12Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR13ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR13.objects.all()
    serializer_class = RegionalR13Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR13MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR13
    queryset = RegionalR13.objects.all()
    serializer_class = RegionalR13Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR14AutoViewSet(BaseRegionalRAutoViewSet):
    """Вьюсет для выгрузки автоматических отчетов по 14 показателю."""


class RegionalR15ViewSet(DownloadReportXlsxMixin, RetrieveModelMixin, GenericViewSet,):
    queryset = RegionalR15.objects.all()
    serializer_class = RegionalR15Serializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get('pk')
        objects = queryset.filter(regional_headquarter_id=pk)
        if objects.exists():
            latest_object = objects.order_by('-id')[0]
            return latest_object
        raise Http404("Страница не найдена")


class RegionalR16ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    queryset = RegionalR16.objects.all()
    serializer_class = RegionalR16Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR16MeViewSet(FormDataNestedFileParser, SendMixin, BaseRegionalRMeViewSet):
    model = RegionalR16
    queryset = RegionalR16.objects.all()
    serializer_class = RegionalR16Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR17ViewSet(FormDataNestedFileParser, RegionalRNoVerifViewSet):
    """Дислокация студенческих отрядов РО РСО.

    file_size выводится в мегабайтах.

    ```json
    {
    "scan_file": документ,
    "comment": строка
    }
    ```
    """

    queryset = RegionalR17.objects.all()
    serializer_class = RegionalR17Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR17MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet):
    model = RegionalR17
    queryset = RegionalR17.objects.all()
    serializer_class = RegionalR17Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR18ViewSet(FormDataNestedFileParser, RegionalRNoVerifViewSet):
    queryset = RegionalR18.objects.all()
    serializer_class = RegionalR18Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR18MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet):
    """Вьюсет для просмотра и редактирования отчета по 18 показателю.

    Показатель не требует верификации.
    Доступ - только региональным командирам.
    """
    model = RegionalR18
    queryset = RegionalR18.objects.all()
    serializer_class = RegionalR18Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)

    def retrieve(self, request, *args, **kwargs):
        """Просмотр отчета по 18 показателю.

        Доступ - только региональным командирам.
        """
        return super().retrieve(request, *args, **kwargs)


class RegionalR19ViewSet(RegionalRNoVerifViewSet):
    """Трудоустройство.

    employed_student_start - Фактическое количество трудоустроенных студентов в третий
    трудовой семестр
    employed_student_end - Фактическое количество трудоустроенных в штат принимающей
    организации по итогам третьего трудового семестра.

    ```json
    {
      "employed_student_start": 0,
      "employed_student_end": 0,
      "comment": "string"
    }
    ```
    """

    queryset = RegionalR19.objects.all()
    serializer_class = RegionalR19Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR19MeViewSet(BaseRegionalRMeViewSet):
    model = RegionalR19
    queryset = RegionalR19.objects.all()
    serializer_class = RegionalR19Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RankingViewSet(ListModelMixin, GenericViewSet):
    """
    - Поддерживается сортировка по всем полям `overall_place`, `k_place`,
      а также `rX_place` и `rX_score` для X от 1 до 16.
    - Алфавитная сортировка по названию регионального штаба (`regional_headquarter__name`).

    - **Параметры сортировки:**
      - `ordering`: определяет порядок сортировки.
        Примеры:
          - `?ordering=overall_place` - сортировка по итоговому месту (возрастание).
          - `?ordering=-overall_place` - сортировка по итоговому месту (убывание).
          - `?ordering=r1_place` - сортировка по месту по 1-му показателю.
          - `?ordering=-r1_score` - сортировка по очкам по 1-му показателю (убывание).
          - `?ordering=regional_headquarter__name` - алфавитная сортировка по названию штаба.

    - **Вывод по умолчанию:**
      - Сортировка по названию регионального штаба (`regional_headquarter__name`).
    """
    queryset = Ranking.objects.all().select_related('regional_headquarter')
    serializer_class = RankingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['overall_place', 'k_place'] + [
        f'r{i}_place' for i in range(1, 17)
    ] + [
        f'r{i}_score' for i in range(1, 17)
    ]
    ordering = ['regional_headquarter__name']

    def get_queryset(self):
        """
        Добавляет приоритетное значение для полей с `place`:
        1. Все значения > 0 идут первыми.
        2. Затем 0.
        3. Затем None.
        """
        qs = super().get_queryset()
        ordering = self.request.query_params.get('ordering', None)

        if ordering:
            field = ordering.lstrip('-')
            if field.endswith('_place') and field in self.ordering_fields:
                reverse = ordering.startswith('-')
                qs = qs.annotate(
                    sort_priority=Coalesce(field, Value(-1, output_field=IntegerField()))
                ).order_by(
                    f"{'-' if reverse else ''}sort_priority",
                    ordering
                )
        return qs


@api_view(['GET'])
@permission_classes((IsCentralOrDistrictHeadquarterExpert,))
def get_sent_reports(request):
    """
    Эндпоинт для получения списка рег штабов, которые отправили отчеты по 2 части.

    Доступ - только экспертам окружных и центрального штабов.

    Для экспертов окр штабов выводит список рег штабов, отчеты которых отправлены, но не верифицирован окр штабом.
    Для экспертов центрального штаба выводит список рег штабов, которые верифицированы окр штабом,
    но не верифицированы и не отклонены центральным штабом.

    Для окружных штабов выводит заявки только подвластных им рег штабов.
    """
    is_central_expert = ExpertRole.objects.filter(
        user=request.user, central_headquarter__isnull=False
    ).exists()

    def get_latest_regional_ids_from_model(model, filter_params):
        if not model:
            return set()

        latest_entries = model.objects.filter(
            regional_headquarter_id=OuterRef('regional_headquarter_id')
        ).order_by('-updated_at')

        return set(
            model.objects.filter(
                id=Subquery(latest_entries.values('id')[:1]),
                **filter_params
            ).values_list('regional_headquarter_id', flat=True)
        )

    if is_central_expert:
        # Для ЦШ: если штаб удовлетворяет условиям хотя бы в одной модели
        filter_params = {'verified_by_dhq': True, 'verified_by_chq': None}
        reg_ids = set()
        for model in REPORTS_IS_SENT_MODELS:
            model_reg_ids = get_latest_regional_ids_from_model(model, filter_params)
            reg_ids.update(model_reg_ids)
    else:
        # Для ОШ: если штаб удовлетворяет условиям хотя бы в одной модели
        district_headquarter_id = ExpertRole.objects.get(user=request.user).district_headquarter_id
        filter_params = {'is_sent': True, 'verified_by_dhq': False}
        reg_ids = set()
        for model in REPORTS_IS_SENT_MODELS:
            model_reg_ids = get_latest_regional_ids_from_model(model, filter_params)
            reg_ids.update(model_reg_ids)

    qs = RegionalHeadquarter.objects.filter(id__in=reg_ids)
    if not is_central_expert:
        qs = qs.filter(district_headquarter_id=district_headquarter_id)

    return Response(ShortRegionalHeadquarterSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes((permissions.IsAuthenticated,))
def user_info(request):
    """Информация о пользователе.

    Возвращает три ключа:
    - is_central_expert - является ли пользователь экспертом центрального штаба или командиром центрального штаба.
    - is_district_expert - является ли пользователь экспертом окружного штаба.
    - is_reg_commander - является ли пользователь командиром регионального штаба.

    Доступ: все аутентифицированные пользователи.
    """
    is_central_expert = ExpertRole.objects.filter(
        user=request.user, central_headquarter__isnull=False
    ).exists()
    is_district_expert = ExpertRole.objects.filter(
        user=request.user, district_headquarter__isnull=False
    ).exists()
    is_commander = RegionalHeadquarter.objects.filter(
        commander=request.user
    ).exists()
    return Response({
        'is_central_expert': is_central_expert,
        'is_district_expert': is_district_expert,
        'is_reg_commander': is_commander
    })
