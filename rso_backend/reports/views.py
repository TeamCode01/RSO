import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from celery.result import AsyncResult
from urllib.parse import quote
from reports.tasks import generate_excel_file
from competitions.models import CompetitionParticipants
from questions.models import Attempt
from reports.constants import (ATTRIBUTION_DATA_HEADERS, COMMANDER_SCHOOL_DATA_HEADERS,
                               COMPETITION_PARTICIPANTS_DATA_HEADERS,
                               DETACHMENT_Q_RESULTS_HEADERS,
                               MEMBERSHIP_FEE_DATA_HEADERS,
                               REGION_USERS_DATA_HEADERS,
                               SAFETY_TEST_RESULTS_HEADERS,
                               COMPETITION_PARTICIPANTS_CONTACT_DATA_HEADERS, Q5_DATA_HEADERS, Q7_DATA_HEADERS, Q8_DATA_HEADERS, Q9_DATA_HEADERS,
                               Q15_DATA_HEADERS, Q16_DATA_HEADERS, Q17_DATA_HEADERS, Q20_DATA_HEADERS,
                               Q18_DATA_HEADERS)

from reports.utils import (
    get_attributes_of_uniform_data, get_commander_school_data, get_competition_users, get_detachment_q_results,
    adapt_attempts, get_membership_fee_data
)


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
            return JsonResponse({'status': 'FAILURE',
                                 'result': str(task.result),
                                 'traceback': str(task.traceback)})
        return JsonResponse({'status': task.state})


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class BaseExcelExportView(View):

    def get_worksheet_title(self):
        """К переопределению."""
        raise NotImplementedError('Определите метод для получения названия Worksheet Excel-файла.')

    def get_headers(self):
        """К переопределению."""
        raise NotImplementedError('Определите метод для получения хедеров для Excel-файла.')

    def get_filename(self):
        """К переопределению."""
        raise NotImplementedError('Определите метод для получения названия для Excel-файла.')

    def get_data_func(self):
        """Для вызова нужной функции в селери-задаче. Может быть переопределено в саб-классе."""
        return 'default'

    def get(self, request):
        headers = self.get_headers()
        worksheet_title = self.get_worksheet_title()
        filename = self.get_filename()
        safe_filename = quote(filename)
        data_func = self.get_data_func()
        task = generate_excel_file.delay(headers, worksheet_title, safe_filename, data_func)

        return JsonResponse({'task_id': task.id})


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class SafetyTestResultsView(View):
    template_name = 'reports/safety_test_results.html'

    def get(self, request):
        results = Attempt.objects.filter(
            category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
        ).order_by('user', 'timestamp')[:15]
        enumerated_results = adapt_attempts(results)
        context = {'sample_results': enumerated_results}
        return render(request, self.template_name, context)


class ExportSafetyTestResultsView(BaseExcelExportView):
    def get_data_func(self):
        return 'safety_test_results'

    def get_headers(self):
        return SAFETY_TEST_RESULTS_HEADERS

    def get_filename(self):
        return f'тестирование_безопасность_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Тестирование - безопасность'


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class CompetitionParticipantView(View):
    template_name = 'reports/competition_participants.html'

    def get(self, request):
        results = CompetitionParticipants.objects.filter()[:1]
        results = get_competition_users(results)
        context = {'sample_results': results}
        return render(request, self.template_name, context)


class ExportCompetitionParticipantsDataView(BaseExcelExportView):

    def get_headers(self):
        return COMPETITION_PARTICIPANTS_DATA_HEADERS

    def get_filename(self):
        return f'участники_данные_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Данные участников'

    def get_data_func(self):
        return 'competition_participants'


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class DetachmentQResultsView(View):
    template_name = 'reports/detachment_q_results.html'

    def get(self, request):
        detachment_q_results = get_detachment_q_results(settings.COMPETITION_ID, is_sample=True)
        context = {'sample_results': detachment_q_results}
        return render(request, self.template_name, context)


class ExportDetachmentQResultsView(BaseExcelExportView):
    def get_data_func(self):
        return 'detachment_q_results'

    def get_headers(self):
        return DETACHMENT_Q_RESULTS_HEADERS

    def get_filename(self):
        return f'показатели_конкурс_результаты_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Результаты отрядов, показатели'


class ExportCompetitionParticipantsContactData(BaseExcelExportView):
    def get_data_func(self):
        return 'contact_data'

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


class ExportCommanderSchoolDataView(BaseExcelExportView):

    def get_headers(self):
        return COMMANDER_SCHOOL_DATA_HEADERS

    def get_filename(self):
        return f'Прохождение_школы_командирского_состава_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Школа командиров'

    def get_data_func(self):
        return 'commander_school'


class ExportQ5DataView(BaseExcelExportView):

    def get_headers(self):
        return Q5_DATA_HEADERS

    def get_filename(self):
        return f'Процент_членов_отр_проф_обуч_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Школа командиров'

    def get_data_func(self):
        return 'get_q5_data'

class ExportQ7DataView(BaseExcelExportView):
    def get_headers(self):
        return Q7_DATA_HEADERS

    def get_filename(self):
        return f'Процент_членов_отр_проф_обуч_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Школа командиров'

    def get_data_func(self):
        return 'get_q7_data'       

class ExportQ8DataView(BaseExcelExportView):
    def get_headers(self):
        return Q8_DATA_HEADERS

    def get_filename(self):
        return f'Процент_членов_отр_проф_обуч_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Школа командиров'

    def get_data_func(self):
        return 'get_q8_data'       

class ExportQ9DataView(BaseExcelExportView):
    def get_headers(self):
        return Q9_DATA_HEADERS

    def get_filename(self):
        return f'Процент_членов_отр_проф_обуч_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Школа командиров'

    def get_data_func(self):
        return 'get_q9_data'       

class ExportQ15DataView(BaseExcelExportView):

    def get_headers(self):
        return Q15_DATA_HEADERS

    def get_filename(self):
        return f'Победы_членов_отр_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Победы членов отряда'

    def get_data_func(self):
        return 'get_q15_data'


class ExportQ16DataView(BaseExcelExportView):

    def get_headers(self):
        return Q16_DATA_HEADERS

    def get_filename(self):
        return f'Активность_в_соц_сет{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Активность в социальных сетях'

    def get_data_func(self):
        return 'get_q16_data'


class ExportQ17DataView(BaseExcelExportView):

    def get_headers(self):
        return Q17_DATA_HEADERS

    def get_filename(self):
        return f'Колич_упоминаний_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Количеество упоминаний в СМИ'

    def get_data_func(self):
        return 'get_q17_data'


class ExportQ18DataView(BaseExcelExportView):
    def get_headers(self):
        return Q18_DATA_HEADERS

    def get_filename(self):
        return f'Охват_бойцов_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Охват бойцов, принявших участие во Всероссийском дне ударного труда'

    def get_data_func(self):
        return 'get_q18_data'
    

class ExportQ20DataView(BaseExcelExportView):

    def get_headers(self):
        return Q20_DATA_HEADERS

    def get_filename(self):
        return f'Соотвецтв_требованиям_и_полож_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Соответствование требованиям'

    def get_data_func(self):
        return 'get_q20_data'


@method_decorator(login_required, name='dispatch')
@method_decorator(
    user_passes_test(has_reports_access,
                     login_url='/',
                     redirect_field_name=None),
    name='dispatch')
class CommanderSchoolView(View):
    template_name = 'reports/commander_school.html'

    def get(self, request):
        results = get_commander_school_data(settings.COMPETITION_ID)
        context = {'sample_results': results,
                   'columns': COMMANDER_SCHOOL_DATA_HEADERS}
        return render(request, self.template_name, context)


class ExportRegionsUserDataView(BaseExcelExportView):

    def get_headers(self):
        return REGION_USERS_DATA_HEADERS

    def get_filename(self):
        return f'юзеры_по_регионам_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Данные пользователей по регионам'

    def get_data_func(self):
        return 'regions_users_data'


class ExportMembershipFeeDataView(BaseExcelExportView):

    def get_headers(self):
        return MEMBERSHIP_FEE_DATA_HEADERS

    def get_filename(self):
        return f'оплата членского_взноса_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Оплата членского взноса'

    def get_data_func(self):
        return 'membership_fee'


@method_decorator(login_required, name='dispatch')
@method_decorator(
    user_passes_test(has_reports_access,
                     login_url='/',
                     redirect_field_name=None),
    name='dispatch')
class MembershipFeeDataView(View):
    template_name = 'reports/membership_fee.html'

    def get(self, request):
        results = get_membership_fee_data(settings.COMPETITION_ID)
        context = {'sample_results': results,
                   'columns': MEMBERSHIP_FEE_DATA_HEADERS}
        return render(request, self.template_name, context)


class ExportAttributesOfUniformView(BaseExcelExportView):

    def get_headers(self):
        return ATTRIBUTION_DATA_HEADERS

    def get_filename(self):
        return f'соответствие_символики_отрядов_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Соответствие символики отрядов'

    def get_data_func(self):
        return 'attributes_of_uniform'


@method_decorator(login_required, name='dispatch')
@method_decorator(
    user_passes_test(has_reports_access,
                     login_url='/',
                     redirect_field_name=None),
    name='dispatch')
class AttributesOfUniformDataView(View):
    template_name = 'reports/attributes_of_uniform.html'

    def get(self, request):
        results = get_attributes_of_uniform_data(settings.COMPETITION_ID)
        context = {'sample_results': results,
                   'columns': ATTRIBUTION_DATA_HEADERS}
        return render(request, self.template_name, context)
