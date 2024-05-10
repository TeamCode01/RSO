from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, List, Tuple

from api.utils import get_user_detachment, get_user_detachment_position
from competitions.constants import SOLO_RANKING_MODELS, TANDEM_RANKING_MODELS
from competitions.models import (CompetitionParticipants, OverallRanking,
                                 OverallTandemRanking)
from headquarters.count_hq_members import count_headquarter_participants
from headquarters.models import UserDetachmentPosition

if TYPE_CHECKING:
    from headquarters.models import Detachment
    from questions.models import Attempt
    from users.models import RSOUser


def enumerate_attempts(results: List[Attempt]) -> list:
    user_attempts = defaultdict(int)
    enumerated_results = []

    for result in results:
        user_attempts[result.user_id] += 1
        result.attempt_number = user_attempts[result.user_id]
        result.detachment = get_user_detachment(result.user)
        result.detachment_position = get_user_detachment_position(result.user)
        enumerated_results.append(result)

    return enumerated_results


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
    return competition_members_data
