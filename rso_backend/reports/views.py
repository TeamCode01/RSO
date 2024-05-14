import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.storage import default_storage
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from celery.result import AsyncResult
from urllib.parse import quote

from reports.tasks import generate_excel_file
from competitions.models import CompetitionParticipants
from questions.models import Attempt
from reports.constants import (COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY,
                               COMPETITION_PARTICIPANTS_DATA_HEADERS,
                               DETACHMENT_Q_RESULTS_HEADERS,
                               SAFETY_TEST_RESULTS_HEADERS, COMPETITION_PARTICIPANTS_CONTACT_DATA_HEADERS)
from reports.utils import (enumerate_attempts, get_competition_users,
                           get_detachment_q_results)


def has_reports_access(user):
    return user.is_authenticated and getattr(user, 'reports_access', False)


class TaskStatusView(View):
    def get(self, request, task_id):
        task = AsyncResult(task_id)
        if task.state == 'SUCCESS':
            file_path = task.result
            download_url = default_storage.url(file_path)
            return JsonResponse({'status': 'SUCCESS', 'download_url': download_url})
        elif task.state == 'FAILURE':
            return JsonResponse({'status': 'FAILURE'})
        return JsonResponse({'status': task.state})


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

    def process_row_type(self):
        """Тип обработки строк для селери-задачи. Может быть переопределено в саб-классе."""
        return 'default'

    def prepare_data(self, data):
        """Для обработки данных, в которых есть несериализуемые объекты. Может быть переопределено в саб-классе."""
        return data

    def process_row(self, index, row):
        return [index] + list(row)

    def get(self, request):
        data = self.prepare_data(self.get_data())
        headers = self.get_headers()
        worksheet_title = self.get_worksheet_title()
        filename = self.get_filename()
        safe_filename = quote(filename)
        process_row_type = self.process_row_type()
        task = generate_excel_file.delay(data, headers, worksheet_title, safe_filename, process_row_type)

        return JsonResponse({'task_id': task.id})


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

    def process_row_type(self):
        return 'safety_test_results'

    def prepare_data(self, data):
        prepared_data = []
        for row in data:
            prepared_data.append({
                'region_name': row.user.region.name if row.user.region else '-',
                'last_name': row.user.last_name,
                'first_name': row.user.first_name,
                'patronymic_name': row.user.patronymic_name,
                'detachment': row.detachment if row.detachment else '-',
                'detachment_position': row.detachment_position if row.detachment_position else '-',
                'attempt_number': row.attempt_number,
                'is_valid': row.is_valid,
                'score': row.score,
            })
        return prepared_data


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

    def process_row_type(self):
        return 'detachment_q_results'

    def prepare_data(self, data):
        prepared_data = []
        for row in data:
            prepared_data.append({
                'region_name': row.region.name,
                'name': row.name,
                'status': row.status,
                'nomination': row.nomination,
                'participants_count': row.participants_count,
                'overall_ranking': row.overall_ranking,
                'places_sum': row.places_sum,
                'places': row.places,
            })
        return prepared_data


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
