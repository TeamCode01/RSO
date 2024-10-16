from urllib.parse import urljoin

from django.db import connection, models
from django.db.models import Count, Q, Case, When, Value
from django.conf import settings

from collections import defaultdict
from typing import List, Tuple

from api.utils import get_user_detachment, get_user_detachment_position
from competitions.constants import SOLO_RANKING_MODELS, TANDEM_RANKING_MODELS
from competitions.models import (CompetitionParticipants, OverallRanking,
                                 OverallTandemRanking, Q5DetachmentReport, Q5EducatedParticipant, Q5TandemRanking, Q5Ranking,
                                 Q6DetachmentReport, Q6TandemRanking, Q6Ranking,
                                 SpartakiadBlock, DemonstrationBlock, PatrioticActionBlock,
                                 SafetyWorkWeekBlock, CommanderCommissionerSchoolBlock,
                                 WorkingSemesterOpeningBlock, CreativeFestivalBlock,
                                 ProfessionalCompetitionBlock, Q15GrantWinner,
                                 Q7Ranking, Q7Report, Q7TandemRanking, LinksQ7, Q7,
                                 Q8Ranking, Q8Report, Q8TandemRanking, Q8, Q9Ranking, Q9Report, Q9TandemRanking, Q9, Q10Ranking, Q10Report, Q10TandemRanking, Q10, Q11Ranking, Q11Report, Q11TandemRanking, Q11, Q12Ranking, Q12Report, Q12TandemRanking, Q12, Q15Rank, Q15TandemRank,
                                 Q15DetachmentReport, Q17DetachmentReport,
                                 Q17EventLink, Q17Ranking, Q17TandemRanking,
                                 Q16Ranking, Q16TandemRanking, Q16Report,
                                 Q18TandemRanking, Q18Ranking, Q18DetachmentReport,
                                 Q13TandemRanking, Q13Ranking, Q13DetachmentReport,
                                 Q13EventOrganization, Q14DetachmentReport, Q14LaborProject, Q14Ranking, Q14TandemRanking, Q19Ranking, Q19Report, Q19TandemRanking, LinksQ8)
from headquarters.count_hq_members import count_headquarter_participants, get_hq_participants_15_september
from headquarters.models import UserDetachmentPosition, Detachment
from questions.models import Attempt
from users.models import RSOUser, UserRegion
from reports.constants import COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY


def process_detachment_users(detachment: Detachment, status: str, nomination: str) -> List[RSOUser]:
    users_to_append = []
    commander = detachment.commander
    commander.position = 'Командир'
    users_to_append.append(commander)
    users_in_detachment = UserDetachmentPosition.objects.filter(headquarter=detachment)
    for entry in users_in_detachment:
        user = entry.user
        user.position = entry.position.name
        users_to_append.append(user)
    detachment.status = status
    detachment.nomination = nomination
    return users_to_append


def get_competition_users(
        competition_participants: List[CompetitionParticipants]
) -> List[Tuple[Detachment, List[RSOUser]]]:
    competition_members_data: List[Tuple[Detachment, List[RSOUser]]] = []
    for participant_entry in competition_participants:
        if participant_entry.detachment:
            area_name = participant_entry.detachment.area.name if participant_entry.detachment.area else '-'
            users_to_append = process_detachment_users(
                participant_entry.detachment,
                'Наставник',
                'Тандем',
            )
            participant_entry.detachment.area_name = area_name
            competition_members_data.append((participant_entry.detachment, users_to_append))

        if participant_entry.junior_detachment:
            area_name = participant_entry.junior_detachment.area.name if participant_entry.junior_detachment.area else '-'
            nomination = 'Тандем' if participant_entry.detachment else 'Дебют'
            users_to_append = process_detachment_users(
                participant_entry.junior_detachment,
                'Младший отряд',
                nomination,
            )
            participant_entry.junior_detachment.area_name = area_name
            competition_members_data.append((participant_entry.junior_detachment, users_to_append))

    return competition_members_data


def get_detachment_q_results(competition_id: int, is_sample=False) -> List[Detachment]:
    competition_members_data = []
    if is_sample:
        junior_detachments_queryset = CompetitionParticipants.objects.filter(
                junior_detachment__isnull=False,
                detachment__isnull=True,
                competition_id=competition_id
        )[:10]
    else:
        junior_detachments_queryset = CompetitionParticipants.objects.filter(
            junior_detachment__isnull=False,
            detachment__isnull=True,
            competition_id=competition_id
        )
    for participant_entry in junior_detachments_queryset:
        detachment = participant_entry.junior_detachment
        detachment.participants_count = get_hq_participants_15_september(detachment)
        detachment.status = 'Младший отряд'
        detachment.nomination = 'Дебют'
        detachment.area_name = detachment.area.name
        detachment.places = []
        try:
            detachment.overall_ranking = OverallRanking.objects.get(
                detachment=detachment, competition_id=competition_id
            ).place
            detachment.places_sum = OverallRanking.objects.get(
                detachment=detachment, competition_id=competition_id
            ).places_sum
        except OverallRanking.DoesNotExist:
            detachment.overall_ranking = 'Рейтинг ещё не сформирован'
            detachment.places_sum = 'Рейтинг ещё не сформирован'
        for q_ranking in SOLO_RANKING_MODELS:
            try:
                detachment.places.append(q_ranking.objects.get(
                    detachment=detachment, competition_id=competition_id
                ).place)
            except q_ranking.DoesNotExist:
                detachment.places.append('Рейтинг еще не сформирован')
        competition_members_data.append(detachment)
    if is_sample:
        tandem_queryset = CompetitionParticipants.objects.filter(
            junior_detachment__isnull=False,
            detachment__isnull=False,
            competition_id=competition_id
        )[:10]
    else:
        tandem_queryset = CompetitionParticipants.objects.filter(
            junior_detachment__isnull=False,
            detachment__isnull=False,
            competition_id=competition_id
        )
    for participant_entry in tandem_queryset:
        junior_detachment = participant_entry.junior_detachment
        junior_detachment.participants_count = get_hq_participants_15_september(junior_detachment)
        junior_detachment.status = 'Младший отряд'
        junior_detachment.nomination = 'Тандем'
        junior_detachment.area_name = junior_detachment.area.name
        junior_detachment.places = []
        detachment = participant_entry.detachment
        detachment.participants_count = get_hq_participants_15_september(detachment)
        detachment.status = 'Наставник'
        detachment.nomination = 'Тандем'
        detachment.area_name = detachment.area.name
        detachment.places = []
        try:
            overall_ranking = OverallTandemRanking.objects.get(
                detachment=detachment,
                junior_detachment=junior_detachment,
                competition_id=competition_id
            ).place
            places_sum = OverallTandemRanking.objects.get(
                detachment=detachment,
                junior_detachment=junior_detachment,
                competition_id=competition_id
            ).places_sum
        except OverallTandemRanking.DoesNotExist:
            overall_ranking = 'Рейтинг ещё не сформирован'
            places_sum = 'Рейтинг ещё не сформирован'
        detachment.overall_ranking = overall_ranking
        detachment.places_sum = places_sum
        junior_detachment.overall_ranking = overall_ranking
        junior_detachment.places_sum = places_sum
        for q_ranking in TANDEM_RANKING_MODELS:
            try:
                place = q_ranking.objects.get(
                    junior_detachment=junior_detachment,
                    detachment=detachment,
                    competition_id=competition_id
                ).place
            except q_ranking.DoesNotExist:
                place = 'Рейтинг еще не сформирован'
            detachment.places.append(place)
            junior_detachment.places.append(place)
        competition_members_data.append(detachment)
        competition_members_data.append(junior_detachment)
    data = []
    for row in competition_members_data:
        data.append((
            row.region.name,
            row.name,
            row.status,
            row.nomination,
            row.area_name,
            row.participants_count,
            row.overall_ranking,
            row.places_sum,
            *row.places,
        ))
    return competition_members_data if is_sample else data


def adapt_attempts(results: List[Attempt]) -> list:
    user_attempts = defaultdict(int)
    enumerated_results = []

    for result in results:
        user_attempts[result.user_id] += 1
        result.attempt_number = user_attempts[result.user_id]
        result.detachment = get_user_detachment(result.user)
        result.detachment_position = get_user_detachment_position(result.user)
        enumerated_results.append(result)

    return enumerated_results


def get_safety_results():
    results = Attempt.objects.filter(
        category=Attempt.Category.SAFETY, is_valid=True, score__gt=0
    ).order_by('-timestamp', 'user')
    results = adapt_attempts(results)
    prepared_data = []
    for row in results:
        timestamp = row.timestamp
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        prepared_data.append((
            row.user.region.name if row.user.region else '-',
            row.user.last_name,
            row.user.first_name,
            row.user.patronymic_name,
            row.detachment if row.detachment else '-',
            row.detachment.area.name if row.detachment.area else '-',
            row.detachment_position if row.detachment_position else '-',
            row.attempt_number,
            row.is_valid,
            row.score,
            timestamp
        ))
    return prepared_data


def get_competition_participants_data():
    competition_participants = CompetitionParticipants.objects.all()
    competition_members_data = get_competition_users(list(competition_participants))

    rows = []
    for detachment, users in competition_members_data:
        for user in users:
            row = (
                detachment.region.name if detachment.region else '-',
                detachment.area.name if detachment.area else '-',
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


def get_competition_participants_contact_data():
    with connection.cursor() as cursor:
        cursor.execute(COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY)
        rows = cursor.fetchall()
        return rows


def get_regions_users_data():
    users_data = UserRegion.objects.select_related(
            'user',
            'user__documents',
            'user__education',
            # 'user__usercentralheadquarterposition__position',
            # 'user__centralheadquarter_commander',
            # 'user__userdistrictheadquarterposition__position',
            # 'user__districtheadquarter_commander',
            # 'user__userregionalheadquarterposition__position',
            # 'user__regionalheadquarter_commander',
            # 'user__userlocalheadquarterposition__position',
            # 'user__usereducationalheadquarterposition__position',
            # 'user__userdetachmentposition__headquarter__area',
            # 'user__userdetachmentposition__position',
            # 'user__detachment_commander__area'
        ).values_list(
            'reg_region__code',
            'reg_region__name',
            'user__id',
            'user__first_name',
            'user__last_name',
            'user__patronymic_name',
            'user__username',
            'user__date_of_birth',
            'user__documents__russian_passport',
            'user__documents__pass_ser_num',
            'user__documents__pass_whom',
            'user__documents__pass_date',
            'user__documents__pass_code',
            'user__documents__inn',
            'user__documents__snils',
            'reg_town',
            'reg_house',
            'reg_fact_same_address',
            'fact_region_id',
            'fact_region__fact_region__reg_region',
            'fact_town',
            'fact_house',
            'user__education__study_institution',
            'user__education__study_faculty',
            'user__education__study_specialty',
            'user__education__study_year',
            'user__phone_number',
            'user__email',
            'user__social_vk',
            'user__social_tg',
            'user__is_rso_member',
            'user__is_verified',
            'user__membership_fee',
            # 'user__usercentralheadquarterposition',
            # 'user__usercentralheadquarterposition__position__name',
            # 'user__centralheadquarter_commander',
            # 'user__userdistrictheadquarterposition',
            # 'user__userdistrictheadquarterposition__position__name',
            # 'user__districtheadquarter_commander',
            # 'user__userregionalheadquarterposition',
            # 'user__userregionalheadquarterposition__position__name',
            # 'user__regionalheadquarter_commander',
            # 'user__userlocalheadquarterposition',
            # 'user__userlocalheadquarterposition__position__name',
            # 'user__localheadquarter_commander',
            # 'user__usereducationalheadquarterposition',
            # 'user__usereducationalheadquarterposition__position__name',
            # 'user__educationalheadquarter_commander',
            # 'user__userdetachmentposition',
            # 'user__userdetachmentposition__headquarter__area__name',
            # 'user__userdetachmentposition__position__name',
            # 'user__detachment_commander',
            # 'user__detachment_commander__area__name',
        ).all()
    return users_data


def get_commander_school_data(competition_id: int) -> list:
    """Функция формирует данные для отчета q2."""
    # информация по отряду наставнику в тандеме
    detachment_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=False)
    ).select_related(
        'detachment__region'
    ).prefetch_related(
        'detachment__q2detachmentreport_detachment_reports',
        'detachment__q2tandemranking_main_detachment'
    ).values(
        'detachment__name',
        'detachment__region__name',
        'detachment__area__name',
        'detachment__q2detachmentreport_detachment_reports__commander_achievement',
        'detachment__q2detachmentreport_detachment_reports__commissioner_achievement',
        'detachment__q2detachmentreport_detachment_reports__commander_link',
        'detachment__q2detachmentreport_detachment_reports__commissioner_link',
        'detachment__q2tandemranking_main_detachment__place',
    ).all()

    # информация по старт отряду в тандеме
    junior_detachment_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=False)
    ).select_related(
        'junior_detachment__region'
    ).prefetch_related(
        'junior_detachment__q2detachmentreport_detachment_reports',
        'junior_detachment__q2tandemranking_junior_detachment'
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
        'junior_detachment__area__name',
        'junior_detachment__q2detachmentreport_detachment_reports__commander_achievement',
        'junior_detachment__q2detachmentreport_detachment_reports__commissioner_achievement',
        'junior_detachment__q2detachmentreport_detachment_reports__commander_link',
        'junior_detachment__q2detachmentreport_detachment_reports__commissioner_link',
        'junior_detachment__q2tandemranking_junior_detachment__place',
    ).all()

    # информация по старт отряду в индивидуальных заявках
    individual_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=True)
    ).select_related(
        'junior_detachment__region'
    ).prefetch_related(
        'junior_detachment__q2detachmentreport_detachment_reports',
        'junior_detachment__q2ranking'
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
        'junior_detachment__area__name',
        'junior_detachment__q2detachmentreport_detachment_reports__commander_achievement',
        'junior_detachment__q2detachmentreport_detachment_reports__commissioner_achievement',
        'junior_detachment__q2detachmentreport_detachment_reports__commander_link',
        'junior_detachment__q2detachmentreport_detachment_reports__commissioner_link',
        'junior_detachment__q2ranking__place',
    ).all()

    # Добываем данные по отряду наставнику в тандеме
    rows = [
        (
            data.get('detachment__name', '-'),
            data.get('detachment__region__name', '-'),
            'Тандем',
            data.get('detachment__area__name', '-') or '-',
            'Да' if data.get('detachment__q2detachmentreport_detachment_reports__commander_achievement') else 'Нет',
            'Да' if data.get('detachment__q2detachmentreport_detachment_reports__commissioner_achievement') else 'Нет',
            data.get('detachment__q2detachmentreport_detachment_reports__commander_link', '-') or '-',
            data.get('detachment__q2detachmentreport_detachment_reports__commissioner_link', '-') or '-',
            data.get('detachment__q2tandemranking_main_detachment__place', 'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in detachment_data
    ]

    # Добываем данные по отряду старт в тандеме
    rows.extend([
        (
            data.get('junior_detachment__name', '-'),
            data.get('junior_detachment__region__name', '-'),
            'Тандем',
            data.get('junior_detachment__area__name', '-') or '-',
            'Да' if data.get('junior_detachment__q2detachmentreport_detachment_reports__commander_achievement') else 'Нет',
            'Да' if data.get('junior_detachment__q2detachmentreport_detachment_reports__commissioner_achievement') else 'Нет',
            data.get('junior_detachment__q2detachmentreport_detachment_reports__commander_link', '-') or '-',
            data.get('junior_detachment__q2detachmentreport_detachment_reports__commissioner_link', '-') or '-',
            data.get('junior_detachment__q2tandemranking_junior_detachment__place', 'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in junior_detachment_data
    ])

    # Добываем данные по отряду старт в индивидуальных заявках
    rows.extend([
        (
            data.get('junior_detachment__name', '-'),
            data.get('junior_detachment__region__name', '-'),
            'Дебют',
            data.get('junior_detachment__area__name', '-') or '-',
            'Да' if data.get('junior_detachment__q2detachmentreport_detachment_reports__commander_achievement') else 'Нет',
            'Да' if data.get('junior_detachment__q2detachmentreport_detachment_reports__commissioner_achievement') else 'Нет',
            data.get('junior_detachment__q2detachmentreport_detachment_reports__commander_link', '-') or '-',
            data.get('junior_detachment__q2detachmentreport_detachment_reports__commissioner_link', '-') or '-',
            data.get('junior_detachment__q2ranking__place', 'Ещё нет в рейтинге') or 'Ещё нет в рейтинге'
        ) for data in individual_data
    ])
    return rows


def get_q5_data(competition_id: int) -> list:
    rows = []

    # Fetch all related data once to avoid multiple queries
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q5DetachmentReport.objects.all().select_related('detachment')
    educated_participants = Q5EducatedParticipant.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q5TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q5Ranking.objects.all()}

    # Fetch data for the main detachments
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for edu_participant in educated_participants.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    document_url = f'https://{settings.DEFAULT_SITE_URL}{edu_participant.document.url}' if edu_participant.document else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        edu_participant.name,
                        document_url,
                        'Верифицирован' if edu_participant.is_verified else 'Не верифицирован',
                        place
                    ))

    # Fetch data for the junior detachments in tandem
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for edu_participant in educated_participants.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    document_url = f'https://{settings.DEFAULT_SITE_URL}{edu_participant.document.url}' if edu_participant.document else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        edu_participant.name,
                        document_url,
                        'Верифицирован' if edu_participant.is_verified else 'Не верифицирован',
                        place
                    ))

    # Fetch data for individual participants
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for edu_participant in educated_participants.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                    document_url = f'https://{settings.DEFAULT_SITE_URL}{edu_participant.document.url}' if edu_participant.document else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        edu_participant.name,
                        document_url,
                        'Верифицирован' if edu_participant.is_verified else 'Не верифицирован',
                        place
                    ))

    return rows

def get_q6_data(competition_id: int) -> list:
    rows = []

    # Fetch all related data once to avoid multiple queries
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q6DetachmentReport.objects.all().select_related('detachment')
    spartakiad_blocks = {s.report_id: s for s in SpartakiadBlock.objects.all()}
    demonstration_blocks = {d.report_id: d for d in DemonstrationBlock.objects.all()}
    patriotic_action_blocks = {p.report_id: p for p in PatrioticActionBlock.objects.all()}
    safety_work_week_blocks = {s.report_id: s for s in SafetyWorkWeekBlock.objects.all()}
    commander_commissioner_school_blocks = {c.report_id: c for c in CommanderCommissionerSchoolBlock.objects.all()}
    working_semester_opening_blocks = {w.report_id: w for w in WorkingSemesterOpeningBlock.objects.all()}
    creative_festival_blocks = {c.report_id: c for c in CreativeFestivalBlock.objects.all()}
    professional_competition_blocks = {p.report_id: p for p in ProfessionalCompetitionBlock.objects.all()}
    tandem_rankings = {tr.detachment_id: tr for tr in Q6TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q6Ranking.objects.all()}

    # Fetch data for the main detachments
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            report = reports.filter(detachment_id=detachment.id).first()
            if report:
                spartakiad = spartakiad_blocks.get(report.id)
                demonstration = demonstration_blocks.get(report.id)
                patriotic_action = patriotic_action_blocks.get(report.id)
                safety_work_week = safety_work_week_blocks.get(report.id)
                commander_commissioner_school = commander_commissioner_school_blocks.get(report.id)
                working_semester_opening = working_semester_opening_blocks.get(report.id)
                creative_festival = creative_festival_blocks.get(report.id)
                professional_competition = professional_competition_blocks.get(report.id)
                place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Тандем',
                    detachment.area.name if detachment.area else '-',
                    'Да' if demonstration and demonstration.first_may_demonstration else 'Нет',
                    demonstration.first_may_demonstration_participants if demonstration else '-',
                    'Да' if patriotic_action and patriotic_action.patriotic_action else 'Нет',
                    patriotic_action.patriotic_action_participants if patriotic_action else '-',
                    'Да' if safety_work_week and safety_work_week.safety_work_week else 'Нет',
                    'Да' if commander_commissioner_school and commander_commissioner_school.commander_commissioner_school else 'Нет',
                    'Да' if working_semester_opening and working_semester_opening.working_semester_opening else 'Нет',
                    working_semester_opening.working_semester_opening_participants if working_semester_opening else '-',
                    'Да' if creative_festival and creative_festival.creative_festival else 'Нет',
                    'Да' if spartakiad and spartakiad.spartakiad else 'Нет',
                    'Да' if professional_competition and professional_competition.professional_competition else 'Нет',
                    report.score if report else '-',
                    place
                ))

    # Fetch data for the junior detachments in tandem
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            report = reports.filter(detachment_id=junior_detachment.id).first()
            if report:
                spartakiad = spartakiad_blocks.get(report.id)
                demonstration = demonstration_blocks.get(report.id)
                patriotic_action = patriotic_action_blocks.get(report.id)
                safety_work_week = safety_work_week_blocks.get(report.id)
                commander_commissioner_school = commander_commissioner_school_blocks.get(report.id)
                working_semester_opening = working_semester_opening_blocks.get(report.id)
                creative_festival = creative_festival_blocks.get(report.id)
                professional_competition = professional_competition_blocks.get(report.id)
                place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                rows.append((
                    junior_detachment.name,
                    junior_detachment.region.name if junior_detachment.region else '-',
                    'Тандем',
                    junior_detachment.area.name if junior_detachment.area else '-',
                    'Да' if demonstration and demonstration.first_may_demonstration else 'Нет',
                    demonstration.first_may_demonstration_participants if demonstration else '-',
                    'Да' if patriotic_action and patriotic_action.patriotic_action else 'Нет',
                    patriotic_action.patriotic_action_participants if patriotic_action else '-',
                    'Да' if safety_work_week and safety_work_week.safety_work_week else 'Нет',
                    'Да' if commander_commissioner_school and commander_commissioner_school.commander_commissioner_school else 'Нет',
                    'Да' if working_semester_opening and working_semester_opening.working_semester_opening else 'Нет',
                    working_semester_opening.working_semester_opening_participants if working_semester_opening else '-',
                    'Да' if creative_festival and creative_festival.creative_festival else 'Нет',
                    'Да' if spartakiad and spartakiad.spartakiad else 'Нет',
                    'Да' if professional_competition and professional_competition.professional_competition else 'Нет',
                    report.score if report else '-',
                    place
                ))

    # Fetch data for individual participants
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            report = reports.filter(detachment_id=detachment.id).first()
            if report:
                spartakiad = spartakiad_blocks.get(report.id)
                demonstration = demonstration_blocks.get(report.id)
                patriotic_action = patriotic_action_blocks.get(report.id)
                safety_work_week = safety_work_week_blocks.get(report.id)
                commander_commissioner_school = commander_commissioner_school_blocks.get(report.id)
                working_semester_opening = working_semester_opening_blocks.get(report.id)
                creative_festival = creative_festival_blocks.get(report.id)
                professional_competition = professional_competition_blocks.get(report.id)
                place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Дебют',
                    detachment.area.name if detachment.area else '-',
                    'Да' if demonstration and demonstration.first_may_demonstration else 'Нет',
                    demonstration.first_may_demonstration_participants if demonstration else '-',
                    'Да' if patriotic_action and patriotic_action.patriotic_action else 'Нет',
                    patriotic_action.patriotic_action_participants if patriotic_action else '-',
                    'Да' if safety_work_week and safety_work_week.safety_work_week else 'Нет',
                    'Да' if commander_commissioner_school and commander_commissioner_school.commander_commissioner_school else 'Нет',
                    'Да' if working_semester_opening and working_semester_opening.working_semester_opening else 'Нет',
                    working_semester_opening.working_semester_opening_participants if working_semester_opening else '-',
                    'Да' if creative_festival and creative_festival.creative_festival else 'Нет',
                    'Да' if spartakiad and spartakiad.spartakiad else 'Нет',
                    'Да' if professional_competition and professional_competition.professional_competition else 'Нет',
                    report.score if report else '-',
                    place
                ))

    return rows

def get_q7_data(competition_id: int) -> list:
    rows = []

    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q7Report.objects.all().select_related('detachment')
    participations = Q7.objects.select_related('detachment_report').all()
    links = {l.event_id: l for l in LinksQ7.objects.all()}
    tandem_rankings = {tr.detachment_id: tr for tr in Q7TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q7Ranking.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else '-'
                    social_link = links.get(participation.id).link if participation.id in links else '-'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.number_of_participants if participation.number_of_participants else '-',
                        social_link,
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else '-'
                    social_link = links.get(participation.id).link if participation.id in links else '-'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.number_of_participants if participation.number_of_participants else '-',
                        social_link,
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else '-'
                    social_link = links.get(participation.id).link if participation.id in links else '-'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.number_of_participants if participation.number_of_participants else '-',
                        social_link,
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    return rows

def get_q8_data(competition_id: int) -> list:
    rows = []

    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q8Report.objects.all().select_related('detachment')
    participations = Q8.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q8TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q8Ranking.objects.all()}
    links = {i.event_id:i for i in LinksQ8.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else '-'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    link = links.get(participation.id).link if participation.id in links else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.number_of_participants if participation.number_of_participants else '-',
                        link,
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else '-'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    link = links.get(participation.id).link if participation.id in links else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.number_of_participants if participation.number_of_participants else '-',
                        link,
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else '-'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    link = links.get(participation.id).link if participation.id in links else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.number_of_participants if participation.number_of_participants else '-',
                        link,
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    return rows

def get_q9_data(competition_id: int) -> list:
    rows = []

    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q9Report.objects.all().select_related('detachment')
    participations = Q9.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q9TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q9Ranking.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    return rows

def get_q10_data(competition_id: int) -> list:
    rows = []

    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q10Report.objects.all().select_related('detachment')
    participations = Q10.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q10TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q10Ranking.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    return rows

def get_q11_data(competition_id: int) -> list:
    rows = []

    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q11Report.objects.all().select_related('detachment')
    participations = Q11.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q11TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q11Ranking.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    return rows

def get_q12_data(competition_id: int) -> list:
    rows = []

    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q12Report.objects.all().select_related('detachment')
    participations = Q12.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q12TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q12Ranking.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for participation in participations.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                    certificate_link = f'https://{settings.DEFAULT_SITE_URL}{participation.certificate_scans.url}' if participation.certificate_scans else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        participation.event_name if participation.event_name else '-',
                        participation.prize_place if participation.prize_place else '-',
                        certificate_link,
                        report.score if report.score else '-',
                        place
                    ))

    return rows

def get_q13_data(competition_id: int) -> list:
    rows = []
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q13DetachmentReport.objects.select_related('detachment').all()
    events = Q13EventOrganization.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr.place for tr in Q13TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir.place for ir in Q13Ranking.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for event in events.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id, 'Ещё нет в рейтинге')
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        event.event_type,
                        event.event_link,
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for event in events.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id, 'Ещё нет в рейтинге')
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        event.event_type,
                        event.event_link,
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for event in events.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id, 'Ещё нет в рейтинге')
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'дебют',
                        detachment.area.name if detachment.area else '-',
                        event.event_type,
                        event.event_link,
                        place
                    ))

    return rows


def get_q14_data(competition_id: int) -> list:
    rows = []
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = list(Q14DetachmentReport.objects.select_related('detachment').all())
    projects = list(Q14LaborProject.objects.select_related('detachment_report').all())
    tandem_rankings = {tr.detachment_id: tr.place for tr in Q14TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir.place for ir in Q14Ranking.objects.all()}

    participants_with_detachment = CompetitionParticipants.objects.filter(
        competition_id=competition_id, detachment__isnull=False
    )

    for participant in participants_with_detachment:
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            detachment_reports = [r for r in reports if r.detachment_id == detachment.id]
            for report in detachment_reports:
                detachment_projects = [p for p in projects if p.detachment_report_id == report.id]
                for project in detachment_projects:
                    place = tandem_rankings.get(detachment.id, 'Ещё нет в рейтинге')
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        project.lab_project_name,
                        project.amount,
                        report.score,
                        place
                    ))

    for participant in participants_with_detachment:
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            junior_reports = [r for r in reports if r.detachment_id == junior_detachment.id]
            for report in junior_reports:
                junior_projects = [p for p in projects if p.detachment_report_id == report.id]
                for project in junior_projects:
                    place = tandem_rankings.get(junior_detachment.id, 'Ещё нет в рейтинге')
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        project.lab_project_name,
                        project.amount,
                        report.score,
                        place
                    ))

    participants_without_detachment = CompetitionParticipants.objects.filter(
        competition_id=competition_id, detachment__isnull=True
    )

    for participant in participants_without_detachment:
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            detachment_reports = [r for r in reports if r.detachment_id == detachment.id]
            for report in detachment_reports:
                detachment_projects = [p for p in projects if p.detachment_report_id == report.id]
                for project in detachment_projects:
                    place = individual_rankings.get(detachment.id, 'Ещё нет в рейтинге')
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        project.lab_project_name,
                        project.amount,
                        report.score,
                        place
                    ))

    return rows



def get_q15_data(competition_id: int) -> list:
    rows = []
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q15DetachmentReport.objects.select_related('detachment').all()
    grant_winners = Q15GrantWinner.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q15TandemRank.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q15Rank.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for grant_winner in grant_winners.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    rows.append((
                        detachment.name,
                        detachment.area.name if detachment.area else '-',
                        grant_winner.name,
                        grant_winner.status,
                        grant_winner.author_name,
                        grant_winner.competition_link,
                        grant_winner.prove_link,
                        'Верифицирован' if grant_winner.is_verified else 'Не верифицирован',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                for grant_winner in grant_winners.filter(detachment_report_id=report.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.area.name if junior_detachment.area else '-',
                        grant_winner.name,
                        grant_winner.status,
                        grant_winner.author_name,
                        grant_winner.competition_link,
                        grant_winner.prove_link,
                        'Верифицирован' if grant_winner.is_verified else 'Не верифицирован',
                        place
                    ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                for grant_winner in grant_winners.filter(detachment_report_id=report.id):
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                    rows.append((
                        detachment.name,
                        detachment.area.name if detachment.area else '-',
                        grant_winner.name,
                        grant_winner.status,
                        grant_winner.author_name,
                        grant_winner.competition_link,
                        grant_winner.prove_link,
                        'Верифицирован' if grant_winner.is_verified else 'Не верифицирован',
                        place
                    ))

    return rows


def get_q16_data(competition_id: int) -> list:
    rows = []
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q16Report.objects.select_related('detachment').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q16TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q16Ranking.objects.all()}
    
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Тандем',
                    detachment.area.name if detachment.area else '-',
                    report.link_vk_commander,
                    report.link_vk_commissar,
                    report.vk_rso_number_subscribers,
                    report.link_vk_detachment,
                    report.vk_detachment_number_subscribers,
                    report.score,
                    report.june_15_detachment_members,
                    place
                ))

    try:
        for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
            junior_detachment = detachments.get(participant.junior_detachment_id).first()
            if junior_detachment:
                for report in reports.filter(detachment_id=junior_detachment.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        report.link_vk_commander,
                        report.link_vk_commissar,
                        report.vk_rso_number_subscribers,
                        report.link_vk_detachment,
                        report.vk_detachment_number_subscribers,
                        report.score,
                        report.june_15_detachment_members,
                        place
                    ))
    except Exception as e:
        print(f"Ошибка: {e}")

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Дебют',
                    detachment.area.name if detachment.area else '-',
                    report.link_vk_commander,
                    report.link_vk_commissar,
                    report.vk_rso_number_subscribers,
                    report.link_vk_detachment,
                    report.vk_detachment_number_subscribers,
                    report.score,
                    report.june_15_detachment_members,
                    place
                ))

    return rows


def get_q17_data(competition_id: int) -> list:
    rows = []
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    reports = Q17DetachmentReport.objects.select_related('detachment').all()
    event_links = Q17EventLink.objects.select_related('detachment_report').all()
    tandem_rankings = {tr.detachment_id: tr for tr in Q17TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q17Ranking.objects.all()}

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                report_event_links = event_links.filter(detachment_report_id=report.id)
                for event_link in report_event_links:
                    place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
                        detachment.area.name if detachment.area else '-',
                        str(event_link.detachment_report),
                        event_link.link,
                        place
                    ))

    try:
        for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
            junior_detachment = detachments.filter(id=participant.junior_detachment_id).first()
            if junior_detachment:
                for report in reports.filter(detachment_id=junior_detachment.id):
                    report_event_links = event_links.filter(detachment_report_id=report.id)
                    for event_link in report_event_links:
                        tandem_ranking = tandem_rankings.get(junior_detachment.id)
                        place = tandem_ranking.place if tandem_ranking else 'Ещё нет в рейтинге'
                        rows.append((
                            junior_detachment.name,
                            junior_detachment.region.name if junior_detachment.region else '-',
                            'Тандем',
                            junior_detachment.area.name if junior_detachment.area else '-',
                            str(event_link.detachment_report),
                            event_link.link,
                            place
                        ))
    except Exception as e:
        print(f"Ошибка: {e}")

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                report_event_links = event_links.filter(detachment_report_id=report.id)
                for event_link in report_event_links:
                    place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        detachment.area.name if detachment.area else '-',
                        str(event_link.detachment_report),
                        event_link.link,
                        place
                    ))

    return rows


def get_q18_data(competition_id: int) -> list:
    tandem_rankings = {tr.detachment_id: tr for tr in Q18TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir for ir in Q18Ranking.objects.all()}
    reports = Q18DetachmentReport.objects.all().select_related('detachment')
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    rows = []

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                place = tandem_rankings.get(detachment.id).place if detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Тандем',
                    detachment.area.name if detachment.area else '-',
                    report.participants_number,
                    report.score,
                    place
                ))
                
    try:
        for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False):
            junior_detachment = detachments.get(participant.junior_detachment_id).first()
            if junior_detachment:
                for report in reports.filter(detachment_id=junior_detachment.id):
                    place = tandem_rankings.get(junior_detachment.id).place if junior_detachment.id in tandem_rankings else 'Ещё нет в рейтинге'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
                        junior_detachment.area.name if junior_detachment.area else '-',
                        report.participants_number,
                        report.score,
                        place
                    ))
    except Exception as e:
        print(f"Ошибка: {e}")
                
    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                place = individual_rankings.get(detachment.id).place if detachment.id in individual_rankings else 'Ещё нет в рейтинге'
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Дебют',
                    detachment.area.name if detachment.area else '-',
                    report.participants_number,
                    report.score,
                    place
                ))

    return rows


def get_q19_data(competition_id: int) -> list:
    tandem_rankings = {tr.detachment_id: tr.place for tr in Q19TandemRanking.objects.all()}
    individual_rankings = {ir.detachment_id: ir.place for ir in Q19Ranking.objects.all()}
    reports = Q19Report.objects.select_related('detachment').all()
    detachments = {d.id: d for d in Detachment.objects.select_related('region').all()}
    rows = []

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False).select_related('detachment', 'junior_detachment'):
        detachment = detachments.get(participant.detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                place = tandem_rankings.get(detachment.id, 'Ещё нет в рейтинге')
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Тандем',
                    detachment.area.name if detachment.area else '-',
                    report.safety_violations,
                    place
                ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=False).select_related('junior_detachment'):
        junior_detachment = detachments.get(participant.junior_detachment_id)
        if junior_detachment:
            for report in reports.filter(detachment_id=junior_detachment.id):
                place = tandem_rankings.get(junior_detachment.id, 'Ещё нет в рейтинге')
                rows.append((
                    junior_detachment.name,
                    junior_detachment.region.name if junior_detachment.region else '-',
                    'Тандем',
                    junior_detachment.area.name if junior_detachment.area else '-',
                    report.safety_violations,
                    place
                ))

    for participant in CompetitionParticipants.objects.filter(competition_id=competition_id, detachment__isnull=True):
        detachment = detachments.get(participant.junior_detachment_id)
        if detachment:
            for report in reports.filter(detachment_id=detachment.id):
                place = individual_rankings.get(detachment.id, 'Ещё нет в рейтинге')
                rows.append((
                    detachment.name,
                    detachment.region.name if detachment.region else '-',
                    'Дебют',
                    detachment.area.name if detachment.area else '-',
                    report.safety_violations,
                    place
                ))

    return rows


def get_membership_fee_data(competition_id: int) -> list:
    """Функция формирует данные для отчета q1."""
    # информация по отряду наставнику в тандеме
    detachment_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=False)
    ).select_related(
        'detachment__region',
        'detachment__sep_15_participants'
    ).prefetch_related(
        'detachment__q1report_detachment_reports',
        'detachment__q1tandemranking_main_detachment'
    ).values(
        'detachment__name',
        'detachment__region__name',
        'detachment__area__name',
        'detachment__sep_15_participants__members_number',
        'detachment__sep_15_participants__participants_number',
        'detachment__q1report_detachment_reports__score',
        'detachment__q1tandemranking_main_detachment__place',
    ).all()

    junior_detachment_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=False)
    ).select_related(
        'junior_detachment__region',
        'junior_detachment__sep_15_participants'
    ).prefetch_related(
        'junior_detachment__q1report_detachment_reports',
        'junior_detachment__q1tandemranking_junior_detachment'
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
        'junior_detachment__area__name',
        'junior_detachment__sep_15_participants__members_number',
        'junior_detachment__sep_15_participants__participants_number',
        'junior_detachment__q1report_detachment_reports__score',
        'junior_detachment__q1tandemranking_junior_detachment__place',
    ).all()

    # # информация по старт отряду в индивидуальных заявках
    individual_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=True)
    ).select_related(
        'junior_detachment__region',
        'junior_detachment__sep_15_participants'
    ).prefetch_related(
        'junior_detachment__q1report_detachment_reports',
        'junior_detachment__q1ranking'
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
        'junior_detachment__area__name',
        'junior_detachment__sep_15_participants__members_number',
        'junior_detachment__sep_15_participants__participants_number',
        'junior_detachment__q1report_detachment_reports__score',
        'junior_detachment__q1ranking__place',
    ).all()

    # Добавляем данные по отряду наставнику в тандеме
    rows = [
        (
            data.get('detachment__name', '-'),
            data.get('detachment__region__name', '-'),
            'Тандем',
            data.get('detachment__area__name', '-') or '-',
            data.get('detachment__sep_15_participants__participants_number'),
            data.get('detachment__sep_15_participants__members_number'),
            data.get('detachment__q1report_detachment_reports__score', '-') or '-',
            data.get('detachment__q1tandemranking_main_detachment__place', 'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in detachment_data
    ]

    # Добавляем данные по отряду старт в тандеме
    rows.extend([
        (
            data.get('junior_detachment__name', '-'),
            data.get('junior_detachment__region__name', '-'),
            'Тандем',
            data.get('junior_detachment__area__name', '-') or '-',
            data.get('junior_detachment__sep_15_participants__participants_number'),
            data.get('junior_detachment__sep_15_participants__members_number'),
            data.get('junior_detachment__q1report_detachment_reports__score', '-'
                     ) or '-',
            data.get(
                'junior_detachment__q1tandemranking_junior_detachment__place',
                'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in junior_detachment_data
    ])

    # Добавляем данные по отряду старт в индивидуальных заявках
    rows.extend([
        (
            data.get('junior_detachment__name', '-'),
            data.get('junior_detachment__region__name', '-'),
            'Дебют',
            data.get('junior_detachment__area__name', '-') or '-',
            data.get('junior_detachment__sep_15_participants__participants_number'),
            data.get('junior_detachment__sep_15_participants__members_number'),
            data.get('junior_detachment__q1report_detachment_reports__score', '-'
                     ) or '-',
            data.get(
                'junior_detachment__q1ranking__place',
                'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in individual_data
    ])

    return rows


def get_attributes_of_uniform_data(competition_id):
    detachment_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=False)
    ).select_related(
        'detachment__region'
    ).prefetch_related(
        'detachment__q20report_detachment_reports',
        'detachment__q20tandemranking_main_detachment'
    ).values(
        'detachment__name',
        'detachment__region__name',
        'detachment__area__name',
        'detachment__q20report_detachment_reports__score',
        'detachment__q20report_detachment_reports__link_emblem',
        'detachment__q20report_detachment_reports__link_emblem_img',
        'detachment__q20report_detachment_reports__link_flag',
        'detachment__q20report_detachment_reports__link_flag_img',
        'detachment__q20report_detachment_reports__link_banner',
        'detachment__q20report_detachment_reports__link_banner_img',
        'detachment__q20report_detachment_reports__is_verified',
        'detachment__q20tandemranking_main_detachment__place',
    ).all()

    junior_detachment_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=False)
    ).select_related(
        'junior_detachment__region'
    ).prefetch_related(
        'junior_detachment__q20report_detachment_reports',
        'junior_detachment__q20tandemranking_junior_detachment'
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
        'junior_detachment__area__name',
        'junior_detachment__q20report_detachment_reports__score',
        'junior_detachment__q20report_detachment_reports__link_emblem',
        'junior_detachment__q20report_detachment_reports__link_emblem_img',
        'junior_detachment__q20report_detachment_reports__link_flag',
        'junior_detachment__q20report_detachment_reports__link_flag_img',
        'junior_detachment__q20report_detachment_reports__link_banner',
        'junior_detachment__q20report_detachment_reports__link_banner_img',
        'junior_detachment__q20report_detachment_reports__is_verified',
        'junior_detachment__q20tandemranking_junior_detachment__place',
    ).all()

    # # информация по старт отряду в индивидуальных заявках
    individual_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=True)
    ).select_related(
        'junior_detachment__region'
    ).prefetch_related(
        'junior_detachment__q20report_detachment_reports',
        'junior_detachment__q20ranking'
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
        'junior_detachment__area__name',
        'junior_detachment__q20report_detachment_reports__score',
        'junior_detachment__q20report_detachment_reports__link_emblem',
        'junior_detachment__q20report_detachment_reports__link_emblem_img',
        'junior_detachment__q20report_detachment_reports__link_flag',
        'junior_detachment__q20report_detachment_reports__link_flag_img',
        'junior_detachment__q20report_detachment_reports__link_banner',
        'junior_detachment__q20report_detachment_reports__link_banner_img',
        'junior_detachment__q20report_detachment_reports__is_verified',
        'junior_detachment__q20ranking__place',
    ).all()

    # Добавляем данные по отряду наставнику в тандеме
    rows = [
        (
            data.get('detachment__name', '-'),
            data.get('detachment__region__name', '-'),
            'Тандем',
            data.get('detachment__area__name', '-') or '-',
            data.get('detachment__q20report_detachment_reports__link_emblem', '-') or '-',
            data.get('detachment__q20report_detachment_reports__link_emblem_img', '-') or '-',
            data.get('detachment__q20report_detachment_reports__link_flag', '-') or '-',
            data.get('detachment__q20report_detachment_reports__link_flag_img', '-') or '-',
            data.get('detachment__q20report_detachment_reports__link_banner', '-') or '-',
            data.get('detachment__q20report_detachment_reports__link_banner_img', '-') or '-',
            data.get('detachment__q20report_detachment_reports__is_verified', 'False') or 'False',
            data.get('detachment__q20report_detachment_reports__score', '-') or '-',
            data.get('detachment__q20tandemranking_main_detachment__place', 'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in detachment_data
    ]

    # Добавляем данные по отряду старт в тандеме
    rows.extend([
        (
            data.get('junior_detachment__name', '-'),
            data.get('junior_detachment__region__name', '-'),
            'Тандем',
            data.get('junior_detachment__area__name', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_emblem', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_emblem_img', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_flag', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_flag_img', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_banner', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_banner_img', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__is_verified', 'False') or 'False',
            data.get('junior_detachment__q20report_detachment_reports__score', '-'
                     ) or '-',
            data.get(
                'junior_detachment__q20tandemranking_junior_detachment__place',
                'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in junior_detachment_data
    ])

    # Добавляем данные по отряду старт в индивидуальных заявках
    rows.extend([
        (
            data.get('junior_detachment__name', '-'),
            data.get('junior_detachment__region__name', '-'),
            'Дебют',
            data.get('junior_detachment__area__name', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_emblem', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_emblem_img', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_flag', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_flag_img', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_banner', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__link_banner_img', '-') or '-',
            data.get('junior_detachment__q20report_detachment_reports__is_verified', 'False') or 'False',
            data.get('junior_detachment__q20report_detachment_reports__score', '-'
                     ) or '-',
            data.get(
                'junior_detachment__q20ranking__place',
                'Ещё нет в рейтинге') or 'Ещё не подал отчет'
        ) for data in individual_data
    ])

    return rows
