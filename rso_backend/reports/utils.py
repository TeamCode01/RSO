from urllib.parse import urljoin

from django.db import connection
from django.db.models import Q
from django.conf import settings

from collections import defaultdict
from typing import List, Tuple

from api.utils import get_user_detachment, get_user_detachment_position
from competitions.constants import SOLO_RANKING_MODELS, TANDEM_RANKING_MODELS
from competitions.models import (CompetitionParticipants, OverallRanking,
                                 OverallTandemRanking, Q5DetachmentReport, Q5EducatedParticipant, Q5TandemRanking,
                                 Q5Ranking)
from headquarters.count_hq_members import count_headquarter_participants
from headquarters.models import UserDetachmentPosition, Detachment
from questions.models import Attempt
from users.models import RSOUser, UserRegion
from reports.constants import COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY
from users.serializers import UserIdRegionSerializer


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
            users_to_append = process_detachment_users(
                participant_entry.detachment,
                'Наставник',
                'Тандем'
            )
            competition_members_data.append((participant_entry.detachment, users_to_append))

        if participant_entry.junior_detachment:
            nomination = 'Тандем' if participant_entry.detachment else 'Дебют'
            users_to_append = process_detachment_users(
                participant_entry.junior_detachment,
                'Младший отряд',
                nomination
            )
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
        detachment.participants_count = count_headquarter_participants(detachment)
        detachment.status = 'Младший отряд'
        detachment.nomination = 'Дебют'
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
        junior_detachment.participants_count = count_headquarter_participants(junior_detachment)
        junior_detachment.status = 'Младший отряд'
        junior_detachment.nomination = 'Тандем'
        junior_detachment.places = []
        detachment = participant_entry.detachment
        detachment.participants_count = count_headquarter_participants(detachment)
        detachment.status = 'Наставник'
        detachment.nomination = 'Тандем'
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
    queryset = UserRegion.objects.all()
    queryset = queryset.order_by('reg_region')
    serializer = UserIdRegionSerializer(queryset, many=True)

    rows = []
    for item in serializer.data:
        row = (list(dict(item).values()))
        rows.append(row)
    return rows


def get_commander_school_data(competition_id: int) -> list:
    # информация по отряду наставнику в тандеме
    detachment_data = CompetitionParticipants.objects.filter(
        Q(competition_id=competition_id) & Q(detachment__isnull=False)
    ).select_related(
        'detachment'
    ).prefetch_related(
        'detachment__region',
    ).values(
        'detachment__name',
        'detachment__region__name',
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
        'junior_detachment'
    ).prefetch_related(
        'junior_detachment__region',
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
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
        'junior_detachment'
    ).prefetch_related(
        'junior_detachment__region',
    ).values(
        'junior_detachment__name',
        'junior_detachment__region__name',
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
            'Да' if data.get('detachment__q2detachmentreport_detachment_reports__commander_achievement') else 'Нет',
            'Да' if data.get('detachment__q2detachmentreport_detachment_reports__commissioner_achievement') else 'Нет',
            data.get('detachment__q2detachmentreport_detachment_reports__commander_link', '-') or '-',
            data.get('detachment__q2detachmentreport_detachment_reports__commissioner_link', '-') or '-',
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
                    document_url = f'https://{settings.DEFAULT_SITE_URL}/{edu_participant.document.url}' if edu_participant.document else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Тандем',
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
                    document_url = f'https://{settings.DEFAULT_SITE_URL}/{edu_participant.document.url}' if edu_participant.document else '-'
                    rows.append((
                        junior_detachment.name,
                        junior_detachment.region.name if junior_detachment.region else '-',
                        'Тандем',
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
                    document_url = f'https://{settings.DEFAULT_SITE_URL}/{edu_participant.document.url}' if edu_participant.document else '-'
                    rows.append((
                        detachment.name,
                        detachment.region.name if detachment.region else '-',
                        'Дебют',
                        edu_participant.name,
                        document_url,
                        'Верифицирован' if edu_participant.is_verified else 'Не верифицирован',
                        place
                    ))

    return rows
