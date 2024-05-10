import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from openpyxl import Workbook
from urllib.parse import quote

from competitions.models import CompetitionParticipants
from questions.models import Attempt
from reports.constants import (COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY,
                               COMPETITION_PARTICIPANTS_DATA_HEADERS,
                               DETACHMENT_Q_RESULTS_HEADERS,
                               OPENXML_CONTENT_TYPE,
                               SAFETY_TEST_RESULTS_HEADERS, COMPETITION_PARTICIPANTS_CONTACT_DATA_HEADERS)
from reports.utils import (enumerate_attempts, get_competition_users,
                           get_detachment_q_results)


def has_reports_access(user):
    return user.is_authenticated and getattr(user, 'reports_access', False)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class BaseExcelExportView(View):
    def get_data(self):
        """К переопределению."""
        raise NotImplementedError('Определите метод для получения данных для Excel-файла.')

    def get_headers(self):
        """К переопределению."""
        raise NotImplementedError('Определите метод для получения хедеров для Excel-файла.')

    def get_filename(self):
        """К переопределению."""
        raise NotImplementedError('Определите метод для получения названия для Excel-файла.')

    def get_worksheet_title(self):
        """К переопределению."""
        raise NotImplementedError('Определите метод для получения названия Worksheet Excel-файла.')

    def process_row(self, index, row):
        """По умолчанию возвращает запись as is. Может быть переопределено в саб-классе."""
        return [index] + list(row)

    def get(self, request):
        data = self.get_data()
        headers = self.get_headers()
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = self.get_worksheet_title()
        worksheet.append(headers)

        for index, row in enumerate(data, start=1):
            processed_row = self.process_row(index, row)
            worksheet.append(processed_row)

        response = HttpResponse(
            content_type=OPENXML_CONTENT_TYPE
        )
        filename = self.get_filename()
        safe_filename = quote(filename)  # Кодирование имени файла для безопасной передачи в HTTP заголовке
        response['Content-Disposition'] = f'attachment; filename={safe_filename}'
        workbook.save(response)
        return response


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class SafetyTestResultsView(View):
    template_name = 'reports/safety_test_results.html'

    def get(self, request):
        results = Attempt.objects.filter(
            category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
        ).order_by('user', 'timestamp')[:15]
        enumerated_results = enumerate_attempts(results)
        context = {'sample_results': enumerated_results}
        return render(request, self.template_name, context)


class ExportSafetyTestResultsView(BaseExcelExportView):
    def get_data(self):
        results = Attempt.objects.filter(
            category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
        ).order_by('-timestamp', 'user')
        return enumerate_attempts(results)

    def get_headers(self):
        return SAFETY_TEST_RESULTS_HEADERS

    def get_filename(self):
        return f'тестирование_безопасность_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Тестирование - безопасность'

    def process_row(self, index, row):
        return [
            index,
            row.user.region.name if row.user.region else '-',
            f'{row.user.last_name} {row.user.first_name} '
            f'{row.user.patronymic_name if row.user.patronymic_name else "(без отчества)"}',
            row.detachment if row.detachment else '-',
            row.detachment_position if row.detachment_position else '-',
            row.attempt_number,
            "Да" if row.is_valid else "Нет",
            row.score,
        ]


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class CompetitionParticipantView(View):
    template_name = 'reports/competition_participants.html'

    def get(self, request):
        results = CompetitionParticipants.objects.filter()[:15]
        results = get_competition_users(results)
        context = {'sample_results': results}
        return render(request, self.template_name, context)


class ExportCompetitionParticipantsDataView(BaseExcelExportView):

    def get_data(self):
        competition_participants = CompetitionParticipants.objects.all()
        competition_members_data = get_competition_users(list(competition_participants))

        rows = []
        for detachment, users in competition_members_data:
            for user in users:
                row = (
                    detachment.region.name if detachment.region else '-',
                    f'{user.last_name} {user.first_name} '
                    f'{user.patronymic_name if user.patronymic_name else "(без отчества)"}',
                    detachment.name if detachment else '-',
                    detachment.status if detachment else '-',
                    detachment.nomination if detachment else '-',
                    user.position if user.position else '-',
                    'Да' if user.is_verified else 'Нет',
                    'Да' if user.membership_fee else 'Нет',
                )
                rows.append(row)
        return rows

    def get_headers(self):
        return COMPETITION_PARTICIPANTS_DATA_HEADERS

    def get_filename(self):
        return f'участники_данные_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Данные участников'


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class DetachmentQResultsView(View):
    template_name = 'reports/detachment_q_results.html'

    def get(self, request):
        detachment_q_results = get_detachment_q_results(settings.COMPETITION_ID, is_sample=True)
        context = {'sample_results': detachment_q_results}
        return render(request, self.template_name, context)


class ExportDetachmentQResultsView(BaseExcelExportView):
    def get_data(self):
        return get_detachment_q_results(settings.COMPETITION_ID)

    def get_headers(self):
        return DETACHMENT_Q_RESULTS_HEADERS

    def get_filename(self):
        return f'показатели_конкурс_результаты_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Результаты отрядов, показатели'

    def process_row(self, index, row):
        return [
            index,
            row.region.name,
            row.name,
            row.status,
            row.nomination,
            row.participants_count,
            row.overall_ranking,
            row.places_sum,
            *row.places
        ]


class ExportCompetitionParticipantsContactData(BaseExcelExportView):
    def get_data(self):
        with connection.cursor() as cursor:
            cursor.execute(COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY)
            rows = cursor.fetchall()
            return rows

    def get_headers(self):
        return COMPETITION_PARTICIPANTS_CONTACT_DATA_HEADERS

    def get_filename(self):
        return f'контакты_конкурс_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Контакты участников конкурса'


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class ReportView(View):
    template_name = 'reports/reports.html'

    def get(self, request):
        return render(request, self.template_name)
