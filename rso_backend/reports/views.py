from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.views import View
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from openpyxl import Workbook

from competitions.models import CompetitionParticipants
from questions.models import Attempt
from reports.utils import enumerate_attempts, get_competition_users, get_detachment_q_results
import datetime


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
        results = CompetitionParticipants.objects.filter()[:15]
        results = get_competition_users(results)
        context = {'sample_results': results}
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
        worksheet.title = "Detachment Results"
        headers = [
            '№',
            'Регион',
            'Отряд',
            'Статус отряда',
            'Номинация',
            'Количество участников',
            'Итоговое место',
            'Сумма мест',
            'Численность членов линейного студенческого отряда в соответствии с объемом уплаченных членских взносов',
            'Прохождение Командиром и Комиссаром студенческого отряда региональной школы командного состава',
            'Получение командным составом отряда образования в корпоративном университете РСО',
            'Прохождение обучение по охране труда и пожарной безопасности в рамках недели охраны труда РСО',
            'Процент членов студенческого отряда, прошедших профессиональное обучение',
            'Участие членов студенческого отряда в обязательных общесистемных мероприятиях на региональном уровне',
            'Участие членов студенческого отряда в окружных и межрегиональных мероприятиях РСО',
            'Участие членов студенческого отряда во всероссийских мероприятиях РСО',
            'Призовые места отряда в окружных и межрегиональных мероприятиях и конкурсах РСО',
            'Призовые места отряда во Всероссийских мероприятиях и конкурсах РСО',
            'Призовые места отряда на окружных и межрегиональных трудовых проектах',
            'Призовые места отряда на всероссийских трудовых проектах',
            'Организация собственных мероприятий отряда',
            'Отношение количества бойцов, отработавших в летнем трудовом семестре, к общему числу членов отряда',
            'Победы членов отряда в региональных, окружных и всероссийских грантовых конкурсах, направленных на развитие студенческих отрядов',
            'Активность отряда в социальных сетях',
            'Количество упоминаний в СМИ о прошедших творческих, добровольческих и патриотических мероприятиях отряда',
            'Охват бойцов, принявших участие во Всероссийском дне ударного труда',
            'Отсутствие нарушении техники безопасности, охраны труда и противопожарной безопасности в трудовом семестре',
            'Соответствие требованиями положения символики и атрибутике форменной одежды и символики отрядов'
        ]
        worksheet.append(headers)

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
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=detachment_results_{}.xlsx'.format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        workbook.save(response)
        return response


@method_decorator(login_required, name='dispatch')
class ReportView(View):
    template_name = 'reports/reports.html'

    def get(self, request):
        return render(request, self.template_name)
