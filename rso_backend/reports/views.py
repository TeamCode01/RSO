import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.storage import default_storage
from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from celery.result import AsyncResult
from urllib.parse import quote
from reports.tasks import generate_excel_file
from competitions.models import CompetitionParticipants
from questions.models import Attempt
from reports.constants import (ATTRIBUTION_DATA_HEADERS,
                               COMPETITION_PARTICIPANTS_DATA_HEADERS,
                               DETACHMENT_Q_RESULTS_HEADERS,
                               MEMBERSHIP_FEE_DATA_HEADERS,
                               SAFETY_TEST_RESULTS_HEADERS,
                               COMPETITION_PARTICIPANTS_CONTACT_DATA_HEADERS, Q5_DATA_HEADERS, Q6_DATA_HEADERS, Q7_DATA_HEADERS, Q8_DATA_HEADERS, Q9_DATA_HEADERS, Q10_DATA_HEADERS, Q11_DATA_HEADERS, Q12_DATA_HEADERS,
                               Q15_DATA_HEADERS, Q16_DATA_HEADERS, Q17_DATA_HEADERS,
                               Q18_DATA_HEADERS,
                               COMMANDER_SCHOOL_DATA_HEADERS,
                               Q13_DATA_HEADERS, Q14_DATA_HEADERS,
                               Q19_DATA_HEADERS, DISTRICT_HQ_HEADERS, REGIONAL_HQ_HEADERS,
                               LOCAL_HQ_HEADERS, EDUCATION_HQ_HEADERS, DETACHMENT_HEADERS, CENTRAL_HQ_HEADERS,
                               DIRECTIONS_HEADERS)

from reports.utils import (
    get_attributes_of_uniform_data, get_commander_school_data,
    get_competition_users, get_detachment_q_results,
    adapt_attempts, get_membership_fee_data
)
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from api.permissions import (IsCentralCommander, IsDistrictCommander, IsDetachmentCommander,
                             IsEducationalCommander, IsLocalCommander, IsRegionalCommander)


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


class BaseExcelExportMixin:
    def get_worksheet_title(self):
        """To be overridden."""
        raise NotImplementedError('Define a method to get the Worksheet title of the Excel file.')

    def get_headers(self):
        """To be overridden."""
        raise NotImplementedError('Define a method to get headers for the Excel file.')

    def get_filename(self):
        """To be overridden."""
        raise NotImplementedError('Define a method to get the filename for the Excel file.')

    def get_data_func(self):
        """For calling the required function in the Celery task. Can be overridden in subclass."""
        return 'default'
    
    def get_fields(self):
        return None

    def process_request(self, request):
        headers = self.get_headers()
        worksheet_title = self.get_worksheet_title()
        filename = self.get_filename()
        safe_filename = quote(filename)
        data_func = self.get_data_func()
        
        if isinstance(data_func, dict):
            return data_func

        if hasattr(self, 'get_fields'):
            fields = self.get_fields()
            
        if fields:
            task = generate_excel_file.delay(headers, worksheet_title, safe_filename, data_func, fields)
        else:
            task = generate_excel_file.delay(headers, worksheet_title, safe_filename, data_func)

        return {'task_id': task.id}


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(has_reports_access, login_url='/', redirect_field_name=None), name='dispatch')
class BaseExcelExportView(BaseExcelExportMixin, View):
    def get(self, request):
        result = self.process_request(request)
        return JsonResponse(result)


class BaseExcelExportAPIView(BaseExcelExportMixin, views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        result = self.process_request(request)
        return Response(result, status=status.HTTP_200_OK)


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
    
class ExportQ6DataView(BaseExcelExportView):

    def get_headers(self):
        return Q6_DATA_HEADERS

    def get_filename(self):
        return f'Участие_членов_студ_отр_в_обяз_общесис_мероп_на_рег_ур_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Участие членов студенческого отряда в обязательных общесистемных мероприятиях на региональном уровне'

    def get_data_func(self):
        return 'get_q6_data'

class ExportQ7DataView(BaseExcelExportView):
    def get_headers(self):
        return Q7_DATA_HEADERS

    def get_filename(self):
        return f'Участие_членов_студ_отр_во_всерос_мероприятиях_РСО_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Участие членов студенческого отряда во всероссийских мероприятиях РСО'

    def get_data_func(self):
        return 'get_q7_data'       

class ExportQ8DataView(BaseExcelExportView):
    def get_headers(self):
        return Q8_DATA_HEADERS

    def get_filename(self):
        return f'Призовые_места_отр_в_окруж_межрег_конк_РСО_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Призовые места отряда в окружных и межрегиональных мероприятиях и конкурсах РСО'

    def get_data_func(self):
        return 'get_q8_data'       

class ExportQ9DataView(BaseExcelExportView):
    def get_headers(self):
        return Q9_DATA_HEADERS

    def get_filename(self):
        return f'Призовые_места_отр_во_всеросс_мероп_и конк_РСО_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Призовые места отряда во всероссийских мероприятиях и конкурсах РСО'

    def get_data_func(self):
        return 'get_q9_data'       

class ExportQ10DataView(BaseExcelExportView):
    def get_headers(self):
        return Q10_DATA_HEADERS

    def get_filename(self):
        return f'Призовые_места_отр_на_окруж_и_межрегионал_труд_проектах_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Призовые места отряда на окружных и межрегиональных трудовых проектах'

    def get_data_func(self):
        return 'get_q10_data'       

class ExportQ11DataView(BaseExcelExportView):
    def get_headers(self):
        return Q11_DATA_HEADERS

    def get_filename(self):
        return f'Призовые_места_отр_на_всеросс_труд_проектах_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Призовые места отряда на всероссийских трудовых проектах'

    def get_data_func(self):
        return 'get_q11_data'       

class ExportQ12DataView(BaseExcelExportView):
    def get_headers(self):
        return Q12_DATA_HEADERS

    def get_filename(self):
        return f'Организ_собственных_мероприятий_отр_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Организация собственных мероприятий отряда'

    def get_data_func(self):
        return 'get_q12_data'       

class ExportQ13DataView(BaseExcelExportView):

    def get_headers(self):
        return Q13_DATA_HEADERS

    def get_filename(self):
        return f'Организац_собств_мероприятий_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Организация мероприятий'

    def get_data_func(self):
        return 'get_q13_data'    
    

class ExportQ14DataView(BaseExcelExportView):

    def get_headers(self):
        return Q14_DATA_HEADERS

    def get_filename(self):
        return f'Отнош_колва_бойцов_отраб_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Отношение отработавших'

    def get_data_func(self):
        return 'get_q14_data'
    

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
    

class ExportQ19DataView(BaseExcelExportView):
    def get_headers(self):
        return Q19_DATA_HEADERS

    def get_filename(self):
        return f'Отсутствие_нарушений_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Отсутствие нарушений'

    def get_data_func(self):
        return 'get_q19_data'


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
    

class CommanerPermissionMixin:
    def get_user_role(self):
        user = self.request.user
        
        if hasattr(user, 'centralheadquarter_commander'):
            return 'central'
        elif hasattr(user, 'districtheadquarter_commander'):
            return 'district'
        elif hasattr(user, 'regionalheadquarter_commander'):
            return 'regional'
        elif hasattr(user, 'localheadquarter_commander'):
            return 'local'
        elif hasattr(user, 'educationalheadquarter_commander'):
            return 'educational'
        elif hasattr(user, 'detachment_commander'):
            return 'detachment'
        else:
            raise PermissionDenied("У вас недостаточно прав")

    def filter_fields_by_role(self, fields, role):
        if role == 'regional':
            return [field for field in fields if field not in ['district_headquarters']]
        elif role == 'local':
            return [field for field in fields if field not in ['district_headquarters', 'regional_headquarters']]
        elif role == 'educational':
            return [field for field in fields if field not in ['district_headquarters', 'regional_headquarters', 'local_headquarters']]
        elif role == 'detachment':
            return [field for field in fields if field not in ['district_headquarters', 'regional_headquarters', 'local_headquarters', 'educational_headquarters']]
        return fields

    def get_fields(self):
        fields = super().get_fields()
        user_role = self.get_user_role()
        return self.filter_fields_by_role(fields, user_role)


class ExportCentralHqDataMixin:
    def get_headers(self):
        return CENTRAL_HQ_HEADERS

    def get_filename(self):
        return f'Центральный_штаб_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Центральный штаб'
    
    def get_fields(self):
        fields = self.request.POST.getlist('fields')
        return fields or[
            'regional_headquarters', 'local_headquarters', 
            'educational_headquarters', 'detachments', 
            'participants_count', 'verification_percent', 
            'membership_fee_percent', 'test_done_percent', 
            'events_organizations', 'event_participants'
            ]
    
    def get_data_func(self):  
        return 'get_central_hq_data'
    

@method_decorator(csrf_exempt, name='dispatch')
class ExportCentralDataView(ExportCentralHqDataMixin, BaseExcelExportView):
    pass


class ExportCentralDataAPIView(CommanerPermissionMixin, ExportCentralHqDataMixin, BaseExcelExportAPIView):
    permission_classes = [IsCentralCommander]


class ExportDistrictHqDataMixin:
    def get_headers(self):
        return DISTRICT_HQ_HEADERS

    def get_filename(self):
        return f'Окружной_штаб_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Окружной штаб'
    
    def get_fields(self):
        fields = self.request.POST.getlist('fields')
        return fields or[
            'regional_headquarters', 'local_headquarters', 
            'educational_headquarters', 'detachments', 
            'participants_count', 'verification_percent', 
            'membership_fee_percent', 'test_done_percent', 
            'events_organizations', 'event_participants'
            ]

    def get_data_func(self):
        return 'get_district_hq_data'
    

class ExportDistrictDataView(ExportDistrictHqDataMixin, BaseExcelExportView):
    pass


class ExportDistrictDataAPIView(CommanerPermissionMixin, ExportDistrictHqDataMixin, BaseExcelExportAPIView):
    permission_classes = [IsDistrictCommander]
    

class ExportRegionalHqDataMixin:
    def get_headers(self):
        return REGIONAL_HQ_HEADERS

    def get_filename(self):
        return f'Региональный_штаб_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Региональный штаб'
    
    def get_fields(self):
        fields = self.request.POST.getlist('fields')
        return fields or[
            'district_headquarters','local_headquarters', 
            'educational_headquarters', 'detachments', 
            'participants_count', 'verification_percent', 
            'membership_fee_percent', 'test_done_percent', 
            'events_organizations', 'event_participants'
            ]

    def get_data_func(self):
        return 'get_regional_hq_data'
    

class ExportRegionalDataView(ExportRegionalHqDataMixin, BaseExcelExportView):
    pass


class ExportRegionalDataAPIView(CommanerPermissionMixin, ExportRegionalHqDataMixin, BaseExcelExportAPIView):
    permission_classes = [IsRegionalCommander]


class ExportLocalHqDataMixin:
    def get_headers(self):
        return LOCAL_HQ_HEADERS

    def get_filename(self):
        return f'Местный_штаб_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'Местный штаб'
    
    def get_fields(self):
        fields = self.request.POST.getlist('fields')
        return fields or[
            'district_headquarters', 'regional_headquarters',
            'educational_headquarters', 'detachments', 
            'participants_count', 'verification_percent', 
            'membership_fee_percent', 'test_done_percent', 
            'events_organizations', 'event_participants'
            ]

    def get_data_func(self):
        return 'get_local_hq_data'
    

class ExportLocalDataView(ExportLocalHqDataMixin, BaseExcelExportView):
    pass


class ExportLocalDataAPIView(CommanerPermissionMixin, ExportLocalHqDataMixin, BaseExcelExportAPIView):
    permission_classes = [IsLocalCommander]


class ExportEducationHqDataMixin:
    def get_headers(self):
        return EDUCATION_HQ_HEADERS

    def get_filename(self):
        return f'СО_ОО_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'СО ОО'
    
    def get_fields(self):
        fields = self.request.POST.getlist('fields')
        return fields or[
            'district_headquarters', 'regional_headquarters',
            'local_headquarters','detachments', 
            'participants_count', 'verification_percent', 
            'membership_fee_percent', 'test_done_percent', 
            'events_organizations', 'event_participants'
            ]

    def get_data_func(self):
        return 'get_educational_hq_data'
    

class ExportEducationDataView(ExportEducationHqDataMixin, BaseExcelExportView):
    pass


class ExportEducationDataAPIView(CommanerPermissionMixin, ExportEducationHqDataMixin, BaseExcelExportAPIView):
    permission_classes = [IsEducationalCommander]


class ExportDetachmentDataMixin:
    def get_headers(self):
        return DETACHMENT_HEADERS

    def get_filename(self):
        return f'ЛСО_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'

    def get_worksheet_title(self):
        return 'ЛСО'
    
    def get_fields(self):
        fields = self.request.POST.getlist('fields')
        return fields or[
            'district_headquarter', 'regional_headquarter',
            'local_headquarter', 'educational_headquarter',
            'directions',
            'participants_count', 'verification_percent', 
            'membership_fee_percent', 'test_done_percent', 
            'events_organizations', 'event_participants'
            ]

    def get_data_func(self):
        return 'get_detachment_data'


class ExportDetachmentDataView(ExportDetachmentDataMixin, BaseExcelExportView):
    pass


class ExportDetachmentDataAPIView(CommanerPermissionMixin, ExportDetachmentDataMixin, BaseExcelExportAPIView):
    permission_classes = [IsDetachmentCommander]


class ExportDirectionDataMixin:
    def get_headers(self):
        return DIRECTIONS_HEADERS
    
    def get_filename(self):
        return f'Направление_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'
    
    def get_worksheet_title(self):
        return 'Направление'
    
    def get_fields(self):
        fields = self.request.POST.getlist('fields')
        return fields or [
            'detachments',
            'participants_count', 'verification_percent', 
            'membership_fee_percent', 'test_done_percent', 
            'events_organizations', 'event_participants'
            ]
        
    def get_data_func(self):
        return 'get_direction_data'
    

class ExportDirectionDataView(ExportDirectionDataMixin, BaseExcelExportView):
    pass


class ExportDirectionDataAPIView(CommanerPermissionMixin, ExportDirectionDataMixin, BaseExcelExportAPIView):
    pass
