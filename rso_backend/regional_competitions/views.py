import datetime
import json
import traceback
from contextlib import suppress

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from api.mixins import SendMixin
from headquarters.models import (CentralHeadquarter, RegionalHeadquarter,
                                 UserDistrictHeadquarterPosition)
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from django_celery_beat.models import PeriodicTask, IntervalSchedule

from api.utils import get_calculation
from regional_competitions.constants import R6_DATA, R7_DATA, R9_EVENTS_NAMES, EMAIL_REPORT_DECLINED_MESSAGE
from regional_competitions.factories import RViewSetFactory
from regional_competitions.mixins import RegionalRMeMixin, RegionalRMixin, RetrieveCreateMixin
from regional_competitions.models import (CHqRejectingLog, RegionalR1, RegionalR18,
                                          RegionalR4, RegionalR5, RegionalR11,
                                          RegionalR12, RegionalR13,
                                          RegionalR16, RegionalR17,
                                          RegionalR19, RegionalR101,
                                          RegionalR102, RVerificationLog,
                                          StatisticalRegionalReport,
                                          r6_models_factory,
                                          r7_models_factory, r9_models_factory)
from regional_competitions.permissions import IsRegionalCommander
from regional_competitions.serializers import (
    EventNameSerializer, MassSendSerializer, RegionalR18Serializer, 
    RegionalR1Serializer, RegionalR4Serializer, RegionalR5Serializer,
    RegionalR11Serializer, RegionalR12Serializer, RegionalR13Serializer,
    RegionalR16Serializer, RegionalR17Serializer, RegionalR19Serializer,
    RegionalR101Serializer, RegionalR102Serializer,
    StatisticalRegionalReportSerializer, r6_serializers_factory, r7_serializers_factory,
    r9_serializers_factory)
from regional_competitions.tasks import send_email_report_part_1, send_mail
from regional_competitions.utils import (
    get_report_number_by_class_name, get_report_xlsx, swagger_schema_for_central_review,
    swagger_schema_for_create_and_update_methods,
    swagger_schema_for_district_review, swagger_schema_for_retrieve_method, get_emails)
from django.conf import settings


class StatisticalRegionalViewSet(RetrieveCreateMixin):
    """Отчет 1 ч. Get принимает id РШ и возвращает его последний отчет, если существует."""
    queryset = StatisticalRegionalReport.objects.all()
    serializer_class = StatisticalRegionalReportSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            return (permissions.IsAuthenticated(),)
        return permissions.IsAuthenticated(), IsRegionalCommander()

    def retrieve(self, request, *args, **kwargs):
        regional_headquarter_id = kwargs.get('pk')
        statistical_report = StatisticalRegionalReport.objects.filter(
            regional_headquarter_id=regional_headquarter_id
        ).last()

        if not statistical_report:
            return Response(
                {"detail": "Отчет не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(statistical_report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['GET', 'PATCH'],
        url_path='me',
    )
    def my_statistical_report(self, request, pk=None):
        regional_headquarter = RegionalHeadquarter.objects.get(
            commander=self.request.user
        )
        statistical_report = get_object_or_404(StatisticalRegionalReport, regional_headquarter=regional_headquarter)
        if request.method == "GET":
            return Response(
                data=self.get_serializer(statistical_report).data,
                status=status.HTTP_200_OK
            )
        # TODO: Ограничение на изменение отчета (нельзя редактировать, если первый показатель отправлен is_sent=True)
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def perform_create(self, serializer):
        report = serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))
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

    def get_report_number(self):
        return get_report_number_by_class_name(self)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action not in ('district_review', 'central_review'):
            context.update(
                {
                    'regional_hq': RegionalHeadquarter.objects.get(commander=self.request.user),
                    'action': self.action
                }
            )
        return context

    def perform_create(self, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))

    def perform_update(self, request, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))

    @action(
        methods=['PATCH'],
        detail=True,
        url_path='district_review',
        permission_classes=(permissions.IsAuthenticated,),  # TODO: permission
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

        Доступ: TODO
        """
        verification_action = request.data.pop('action', None)
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
        district_headquarter = UserDistrictHeadquarterPosition.objects.get(user=request.user).headquarter

        if not verification_action:
            update_serializer = self.get_serializer(report, data=request.data, partial=True)

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
        methods=['PATCH', 'DELETE'],
        detail=True,
        url_path='central_review',
        permission_classes=(permissions.IsAuthenticated,),  # TODO: permission
    )
    def central_review(self, request, pk=None):
        """Обрабатывает верификацию или отклонение отчета Центральным Штабом.

        Метод поддерживает обработку запросов PATCH и DELETE.
        - PATCH для верификации отчета.
        - DELETE для отклонения отчета с указанием причин.

        В теле запроса необходимо передать:
        - `action`: с любым значением. Необязательное поле, указывающее на то, что Центральный Штаб верифицирует отчет
           без изменений. В таком случае нет необходимости передавать остальные поля отчета.
        - Стандартные поля отчета - будут использоваться для обновления отчета при отсутствии поля `action`.
        - `reasons`: словарь, обязательное поле для DELETE, содержащий причины отклонения, где ключи
           соответствуют полям отчета, а значения являются строками.

        При успешной обработке возвращает:
        - `HTTP 200 OK` для PATCH.
        - `HTTP 204 No Content` для DELETE.

        Возвращает ошибку `HTTP 400 Bad Request` в случаях:
        - Если отчет еще не был отправлен на верификацию или не был проверен Окружным Штабом -
          `Отчет еще не был отправлен на верификацию или не был проверен Окружным Штабом`.
        - Если отчет уже был рассмотрен Центральным Штабом - `Отчет рассмотрен Центральным Штабом`.
        - Если для DELETE не указаны причины отклонения - `Необходимо указать причины отклонения отчета.`.
        - Если ключи в `reasons` не соответствуют полям отчета или значения не являются строками.

        Доступ: TODO
        """
        verification_action = request.data.pop('action', None)
        reasons = request.data.pop('reasons', {})
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

        # Определяем последний тип лога для этого отчёта
        last_log = RVerificationLog.objects.filter(report_id=report.id).last()
        if not last_log:
            return Response({
                'non_field_errors': 'Не найдено исходное состояние отчета'
            }, status=status.HTTP_400_BAD_REQUEST)

        if last_log.is_regional_data:
            is_district_data, is_central_data = True, False
        elif last_log.is_district_data or last_log.is_central_data:
            is_central_data, is_district_data = True, False
        else:
            return Response({
                'non_field_errors': 'Некорректное исходное состояние отчета'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not verification_action:
            update_serializer = self.get_serializer(report, data=request.data, partial=True)
            if update_serializer.is_valid():
                update_serializer.save()

        if request.method == 'PATCH':

            report.verified_by_chq = True
            report.save()

            # Вызываем функцию подсчета очков
            get_calculation(report=report, report_number=self.get_report_number())

            RVerificationLog.objects.create(
                user=user,
                central_headquarter=CentralHeadquarter.objects.first(),
                regional_headquarter=report.regional_headquarter,
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
                is_district_data=is_district_data,
                is_central_data=is_central_data,
                report_id=report.id,
                report_number=self.get_report_number(),
                data=serialized_json
            )
            CHqRejectingLog.objects.create(
                user=user,
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


class RegionalRNoVerifViewSet(RegionalRMixin):
    """
    Базовый класс для вьюсетов шаблона RegionalR<int>ViewSet,
    которые не требуют верификации.
    """
    serializer_class = None
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)

    def get_report_number(self):
        return get_report_number_by_class_name(self)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(
            {
                'regional_hq': RegionalHeadquarter.objects.get(commander=self.request.user),
                # 'action': self.action
            }
        )
        return context

    def perform_create(self, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))

    def perform_update(self, request, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))


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

    @action(
        detail=True,
        methods=['GET',],
        url_path='download_report_data',
    )
    def download_report_data(self, request, pk=None):
        """Скачивание данных отчета в формате XLSX."""
        return get_report_xlsx(self)


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

    @action(
        detail=False,
        methods=['POST'],
        url_path='7/send',
    )
    def r7_mass_send_for_verification(self, request):
        """Отправляет все отчеты по 7 показателю на верификацию.

        Метод идемпотентен. В случае успешной отправки возвращает `HTTP 200 OK`.
        """
        return self.send_reports(request, r7_models_factory)

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
        event_data = [{'id': list(tup[0].keys())[0], 'name': list(tup[0].values())[0], 'month': list(tup[1].values())[0], 'city': list(tup[2].values())[0]} for tup in R6_DATA]
        return Response(event_data)

    @action(
        detail=False,
        methods=['GET'],
        url_path='r7-event-names',
    )
    def get_event_names_r7(self, request):
        event_data = [{'id': list(tup[0].keys())[0], 'name': list(tup[0].values())[0], 'month': list(tup[1].values())[0], 'city': list(tup[2].values())[0]} for tup in R7_DATA]
        return Response(event_data)

    @action(
        detail=False,
        methods=['GET'],
        url_path='r9-event-names',
    )
    def get_event_names_r9(self, request):
        event_data = [{'id': id, 'name': name} for id, name in R9_EVENTS_NAMES.items()]
        return Response(event_data)


class RegionalR1ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR1.objects.all()
    serializer_class = RegionalR1Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)
    parser_classes = (MultiPartParser, FormParser)


class RegionalR1MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR1
    queryset = RegionalR1.objects.all()
    serializer_class = RegionalR1Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR4ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR4.objects.all()
    serializer_class = RegionalR4Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR4MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR4
    queryset = RegionalR4.objects.all()
    serializer_class = RegionalR4Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR5ViewSet(BaseRegionalRViewSet):
    """
    Организация всероссийских (международных) (организатор – региональное отделение РСО),
    окружных и межрегиональных трудовых проектов в соответствии с Положением об организации
    трудовых проектов РСО.

    Принимает JSON:
    {
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
    }
    """

    queryset = RegionalR5.objects.all()
    serializer_class = RegionalR5Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR5MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR5
    queryset = RegionalR5.objects.all()
    serializer_class = RegionalR5Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


r6_view_sets_factory = RViewSetFactory(
    models=r6_models_factory.models,
    serializers=r6_serializers_factory.serializers,
    base_r_view_set=BaseRegionalRViewSet,
    base_r_me_view_set=BaseRegionalRMeViewSet,
)
r6_view_sets_factory.create_view_sets()


r7_view_sets_factory = RViewSetFactory(
    models=r7_models_factory.models,
    serializers=r7_serializers_factory.serializers,
    base_r_view_set=BaseRegionalRViewSet,
    base_r_me_view_set=BaseRegionalRMeViewSet,
)
r7_view_sets_factory.create_view_sets()

r9_view_sets_factory = RViewSetFactory(
    models=r9_models_factory.models,
    serializers=r9_serializers_factory.serializers,
    base_r_view_set=BaseRegionalRViewSet,
    base_r_me_view_set=BaseRegionalRMeViewSet,
)
r9_view_sets_factory.create_view_sets()


class RegionalR101ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR101.objects.all()
    serializer_class = RegionalR101Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR101MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR101
    queryset = RegionalR101.objects.all()
    serializer_class = RegionalR101Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR102ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR102.objects.all()
    serializer_class = RegionalR102Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR102MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR102
    queryset = RegionalR102.objects.all()
    serializer_class = RegionalR102Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR11ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR11.objects.all()
    serializer_class = RegionalR11Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)
    parser_classes = (MultiPartParser, FormParser)


class RegionalR11MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR11
    queryset = RegionalR11.objects.all()
    serializer_class = RegionalR11Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR12ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR12.objects.all()
    serializer_class = RegionalR12Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)
    parser_classes = (MultiPartParser, FormParser)


class RegionalR12MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR12
    queryset = RegionalR12.objects.all()
    serializer_class = RegionalR12Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR13ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR13.objects.all()
    serializer_class = RegionalR13Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)
    parser_classes = (MultiPartParser, FormParser)


class RegionalR13MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR13
    queryset = RegionalR13.objects.all()
    serializer_class = RegionalR13Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR16ViewSet(BaseRegionalRViewSet):
    queryset = RegionalR16.objects.all()
    serializer_class = RegionalR16Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR16MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR16
    queryset = RegionalR16.objects.all()
    serializer_class = RegionalR16Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR17ViewSet(BaseRegionalRViewSet):
    """Дислокация студенческих отрядов РО РСО.

    file_size выводится в мегабайтах.
    """

    queryset = RegionalR17.objects.all()
    serializer_class = RegionalR17Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)
    parser_classes = (MultiPartParser, FormParser)


class RegionalR17MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR17
    queryset = RegionalR17.objects.all()
    serializer_class = RegionalR17Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR18ViewSet(RegionalRNoVerifViewSet):
    """Вьюсет для просмотра и создания отчета по 18 показателю.

    Показатель не требует верификации.
    Доступ - только региональным командирам.
    """
    queryset = RegionalR18.objects.all()
    serializer_class = RegionalR18Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        """Метод для создания отчета по 18 показателю.
        Пример отчета:
        ```json
                {
        "comment": "Комментарий",
        "projects": [
            {
                "links": [
                    {
                    "link": "http://127.0.0.1:8000/swagger/"
                    }
                ]
            }
        ]
        }
        ```

        Также стоят MultiPartParser, FormParser.
        """
        return super().create(request, *args, **kwargs)


class RegionalR18MeViewSet(BaseRegionalRMeViewSet):
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


class RegionalR19ViewSet(BaseRegionalRViewSet):
    """Трудоустройство."""

    queryset = RegionalR19.objects.all()
    serializer_class = RegionalR19Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR19MeViewSet(BaseRegionalRMeViewSet, SendMixin):
    model = RegionalR19
    queryset = RegionalR19.objects.all()
    serializer_class = RegionalR19Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)
