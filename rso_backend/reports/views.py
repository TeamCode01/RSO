from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.views import View
from django.http import HttpResponse
from django.shortcuts import render
from openpyxl import Workbook

from competitions.models import CompetitionParticipants
from questions.models import Attempt
from reports.utils import enumerate_attempts, get_competition_users
import datetime


class SafetyTestResultsView(View):
    template_name = 'reports/safety_test_results.html'

    def get(self, request):
        results = Attempt.objects.filter(
            category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
        ).order_by('user', 'timestamp')
        enumerated_results = enumerate_attempts(results)
        context = {
            'results': enumerated_results,
            'sample_results': enumerated_results[:11],
        }
        return render(request, self.template_name, context)


class ExportSafetyTestResultsView(View):
    def get(self, request):
        results = Attempt.objects.filter(
            category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
        ).order_by('-timestamp', 'user')
        enumerated_results = enumerate_attempts(results)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Safety Test Results"
        headers = ['№', 'Регион', 'ФИО', 'Отряд', 'Должность', 'Попытка', 'Валидность попытки', 'Очки']
        worksheet.append(headers)

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
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=safety_test_results_{}.xlsx'.format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        workbook.save(response)
        return response


class CompetitionParticipantView(View):
    template_name = 'reports/competition_participants.html'

    def get(self, request):
        results = CompetitionParticipants.objects.filter()
        results = get_competition_users(results)
        context = {
            'results': results,
            'sample_results': results[:11],
        }
        return render(request, self.template_name, context)


class ExportCompetitionParticipantsResultsView(View):
    def get(self, request):
        competition_participants = CompetitionParticipants.objects.all()
        competition_members_data = get_competition_users(list(competition_participants))

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Competition Participants Results"
        headers = [
            '№', 'Регион', 'ФИО', 'Отряд', 'Статус отряда',
            'Номинация', 'Должность', 'Верификация', 'Членский взнос'
        ]
        worksheet.append(headers)

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
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=competition_participants_results_{}.xlsx'.format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        workbook.save(response)
        return response


@method_decorator(login_required, name='dispatch')
class ReportView(View):
    template_name = 'reports/reports.html'

    def get(self, request):
        return render(request, self.template_name)
