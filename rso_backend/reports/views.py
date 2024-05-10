import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from openpyxl import Workbook

from competitions.models import CompetitionParticipants
from questions.models import Attempt
from reports.constants import (COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY,
                               COMPETITION_PARTICIPANTS_DATA_HEADERS,
                               DETACHMENT_Q_RESULTS_HEADERS,
                               OPENXML_CONTENT_TYPE,
                               SAFETY_TEST_RESULTS_HEADERS)
from reports.utils import (enumerate_attempts, get_competition_users,
                           get_detachment_q_results)


class SafetyTestResultsView(View):
    template_name = 'reports/safety_test_results.html'

    def get(self, request):
        results = Attempt.objects.filter(
            category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
        ).order_by('user', 'timestamp')[:15]
        enumerated_results = enumerate_attempts(results)
        context = {'sample_results': enumerated_results}
        return render(request, self.template_name, context)


class ExportSafetyTestResultsView(View):
    def get(self, request):
        results = Attempt.objects.filter(
            category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
        ).order_by('-timestamp', 'user')
        enumerated_results = enumerate_attempts(results)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'Результаты тестирования по безопасности'
        worksheet.append(SAFETY_TEST_RESULTS_HEADERS)

        for index, result in enumerate(enumerated_results, start=1):
            row = [
                index,
                result.user.region.name if result.user.region else '-',
                f'{result.user.last_name} {result.user.first_name} '
                f'{result.user.patronymic_name if result.user.patronymic_name else "(без отчества)"}',
                result.detachment if result.detachment else '-',
                result.detachment_position if result.detachment_position else '-',
                result.attempt_number,
                "Да" if result.is_valid else "Нет",
                result.score,
            ]
            worksheet.append(row)

        response = HttpResponse(
            content_type=OPENXML_CONTENT_TYPE
        )
        response['Content-Disposition'] = 'attachment; filename=тестирование_безопасность_{}.xlsx'.format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        workbook.save(response)
        return response


class CompetitionParticipantView(View):
    template_name = 'reports/competition_participants.html'

    def get(self, request):
        results = CompetitionParticipants.objects.filter()[:15]
        results = get_competition_users(results)
        context = {'sample_results': results}
        return render(request, self.template_name, context)


class ExportCompetitionParticipantsDataView(View):
    def get(self, request):
        competition_participants = CompetitionParticipants.objects.all()
        competition_members_data = get_competition_users(list(competition_participants))

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Данные по участникам конкурсам"
        worksheet.append(COMPETITION_PARTICIPANTS_DATA_HEADERS)

        for detachment, users in competition_members_data:
            for index, user in enumerate(users, start=1):
                row = [
                    index,
                    detachment.region.name if detachment.region else '-',
                    f'{user.last_name} {user.first_name} '
                    f'{user.patronymic_name if user.patronymic_name else "(без отчества)"}',
                    detachment.name if detachment else '-',
                    detachment.status if detachment else '-',
                    detachment.nomination if detachment else '-',
                    user.position if user.position else '-',
                    "Да" if user.is_verified else "Нет",
                    "Да" if user.membership_fee else "Нет",
                ]
                worksheet.append(row)

        response = HttpResponse(
            content_type=OPENXML_CONTENT_TYPE
        )
        response['Content-Disposition'] = 'attachment; filename=участники_данные_{}.xlsx'.format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        workbook.save(response)
        return response


class DetachmentQResultsView(View):
    template_name = 'reports/detachment_q_results.html'

    def get(self, request):
        detachment_q_results = get_detachment_q_results(settings.COMPETITION_ID, is_sample=True)
        context = {'sample_results': detachment_q_results}
        return render(request, self.template_name, context)


class ExportDetachmentQResultsView(View):
    def get(self, request):
        detachments = get_detachment_q_results(settings.COMPETITION_ID)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'Результаты отрядов, показатели'
 
        worksheet.append(DETACHMENT_Q_RESULTS_HEADERS)

        for index, detachment in enumerate(detachments, start=1):
            row = [
                index,
                detachment.region.name,
                detachment.name,
                detachment.status,
                detachment.nomination,
                detachment.participants_count,
                detachment.overall_ranking,
                detachment.places_sum,
            ]
            row.extend(detachment.places)
            worksheet.append(row)

        response = HttpResponse(
            content_type=OPENXML_CONTENT_TYPE
        )
        response['Content-Disposition'] = 'attachment; filename=показатели_конкурс_{}.xlsx'.format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        workbook.save(response)
        return response


class ExportCompetitionParticipantsContactData(View):
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute(COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY)
            rows = cursor.fetchall()

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'Контакты участников конкурса'
        worksheet.append(SAFETY_TEST_RESULTS_HEADERS)

        for row in rows:
            worksheet.append(row)

        response = HttpResponse(
            content_type=OPENXML_CONTENT_TYPE
        )
        response['Content-Disposition'] = 'attachment; filename=контакты_конкурс_{}.xlsx'.format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        workbook.save(response)
        return response


@method_decorator(login_required, name='dispatch')
class ReportView(View):
    template_name = 'reports/reports.html'

    def get(self, request):
        return render(request, self.template_name)
