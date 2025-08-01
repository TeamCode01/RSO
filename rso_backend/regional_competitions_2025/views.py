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
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser


from api.mixins import SendMixin
from api.utils import get_calculation
from headquarters.models import (CentralHeadquarter, RegionalHeadquarter,
                                 UserDistrictHeadquarterPosition, DistrictHeadquarter)
from regional_competitions_2025.constants import EMAIL_REPORT_DECLINED_MESSAGE
from regional_competitions_2025.mixins import (FormDataNestedFileParser, RegionalRMeMixin, 
                                               RegionalRMixin, ListRetrieveCreateMixin, DownloadReportXlsxMixin)
from regional_competitions_2025.models import (CHqRejectingLog, RCompetition, RVerificationLog, RegionalR4)
from regional_competitions_2025.permissions import (IsCentralHeadquarterExpert, IsCentralOrDistrictHeadquarterExpert,
                                                    IsDistrictHeadquarterExpert, IsRegionalCommander,
                                                    IsRegionalCommanderAuthorOrCentralHeadquarterExpert)
from regional_competitions_2025.serializers import RegionalReport4Serializer
from regional_competitions_2025.tasks import send_email_report_part_1, send_mail
from regional_competitions_2025.utils import (current_year, get_all_reports_from_competition, get_report_number_by_class_name,
                                         swagger_schema_for_central_review,
                                         swagger_schema_for_create_and_update_methods,
                                         swagger_schema_for_district_review, swagger_schema_for_retrieve_method,
                                         get_emails)


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
                    'year': self.request.query_params.get('year')
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
        r_competition_year = self.request.query_params.get('year')
        objects = queryset.filter(regional_headquarter_id=pk, r_competition__year=r_competition_year)

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
                'action': self.action,
                'year': self.request.query_params.get('year')
            }
        )
        return context

    def get_object(self):
        regional_headquarter = get_object_or_404(
            RegionalHeadquarter,
            commander=self.request.user
        )

        r_competition_year = self.request.query_params.get('year')
        if r_competition_year:
            r_competition = self.get_r_competition(r_competition_year)
        else:
            r_competition = self.get_r_competition(current_year(), self.model)

        report = self.model.objects.filter(
            regional_headquarter=regional_headquarter,
            r_competition=r_competition
        ).last()

        if report is None:
            raise Http404('Отчет по данному показателю не найден')
        return report

    def update(self, *args, **kwargs):
        """Редактирует актуальную версию отчета для командира регионального штаба.

        Метод идемпотентен. Поддерживается динамическое обновление

        Query параметры:
        - year: год конкурса (опционально, по умолчанию текущий год)
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

        Query параметры:
        - year: год конкурса (опционально, по умолчанию текущий год)

        Возвращает:
        - 200 OK и данные отчета в случае успеха.
        - 404 Not Found, если отчет не найден.
        """
        return Response(self.get_serializer(self.get_object()).data)

    def perform_create(self, serializer):
        regional_hq = RegionalHeadquarter.objects.get(commander=self.request.user)

        r_competition_year = self.request.query_params.get('year')
        if r_competition_year:
            r_competition = self.get_r_competition(r_competition_year)

        serializer.save(
            regional_headquarter=regional_hq,
            r_competition=r_competition
        )

    def get_report_number(self):
        return get_report_number_by_class_name(self)


class BaseRegionalRAutoViewSet(DownloadReportXlsxMixin, GenericViewSet):
    """Базовый вьюсет для выгрузки автоматических отчетов."""


# class RegionalR1ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
#     queryset = RegionalR1.objects.all()
#     serializer_class = RegionalR1Serializer
#     permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


# class RegionalR1MeViewSet(FormDataNestedFileParser, BaseRegionalRMeViewSet, SendMixin):
#     model = RegionalR1
#     queryset = RegionalR1.objects.all()
#     serializer_class = RegionalR1Serializer
#     permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR4ViewSet(FormDataNestedFileParser, BaseRegionalRViewSet):
    """
    Вьюсет для работы с 4 показателем.
    ID - ожидается id регионального штаба.

    Query параметры:
    - year: год конкурса (опционально, по умолчанию текущий год)
    """
    queryset = RegionalR4.objects.all()
    serializer_class = RegionalReport4Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR4MeViewSet(FormDataNestedFileParser, SendMixin, BaseRegionalRMeViewSet):
    """
    Вьюсет для работы с 4 показателем для командира регионального штаба.

    Query параметры:
    - year: год конкурса (опционально, по умолчанию текущий год)
    """
    model = RegionalR4
    queryset = RegionalR4.objects.all()
    serializer_class = RegionalReport4Serializer
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander)


class RegionalR7AutoViewSet(BaseRegionalRAutoViewSet):
    """Вьюсет для выгрузки автоматических отчетов по 7 показателю."""
