import logging
from collections import Counter
from datetime import date
from typing import List

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

from api.constants import Q6_BLOCK_MODELS
from competitions.constants import COUNT_PLACES_DEADLINE
from competitions.models import (CompetitionParticipants, July15Participant, OverallRanking,
                                 OverallTandemRanking, Q1Ranking, Q1Report,
                                 Q2DetachmentReport, Q2Ranking,
                                 Q2TandemRanking, Q3Ranking, Q3TandemRanking,
                                 Q4Ranking, Q4TandemRanking,
                                 Q5DetachmentReport, Q5EducatedParticipant,
                                 Q5Ranking, Q5TandemRanking,
                                 Q6DetachmentReport, Q6Ranking,
                                 Q6TandemRanking, Q7Ranking, Q7Report,
                                 Q7TandemRanking, Q13EventOrganization,
                                 Q14DetachmentReport, Q14LaborProject,
                                 Q14Ranking, Q14TandemRanking,
                                 Q15DetachmentReport, Q15GrantWinner, Q15Rank,
                                 Q15TandemRank, Q16Report, Q17DetachmentReport,
                                 Q17EventLink, Q17Ranking, Q17TandemRanking,
                                 Q18DetachmentReport, Q18Ranking,
                                 Q18TandemRanking, Q19Ranking, Q19Report,
                                 Q19TandemRanking, DemonstrationBlock, PatrioticActionBlock, SafetyWorkWeekBlock,
                                 CommanderCommissionerSchoolBlock, WorkingSemesterOpeningBlock, CreativeFestivalBlock,
                                 ProfessionalCompetitionBlock, SpartakiadBlock)
from competitions.utils import (assign_ranks, find_second_element_by_first,
                                get_place_q2, is_main_detachment,
                                tandem_or_start, round_math)
from headquarters.models import Detachment, UserDetachmentPosition
from questions.models import Attempt

logger = logging.getLogger('tasks')


def calculate_overall_rankings(solo_ranking_models, tandem_ranking_models, competition_id):
    logger.info('Удаляем записи из OverallTandemRanking, OverallTanking')
    OverallTandemRanking.objects.all().delete()
    OverallRanking.objects.all().delete()
    solo_entries = CompetitionParticipants.objects.filter(
        competition_id=competition_id,
        junior_detachment__isnull=False,
        detachment__isnull=True
    )
    tandem_entries = CompetitionParticipants.objects.filter(
        competition_id=competition_id,
        junior_detachment__isnull=False,
        detachment__isnull=False
    )
    solo_worst_places = {}
    tandem_worst_places = {}

    for model in solo_ranking_models:
        worst_entry = model.objects.filter(competition_id=competition_id).order_by('-place').first()
        solo_worst_places[model] = worst_entry.place + 1 if worst_entry else 1

    for model in tandem_ranking_models:
        worst_entry = model.objects.filter(competition_id=competition_id).order_by('-place').first()
        tandem_worst_places[model] = worst_entry.place + 1 if worst_entry else 1

    solo_rankings = []
    tandem_rankings = []

    for solo_entry in solo_entries:
        solo_entry_place = 0
        detachment = solo_entry.junior_detachment

        for model in solo_ranking_models:
            try:
                ranking = model.objects.get(
                    competition_id=competition_id, detachment=detachment
                )
                solo_entry_place += ranking.place
            except model.DoesNotExist:
                solo_entry_place += solo_worst_places[model]

        solo_rankings.append({'detachment': detachment, 'place': solo_entry_place})

    for tandem_entry in tandem_entries:
        tandem_entry_place = 0
        detachment = tandem_entry.detachment
        junior_detachment = tandem_entry.junior_detachment
        for model in tandem_ranking_models:
            try:
                ranking = model.objects.get(
                    competition_id=competition_id,
                    detachment=detachment,
                    junior_detachment=junior_detachment
                )
                tandem_entry_place += ranking.place
            except model.DoesNotExist:
                tandem_entry_place += tandem_worst_places[model]
        tandem_rankings.append(
            {
                'detachment': detachment,
                'junior_detachment': junior_detachment,
                'place': tandem_entry_place
            }
        )

    solo_rankings.sort(key=lambda x: x['place'])
    current_place = 1
    last_place = 0
    previous_places_sum = None

    for solo_ranking_entry in solo_rankings:
        if solo_ranking_entry['place'] != previous_places_sum:
            current_place = last_place + 1

        OverallRanking.objects.create(
            competition_id=competition_id,
            detachment=solo_ranking_entry['detachment'],
            places_sum=solo_ranking_entry['place'],
            place=current_place
        )
        last_place = current_place
        previous_places_sum = solo_ranking_entry['place']

    tandem_rankings.sort(key=lambda x: x['place'])
    current_place = 1
    last_place = 0
    previous_places_sum = None

    for tandem_ranking_entry in tandem_rankings:
        if tandem_ranking_entry['place'] != previous_places_sum:
            current_place = last_place + 1

        OverallTandemRanking.objects.create(
            competition_id=competition_id,
            detachment=tandem_ranking_entry['detachment'],
            junior_detachment=tandem_ranking_entry['junior_detachment'],
            places_sum=tandem_ranking_entry['place'],
            place=current_place
        )
        last_place = current_place
        previous_places_sum = tandem_ranking_entry['place']


def calculate_q13_place(objects: list[Q13EventOrganization]) -> int:
    """
    Спортивных мероприятий указано 1 и более - 1 балл, если не указано ни
    одно спортивное мероприятие - 0 баллов.
    Интеллектуальных мероприятий указано 1 и более - 1 балл, если не указано
    ни одно интеллектуальное мероприятие - 0 баллов.
    Творческих мероприятий указано 1 и более - 1 балл, если не указано ни одно
    творческое мероприятие - 0 баллов.
    Волонтерских мероприятий указано 5 и более - 1 балл, от 0 до 4 - 0 баллов.
    Внутренних мероприятий указано 15 и более - 1 балл, от 0 до 14 - 0 баллов.
    Далее баллы по всем (5 шт) видам мероприятий суммируются
    и определяется место.

    Итоговое место:
    5 баллов - 1 место
    4 балла - 2 место
    3 балла - 3 место
    2 балла - 4 место
    1 балл - 5 место
    0 баллов (если указали только 2 волонтерских и 12 внутренних) - 6 место.
    """
    place = 6
    calculations = {
        'Спортивное': 0,
        'Интеллектуальное': 0,
        'Творческое': 0,
        'Волонтерское': 0,
        'Внутреннее': 0
    }
    for obj in objects:
        event_type = obj.event_type
        calculations[event_type] += 1
    if calculations['Спортивное'] > 0:
        place -= 1
    if calculations['Интеллектуальное'] > 0:
        place -= 1
    if calculations['Творческое'] > 0:
        place -= 1
    if calculations['Волонтерское'] > 4:
        place -= 1
    if calculations['Волонтерское'] > 14:
        place -= 1
    return place


def calculate_q14_place(competition_id):

    today = date.today()
    cutoff_date = date(2024, 6, 15)

    logger.info(f'Сегодняшняя дата: {today}')
    check_date = today <= cutoff_date
    if check_date:
        logger.info(
            f'Сегодняшняя дата {today} меньше '
            f'cutoff date: {cutoff_date}. '
            f'Обновляем кол-во участников.'
        )

    detachment_reports = Q14DetachmentReport.objects.filter(
        competition_id=competition_id,
        q14_labor_project__is_verified=True
    ).distinct()

    start_list = []
    tandem_list = []
    tandem_participants_list = []
    """
    Проходим циклом по всем отчетам
    и записываем число участников отрядов до 15.06.2024
    в поле отчёта.
    """
    for report in detachment_reports:
        if check_date:
            is_tandem = tandem_or_start(
                competition=competition_id,
                detachment=report.detachment.id,
                competition_model=CompetitionParticipants
            )
            if not is_tandem:
                start_list.append(report)
                calculate_june_detachment_members(
                    entry=report,
                    partner_entry=None
                )
            if is_tandem:
                tandem_list.append(report)
                is_main = is_main_detachment(
                    competition_id=competition_id,
                    detachment_id=report.detachment.id,
                    competition_model=CompetitionParticipants

                )
                if is_main:
                    junior_detachment = CompetitionParticipants.objects.filter(
                        competition_id=competition_id,
                        detachment_id=report.detachment.id
                    ).first().junior_detachment
                    tandem_participants_list.append((
                        report.detachment.id, junior_detachment.id
                    ))
                    try:
                        partner_entry = Q14DetachmentReport.objects.filter(
                            competition_id=competition_id,
                            detachment_id=junior_detachment.id
                        ).first()

                    except Q14DetachmentReport.DoesNotExist:
                        partner_entry = None
                    calculate_june_detachment_members(
                        entry=report,
                        partner_entry=partner_entry
                    )

                if not is_main:
                    main_detachment = CompetitionParticipants.objects.filter(
                        competition_id=competition_id,
                        junior_detachment=report.detachment.id
                    ).first().detachment
                    try:
                        partner_entry = Q14DetachmentReport.objects.filter(
                            competition_id=competition_id,
                            detachment_id=main_detachment.id
                        ).first()

                    except Q14DetachmentReport.DoesNotExist:
                        partner_entry = None
                    calculate_june_detachment_members(
                        entry=report,
                        partner_entry=partner_entry
                    )
                    tandem_participants_list.append((
                        main_detachment.id, report.detachment.id
                    ))
                tandem_participants = set(tandem_participants_list)
        verified_projects = (Q14LaborProject.objects.filter(
            detachment_report=report,
            is_verified=True
        ))
        result_amount = sum([entry.amount for entry in verified_projects])
        report.score = (
            result_amount / report.june_15_detachment_members
        )
        report.save()
    data_list = []
    data_dict = {}
    for entry in start_list:
        if entry.detachment.id not in data_dict:
            score = entry.score
        else:
            score = data_dict[entry.detachment.id] + entry.score

        data_list += [(entry.detachment.id, score)]
        score = 0
    ranked_start = assign_ranks(data_list)
    Q14Ranking.objects.all().delete()
    for item in ranked_start:
        Q14Ranking.objects.create(
            competition_id=competition_id,
            detachment_id=item[0],
            place=item[1]
        )
    data_list.clear()
    data_dict.clear()
    for entry in tandem_list:
        if entry.detachment.id not in data_dict:
            data_dict[entry.detachment.id] = entry.score
        else:
            score = data_dict[entry.detachment.id] + entry.score
            data_dict[entry.detachment.id] = score
            score = 0
    for item in tandem_participants:
        score_main = data_dict.pop(item[0], 0)
        score_junior = data_dict.pop(item[1], 0)
        result = score_main + score_junior
        data_dict[item[0]] = result
        data_list += [(item[0], result)]
    ranked_tandem = assign_ranks(data_list)
    Q14TandemRanking.objects.all().delete()
    for item in ranked_tandem:
        for partnership in tandem_participants:
            if item[0] == partnership[0]:
                Q14TandemRanking.objects.get_or_create(
                    competition_id=competition_id,
                    detachment_id=partnership[0],
                    junior_detachment_id=partnership[1],
                    place=item[1]
                )


def calculate_q17_place(competition_id):

    logger.info(f'Начинаем считать места по 17 показателю {competition_id}')
    start_list = []
    tandem_dict_count = {}
    tandem_dict = {}
    tandem_dict_united = {}
    tandem_list_united = []
    detachment_reports = Q17DetachmentReport.objects.filter(
        competition_id=competition_id,
    )
    """
    Проходим циклом по всем отчетам и считаем кол-во
    верифицированных публикаций.
    source_count_dict = {id отчета: кол-во верифицированных отчетов}
    """
    for entry in detachment_reports:
        source_count_dict = dict(Counter(Q17EventLink.objects.filter(
            detachment_report=entry,
            is_verified=True
        ).all().values_list('detachment_report_id', flat=True)))

        """
        В цикле проверяем является ли отчет отряда тандемом.
        Если Стандарт - добавляем в список
        start_list = [(id отряда, кол-во верифицированных отчетов)].
        Если Тандем - добавляем в список
        tandem_list = [(id отряда, кол-во верифицированных отчетов)]
        и добавляем в словарь
        tandem_dict_count = {id отряда: кол-во верифицированных отчетов}.
        Список start_list далее будет преобразован в ranked_start.
        ranked_start - [(id отряда, место)]. Цикл по ranked_start
        создаст записи в Q17Ranking.
        """

        for report_id, verified_count in source_count_dict.items():
            detachment_id = Q17DetachmentReport.objects.get(
                id=report_id,
                competition_id=competition_id
            ).detachment.id
            is_tandem = tandem_or_start(
                competition=competition_id,
                detachment=detachment_id,
                competition_model=CompetitionParticipants
            )
            if not is_tandem:
                start_list.append((detachment_id, verified_count))
            if is_tandem:
                tandem_dict_count[detachment_id] = verified_count
    """
    Проходим циклом по словарю тандемов, определяем main_detachment_id
    и junior_detachment_id. Суммируем количество отчётов и записываем
    в новый словарь
    tandem_dict_united = {id отряда-наставника: сумма отчетов наставника и младшего отрядов}.
    """
    for detachment_id, verified_count in tandem_dict_count.items():
        is_main = is_main_detachment(
            competition_id=competition_id,
            detachment_id=detachment_id,
            competition_model=CompetitionParticipants
        )
        if is_main:
            junior_detachment_id = CompetitionParticipants.objects.filter(
                competition_id=competition_id,
                detachment_id=detachment_id
            ).first().junior_detachment.id

            tandem_dict[detachment_id] = junior_detachment_id
            junior_count = tandem_dict_count.get(junior_detachment_id, 0)

            tandem_dict_united[detachment_id] = verified_count + junior_count
        else:
            main_detachment_id = CompetitionParticipants.objects.filter(
                competition_id=competition_id,
                junior_detachment=detachment_id
            ).first().detachment_id
            tandem_dict[main_detachment_id] = detachment_id
            main_count = tandem_dict_count.get(main_detachment_id, 0)
            tandem_dict_united[main_detachment_id] = (
                verified_count + main_count
            )

    """
    Формируем из словаря tandem_dict_united словарь кортежей, который
    преобразуем в ranked_tandem = [(id отряда, место)].
    Элементы из ranked_tandem будут записаны в Q17TandemRanking.
    """
    for main_detachment_id, verified_count in tandem_dict_united.items():
        tandem_list_united.append((main_detachment_id, verified_count))
    ranked_start = assign_ranks(start_list)
    ranked_tandem = assign_ranks(tandem_list_united)

    Q17Ranking.objects.all().delete()
    Q17TandemRanking.objects.all().delete()

    for id, place in ranked_start:
        Q17Ranking.objects.create(
            competition_id=competition_id,
            detachment_id=id,
            place=place
        )
    for id, place in ranked_tandem:
        Q17TandemRanking.objects.get_or_create(
            competition_id=competition_id,
            junior_detachment_id=tandem_dict[id],
            detachment_id=id,
            place=place
        )
    logger.info(f'Посчитали места по 17 показателю {competition_id}')


def calculate_q18_place(competition_id):
    today = date.today()
    cutoff_date = date(2024, 6, 15)

    logger.info(f'Сегодняшняя дата: {today}')

    verified_entries = Q18DetachmentReport.objects.filter(is_verified=True, competition_id=competition_id)
    logger.info(
        f'Получили верифицированные отчеты: {verified_entries}')

    solo_entries = []
    tandem_entries = []

    for entry in verified_entries:
        participants_entry = CompetitionParticipants.objects.filter(
            junior_detachment=entry.detachment
        ).first()
        partner_entry = None
        if participants_entry and not participants_entry.detachment:
            category = solo_entries
            logger.info(f'Отчет {entry} - соло участник')
        elif participants_entry:
            logger.info(f'Отчет {entry} - тандем участник')
            category = tandem_entries
            if participants_entry:
                partner_entry = Q18DetachmentReport.objects.filter(
                    detachment=participants_entry.detachment,
                    competition_id=competition_id,
                    is_verified=True
                ).first()
                if partner_entry:
                    logger.info(
                        f'Для отчета {entry} найден '
                        f'партнерский отчет: {partner_entry}'
                    )
        elif not participants_entry:
            participants_entry = CompetitionParticipants.objects.filter(
                detachment=entry.detachment
            ).first()
            partner_entry = entry
            if participants_entry:
                logger.info(f'Отчет {entry} - тандем участник')
                category = tandem_entries
                entry = Q18DetachmentReport.objects.filter(
                    detachment=participants_entry.junior_detachment,
                    competition_id=competition_id,
                    is_verified=True
                ).first()
                if entry:
                    logger.info(
                        f'Для отчета {partner_entry} найден '
                        f'партнерский отчет: {entry}'
                    )
                else:
                    logger.info(
                        f'Для отчета {partner_entry} не найден '
                        f'партнерский отчет'
                    )
        if today <= cutoff_date:
            logger.info(
                f'Сегодняшняя дата {today} меньше '
                f'cutoff date: {cutoff_date}. '
                f'Обновляем кол-во участников.'
            )
            if entry:
                calculate_june_detachment_members(entry, partner_entry)

        if entry:
            entry.score = entry.participants_number / entry.june_15_detachment_members
            entry.save()

        if partner_entry and entry:
            partner_entry.score = partner_entry.participants_number / partner_entry.june_15_detachment_members
            partner_entry.save()
            tuple_to_append = (
                entry, partner_entry, entry.score + partner_entry.score)
            if tuple_to_append not in category:
                print(f'В категорию {"tandem entries" if category is tandem_entries else "solo entries"} добавили {tuple_to_append}')
                category.append(tuple_to_append)
        elif entry and not partner_entry:
            if category is tandem_entries:
                elder_detachment = CompetitionParticipants.objects.filter(
                    junior_detachment=entry.detachment
                ).first().detachment
                dummy_entry = Q18DetachmentReport(
                    detachment=elder_detachment,
                    score=0
                )
                print(
                    f'В категорию {"tandem entries" if category is tandem_entries else "solo entries"} добавили ({entry}, {dummy_entry}, {entry.score})'
                )
                category.append((entry, dummy_entry, entry.score))
            else:
                print(
                    f'В категорию {"tandem entries" if category is tandem_entries else "solo entries"} добавили ({entry}, {entry.score})'
                )
                category.append((entry, entry.score))
        elif partner_entry and not entry:
            dummy_junior_detachment = CompetitionParticipants.objects.filter(
                detachment=partner_entry.detachment
            ).first().junior_detachment
            dummy_entry = Q18DetachmentReport(
                detachment=dummy_junior_detachment,
                score=0
            )
            print(f'В категорию {"tandem entries" if category is tandem_entries else "solo entries"} добавили ({dummy_entry}, {partner_entry}, {partner_entry.score})')
            category.append((dummy_entry, partner_entry, partner_entry.score))

    if solo_entries:
        logger.info('Есть записи для соло-участников. Удаляем записи из таблицы Q18 Ranking')
        Q18Ranking.objects.all().delete()

        solo_entries.sort(key=lambda entry: entry[1], reverse=True)
        place = 1
        previous_score = None
        previous_place = 0

        for entry in solo_entries:
            if entry[1] != previous_score:
                place = previous_place + 1
            logger.info(f'Отчет {entry[0]} занимает {place} место')
            Q18Ranking.objects.create(
                detachment=entry[0].detachment,
                place=place,
                competition_id=competition_id
            )
            previous_score = entry[1]
            previous_place = place

    if tandem_entries:
        logger.info('Есть записи для тандем-участников. Удаляем записи из таблицы Q18 TandemRanking')
        Q18TandemRanking.objects.all().delete()

        tandem_entries.sort(key=lambda entry: entry[2], reverse=True)
        place = 1
        previous_score = None
        previous_place = 0

        for entry in tandem_entries:
            if entry[2] != previous_score:
                place = previous_place + 1
            logger.info(f'Отчеты {entry[0]} и {entry[1]} занимают {place} место')
            Q18TandemRanking.objects.create(
                junior_detachment=entry[0].detachment,
                detachment=entry[1].detachment,
                place=place,
                competition_id=competition_id
            )
            previous_score = entry[2]
            previous_place = place


def calculate_q6_place(competition_id):
    today = date.today()
    cutoff_date = date(2024, 6, 15)

    logger.info(f'Сегодняшняя дата: {today}')

    verified_entries = Q6DetachmentReport.objects.filter(competition_id=competition_id)
    logger.info(
        f'Получили отчеты: {verified_entries.count()}'
    )

    solo_entries = []
    tandem_entries = []

    for entry in verified_entries:
        participants_entry = CompetitionParticipants.objects.filter(
            junior_detachment=entry.detachment
        ).first()
        partner_entry = None
        if participants_entry and not participants_entry.detachment:
            category = solo_entries
            logger.info(f'Отчет {entry} - соло участник')
        elif participants_entry:
            logger.info(f'Отчет {entry} - тандем участник')
            category = tandem_entries
            if participants_entry:
                partner_entry = Q6DetachmentReport.objects.filter(
                    detachment=participants_entry.detachment,
                    competition_id=competition_id,
                ).first()
                if partner_entry:
                    logger.info(
                        f'Для отчета {entry} найден '
                        f'партнерский отчет: {partner_entry}'
                    )
                else:
                    partner_entry = Q6DetachmentReport(
                        competition_id=settings.COMPETITION_ID,
                        detachment=participants_entry.detachment,

                    )
                    logger.info(
                        f'Для отчета {entry} НЕ найден '
                        f'партнерский отчет. Создали дефолтный: {partner_entry}'
                    )
        elif not participants_entry:
            participants_entry = CompetitionParticipants.objects.filter(
                detachment=entry.detachment
            ).first()
            partner_entry = entry
            if participants_entry:
                category = tandem_entries
                entry = Q6DetachmentReport.objects.filter(
                    detachment=participants_entry.junior_detachment,
                    competition_id=competition_id,
                ).first()
                if entry:
                    logger.info(
                        f'Для отчета {partner_entry} найден '
                        f'партнерский отчет: {entry}'
                    )
                else:
                    partner_entry = Q6DetachmentReport(
                        competition_id=settings.COMPETITION_ID,
                        detachment=participants_entry.junior_detachment
                    )
                    logger.info(
                        f'Для отчета {entry} НЕ найден '
                        f'партнерский отчет. Создали дефолтный: {partner_entry}'
                    )


        calculate_april_detachment_members(entry, partner_entry)

        working_semester_opening_participants = 0
        patriotic_action_participants = 0
        first_may_demonstration_participants = 0
        if entry:
            try:
                if entry.working_semester_opening_block.is_verified:
                    working_semester_opening_participants = (
                        entry.working_semester_opening_block.working_semester_opening_participants
                    )
            except ObjectDoesNotExist:
                working_semester_opening_participants = 0
            try:
                if entry.patriotic_action_block.is_verified:
                    patriotic_action_participants = (
                        entry.patriotic_action_block.patriotic_action_participants
                    )
            except ObjectDoesNotExist:
                patriotic_action_participants = 0
            try:
                if entry.demonstration_block.is_verified:
                    first_may_demonstration_participants = (
                        entry.demonstration_block.first_may_demonstration_participants
                    )
            except ObjectDoesNotExist:
                first_may_demonstration_participants = 0
            entry_participants_number = (
                    working_semester_opening_participants +
                    patriotic_action_participants +
                    first_may_demonstration_participants
            )
            entry.score = round_math((entry_participants_number / entry.april_1_detachment_members), 2)
            entry.save()

        if partner_entry and entry:
            logger.info(f'ПЕРВОЕ УСЛОВИЕ ДЛЯ {partner_entry.detachment} и {entry.detachment}')
            working_semester_opening_participants = 0
            patriotic_action_participants = 0
            first_may_demonstration_participants = 0
            if entry:
                try:
                    if partner_entry.working_semester_opening_block.is_verified:
                        working_semester_opening_participants = (
                            partner_entry.working_semester_opening_block.working_semester_opening_participants
                        )
                except ObjectDoesNotExist:
                    working_semester_opening_participants = 0
                try:
                    if partner_entry.patriotic_action_block.is_verified:
                        patriotic_action_participants = (
                            partner_entry.patriotic_action_block.patriotic_action_participants
                        )
                except ObjectDoesNotExist:
                    patriotic_action_participants = 0
                try:
                    if partner_entry.demonstration_block.is_verified:
                        first_may_demonstration_participants = (
                            partner_entry.demonstration_block.first_may_demonstration_participants
                        )
                except ObjectDoesNotExist:
                    first_may_demonstration_participants = 0

            partner_entry_participants_number = (
                    working_semester_opening_participants +
                    patriotic_action_participants +
                    first_may_demonstration_participants
            )
            partner_entry.score = round_math((partner_entry_participants_number / partner_entry.april_1_detachment_members), 2)
            partner_entry.save()

            verified = False

            try:
                if entry.working_semester_opening_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.patriotic_action_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.demonstration_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.safety_work_week_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.commander_commissioner_school_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.creative_festival_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.professional_competition_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.spartakiad_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.working_semester_opening_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.patriotic_action_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.demonstration_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.safety_work_week_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.commander_commissioner_school_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.creative_festival_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.professional_competition_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.spartakiad_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            if verified:
                logger.info(f'Для {entry.detachment} и {partner_entry.detachment} найден верифицированный блок, сохраняем {entry.score + partner_entry.score} очков')
                tuple_to_append = (entry, partner_entry, round_math(entry.score + partner_entry.score), 2)
                if tuple_to_append not in category:
                    category.append(tuple_to_append)
        elif entry and not partner_entry and category == solo_entries:
            new_entry = Q6DetachmentReport.objects.filter(detachment=entry.detachment).first()
            if new_entry:
                logger.info(f'нашли new_entry {new_entry}')
                entry = new_entry
            else:
                logger.info('НЕ нашли new_entry')
            logger.info(f'ВТОРОЕ УСЛОВИЕ ДЛЯ')
            logger.info(f'{entry.detachment}')
            logger.info(f'{entry}')
            verified = False
            try:
                if entry.working_semester_opening_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.patriotic_action_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.demonstration_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.safety_work_week_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                logger.info(
                    f'ДЛЯ {entry.detachment} ПРОВЕРЯЕМ commander_commissioner_school_block '
                    f'IS_VERIFIED?: {entry.commander_commissioner_school_block.is_verified}'
                )
                if entry.commander_commissioner_school_block.is_verified:
                    logger.info('YES')
                    verified = True
            except (ObjectDoesNotExist, AttributeError) as e:
                logger.info(f'NO: {e}')
                pass

            try:
                if entry.creative_festival_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.professional_competition_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if entry.spartakiad_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            if verified:
                logger.info(f'Для {entry.detachment} найден верифицированный блок, сохраняем {entry.score} очков')
                category.append((round_math(entry, entry.score), 2))
            else:
                logger.info(f'Для {entry.detachment} не найден верифицированный блок, пропускаем')
        elif partner_entry and not entry and category == solo_entries:
            new_entry = Q6DetachmentReport.objects.filter(detachment=partner_entry.detachment).first()
            if new_entry:
                logger.info(f'нашли new_entry {new_entry}')
                partner_entry = new_entry
            else:
                logger.info('НЕ нашли new_entry')
            logger.info(f'ТРЕТЬЕ УСЛОВИЕ ДЛЯ')
            logger.info(f'{partner_entry.detachment}')
            verified = False
            try:
                if partner_entry.working_semester_opening_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.patriotic_action_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.demonstration_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.safety_work_week_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                logger.info(
                    f'ДЛЯ {partner_entry.detachment} ПРОВЕРЯЕМ commander_commissioner_school_block '
                    f'IS_VERIFIED?: {partner_entry.commander_commissioner_school_block.is_verified}'
                )
                if partner_entry.commander_commissioner_school_block.is_verified:
                    logger.info('YES')
                    verified = True
            except (ObjectDoesNotExist, AttributeError) as e:
                logger.info(f'NO: {e}')
                pass

            try:
                if partner_entry.creative_festival_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.professional_competition_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            try:
                if partner_entry.spartakiad_block.is_verified:
                    verified = True
            except (ObjectDoesNotExist, AttributeError):
                pass

            if verified:
                logger.info(f'Для {partner_entry.detachment} найден верифицированный блок, сохраняем {partner_entry.score} очков')
                category.append((round_math(partner_entry, partner_entry.score), 2))
            else:
                logger.info(f'Для {partner_entry.detachment} не найден верифицированный блок, пропускаем')

    if solo_entries:
        logger.info(
            'Есть записи для соло-участников. Удаляем записи из таблицы Q6 Ranking'
        )
        Q6Ranking.objects.all().delete()
        solo_entries.sort(key=lambda entry: entry[1], reverse=True)
        last_place = 0
        place = 0
        previous_score = None
        for entry in solo_entries:
            additional_place = calculate_q6_boolean_scores(entry[0])
            if additional_place > 5:
                continue
            if entry[1] != previous_score:
                place = last_place + 1
            updated_place = place + additional_place
            logger.info(
                f'Отчет {entry[0].detachment} занимает {updated_place} место'
            )
            Q6Ranking.objects.create(
                detachment=entry[0].detachment,
                place=updated_place,
                competition_id=competition_id
            )
            last_place = place
            previous_score = entry[1]

    if tandem_entries:
        logger.info(
            'Есть записи для тандем-участников. Удаляем записи из таблицы Q6 TandemRanking'
        )
        Q6TandemRanking.objects.all().delete()
        logger.info(f'Tandem Entries: {tandem_entries}')
        tandem_entries.sort(key=lambda entry: entry[2], reverse=True)
        last_place = 0
        place = 0
        previous_score = None
        for entry in tandem_entries:
            additional_place_junior = calculate_q6_boolean_scores(entry[0])
            additional_place_detachment = calculate_q6_boolean_scores(entry[1])
            if entry[2] != previous_score:
                place = last_place + 1
            logger.info(
                f'Для {entry[0].detachment} и {entry[1].detachment} определили места: по части сравнения - {place}, '
                f'доп места {additional_place_junior} и {additional_place_detachment}. '
            )
            updated_place = place + (
                round_math((additional_place_junior + additional_place_detachment) / 2)
            )
            logger.info(
                f'Отчет {entry[0]} и {entry[1]} занимает {updated_place} место'
            )
            Q6TandemRanking.objects.create(
                junior_detachment=entry[0].detachment,
                detachment=entry[1].detachment,
                place=updated_place,
                competition_id=competition_id
            )
            last_place = place
            previous_score = entry[2]


def calculate_q6_boolean_scores(entry: Q6DetachmentReport) -> int:
    score = 0
    try:
        if entry.demonstration_block.first_may_demonstration and entry.demonstration_block.is_verified:
            score += 1
    except ObjectDoesNotExist:
        pass
    try:
        if entry.creative_festival_block.creative_festival and entry.creative_festival_block.is_verified:
            score += 1
    except ObjectDoesNotExist:
        pass
    try:
        if entry.patriotic_action_block.patriotic_action and entry.patriotic_action_block.is_verified:
            score += 1
    except ObjectDoesNotExist:
        pass
    try:
        if entry.safety_work_week_block.safety_work_week and entry.safety_work_week_block.is_verified:
            score += 1
    except ObjectDoesNotExist:
        pass
    try:
        if (
                entry.commander_commissioner_school_block.commander_commissioner_school and
                entry.commander_commissioner_school_block.is_verified
        ):
            score += 1
    except ObjectDoesNotExist:
        pass
    try:
        if (
                entry.working_semester_opening_block.working_semester_opening and
                entry.working_semester_opening_block.is_verified
        ):
            score += 1
    except ObjectDoesNotExist:
        pass
    try:
        if entry.spartakiad_block.spartakiad and entry.spartakiad_block.is_verified:
            score += 1
        if (
                entry.professional_competition_block.professional_competition and
                entry.professional_competition_block.is_verified
        ):
            score += 1
    except ObjectDoesNotExist:
        pass
    place = 6
    if score == 8:
        place = 1
    elif score == 7:
        place = 2
    elif score == 6:
        place = 3
    elif score == 5:
        place = 4
    elif score == 4:
        place = 5
    return place


def calculate_june_detachment_members(entry, partner_entry=None):
    if entry:
        entry.june_15_detachment_members = entry.detachment.members.count() + 1
        entry.save()
    if partner_entry:
        partner_entry.june_15_detachment_members = (
            partner_entry.detachment.members.count() + 1
        )
        partner_entry.save()


def calculate_april_detachment_members(entry, partner_entry=None):
    if entry:
        entry.april_1_detachment_members = July15Participant.objects.filter(detachment=entry.detachment).last().members_number
        entry.save()
    if partner_entry:
        partner_entry.april_1_detachment_members = (
            July15Participant.objects.filter(detachment=partner_entry.detachment).last().members_number
        )
        partner_entry.save()


def calculate_score_q16(competition_id):
    """
    Таска для расчета очков Q16.

    Для celery-beat, считает вплоть до 15 октября 2024 года.
    :param competition_id: id конкурса
    """
    today = date.today()
    cutoff_date = date(2024, 10, 15)

    if today >= cutoff_date:
        return

    reports = Q16Report.objects.filter(
        competition_id=competition_id,
        is_verified=True
    )

    for report in reports:
        # если дата меньше 15 июня, или отчет сдан после 15 июня,
        # пересчитываем score. После 15 июня пересчитывать смысла нет
        # так как количество участников будет тем же
        logger.info(f'Расчет очков для отчета {report}')
        if today <= date(2024, 6, 15) or report.score == 0:
            report.june_15_detachment_members = report.detachment.members.count() + 1
            score = 0
            # первый блок
            if report.link_vk_commander and report.link_vk_commissar:
                score += 3
            # второй блок
            points_vk = (report.vk_rso_number_subscribers
                         / report.june_15_detachment_members
                         * 100)
            if points_vk >= 76:
                score += 3
            elif points_vk >= 51:
                score += 2
            elif points_vk == 50:
                score += 1
            # третий блок
            if report.link_vk_detachment:
                score += 3
            # четвертый блок
            if report.vk_detachment_number_subscribers:
                if report.vk_detachment_number_subscribers >= 300:
                    score += 3
                elif report.vk_detachment_number_subscribers >= 200:
                    score += 2
                elif report.vk_detachment_number_subscribers >= 100:
                    score += 1

            report.score = score
            logger.info(f'Очки {score} для отчета {report}')
            report.save()


def calculate_place(
        competition_id, model_report, model_ranking, model_tandem_ranking,
        reverse=True
):
    """
    Таска для расчета рейтингов Q1, Q7 - Q12, Q16 и Q20.

    Для celery-beat, считает вплоть до 15 октября 2024 года.
    :param competition_id: id конкурса
    :param model_report: модель отчета
    :param model_ranking: модель рейтинга старт
    :param model_tandem_ranking: модель тандем рейтинга
    :param reverse: True - чем больше очков, чем выше место в рейтинге,
                    False - чем меньше очков, тем выше место.
    """
    today = date.today()
    cutoff_date = COUNT_PLACES_DEADLINE

    if today >= cutoff_date:
        return

    participants = CompetitionParticipants.objects.filter(
        # первый запрос к бд
        competition_id=competition_id
    ).select_related('junior_detachment', 'detachment')

    if not participants:
        return

    start_ids = list(participants.filter(detachment__isnull=True)
                     .values_list('junior_detachment__id', flat=True))

    tandem_ids = list(participants.filter(detachment__isnull=False)
                      .values_list('junior_detachment__id', 'detachment__id'))

    reports_start = model_report.objects.filter(  # второй запрос к бд
        competition_id=competition_id,
        detachment_id__in=start_ids
    )

    sorted_by_score_start_reports = sorted(
        reports_start, key=lambda x: x.score, reverse=reverse
    )

    to_create_entries = []
    place = 0
    score = 0
    for report in sorted_by_score_start_reports:
        if report.score != score:
            place += 1
            score = report.score
        # если отчеты в рейтинге есть, но пустые, без элементов (удалили),
        # либо не верифицированы все, чтобы не попадали в рейтинг
        if place == 0:
            continue
        to_create_entries.append(
            model_ranking(competition=report.competition,
                          detachment=report.detachment,
                          place=place)
        )

    model_ranking.objects.filter(
        competition_id=competition_id).delete()  # третий запрос к бд
    model_ranking.objects.bulk_create(
        to_create_entries)  # четвертый запрос к бд

    reports = model_report.objects.filter(  # пятый запрос к бд
        competition_id=competition_id
    ).select_related('detachment').all()

    tandem_reports = [
        [reports.filter(detachment_id=id).first() for id in ids]
        for ids in tandem_ids
    ]

    # сортируем по сумме очков обоих отрядов
    # если у одного отряда нет отчета, то к очкам добавляем ноль или максимум
    # в зависимости от reverse, т.к. в разных показателях,
    # чем больше очков или чем меньше очков, тем выше место
    max_score = len(tandem_ids)
    sorted_by_score_tandem_reports = sorted(
        tandem_reports,
        key=lambda x: ((x[0].score + x[1].score) if (x[0] and x[1])
                       else (x[0].score + (
                           0 if reverse else max_score
                        ) if x[0] is not None
                             else (x[1].score + (
                                 0 if reverse else max_score
                             ) if x[1] is not None
                                   else (0 if reverse else max_score)))),
        reverse=reverse
    )
    to_create_entries = []
    place = 0
    score = 0
    for report in sorted_by_score_tandem_reports:
        if report[0] is None and report[1] is None:
            continue

        if report[0] is not None and report[1] is not None:
            if report[0].score + report[1].score != score:
                place += 1
                score = report[0].score + report[1].score
            # если отчеты в рейтинге есть, но пустые, без элементов (удалили),
            # либо не верифицированы все, чтобы не попадали в рейтинг
            if place == 0:
                continue
            to_create_entries.append(
                model_tandem_ranking(competition=report[0].competition,
                                     junior_detachment=report[0].detachment,
                                     detachment=report[1].detachment,
                                     place=place)
            )

        elif report[0] is not None:
            if report[0].score + max_score != score:
                place += 1
                score = report[0].score + max_score
            if place == 0:
                continue
            detachment = participants.get(
                junior_detachment=report[0].detachment,
            ).detachment
            to_create_entries.append(
                model_tandem_ranking(competition=report[0].competition,
                                     junior_detachment=report[0].detachment,
                                     detachment=detachment,
                                     place=place)
            )

        elif report[1] is not None:
            if report[1].score + max_score != score:
                place += 1
                score = report[1].score + max_score
            if place == 0:
                continue
            junior_detachment = participants.get(
                detachment=report[1].detachment,
            ).junior_detachment
            to_create_entries.append(
                model_tandem_ranking(competition=report[1].competition,
                                     junior_detachment=junior_detachment,
                                     detachment=report[1].detachment,
                                     place=place)
            )
    model_tandem_ranking.objects.filter(
        competition_id=competition_id).delete()  # шестой запрос к бд
    model_tandem_ranking.objects.bulk_create(
        to_create_entries)  # седьмой запрос к бд


def calculate_q1_score(competition_id):
    """
    Функция для расчета очков по 1 показателю.

    Выполняется каждый день до 15.07.2024.
    """
    today = date.today()
    end_date = date(2024, 7, 16)

    if today > end_date:
        return
    try:
        participants = CompetitionParticipants.objects.filter(
            competition_id=competition_id
        ).all()

        if not participants:
            logger.info('Нет участников')
            return

        detachments_data = []

        members = July15Participant.objects.all()

        members_dict = {m.detachment_id: m for m in members}

        # Собираем список списков, где
        #       первый элемент - id отряда-участника,
        #       второй - количество участников в отряде,
        #       третий - количество участников с оплаченным членским взносом
        # Добавляем везде единичку, т.к. командира нет в members
        for entry in participants:
            detachments_data.append([
                entry.junior_detachment_id,
                members_dict[entry.junior_detachment_id].participants_number,
                members_dict[entry.junior_detachment_id].members_number
            ])
            if entry.detachment:
                detachments_data.append([
                    entry.detachment_id,
                    members_dict[entry.detachment_id].participants_number,
                    members_dict[entry.detachment_id].members_number
                ])

        # logger.info(f'Всего участников 1 показателя: {len(detachments_data)} участники {detachments_data}')
        # Создаем отчеты каждому отряду с посчитанными score
        #       10 и менее человек в отряде  – за каждого уплатившего 1 балл
        #       11-20 человек – за каждого уплатившего 0.75 балла
        #       21 и более человек – за каждого уплатившего 0.5 балла

        to_create_entries = []

        # score по дефолту 1, иначе в таске как False проходит, не считается
        for data in detachments_data:
            score = 0
            if data[1] <= 10:
                score = data[2] * 1
            elif data[1] > 10 and data[1] <= 20:
                score = data[2] * 0.75
            elif data[1] > 20:
                score = data[2] * 0.5
            to_create_entries.append(
                Q1Report(competition_id=competition_id,
                         detachment_id=data[0],
                         score=score)
            )

        Q1Report.objects.filter(competition_id=competition_id).delete()
        Q1Report.objects.bulk_create(to_create_entries)
    except Exception as e:
        logger.exception(e)


def calculate_q3_q4_place(competition_id: int):
    logger.info(
        'Удаляем все записи из '
        'Q4Ranking, Q4TandemRanking, '
    )
    # Q3TandemRanking.objects.all().delete()
    # Q3Ranking.objects.all().delete()
    Q4Ranking.objects.all().delete()
    Q4TandemRanking.objects.all().delete()
    logger.info('Считаем места по 3 показателю')
    solo_entries = CompetitionParticipants.objects.filter(
        competition_id=competition_id,
        junior_detachment__isnull=False,
        detachment__isnull=True
    )
    logger.info('SOLO ENTRIES:')
    logger.info(solo_entries)
    tandem_entries = CompetitionParticipants.objects.filter(
        competition_id=competition_id,
        junior_detachment__isnull=False,
        detachment__isnull=False
    )
    logger.info('TANDEM ENTRIES:')
    logger.info(tandem_entries)
    for entry in solo_entries:
        # Получаем результаты для командира отряда
        # q3_place = get_q3_q4_place(entry.junior_detachment, 'university')
        q4_place = get_q3_q4_place(entry.junior_detachment, 'safety')
        # if q3_place:
        #     logger.info(f'Для СОЛО {entry} посчитали Q3 место - {q3_place}')
        #     Q3Ranking.objects.create(
        #         competition_id=competition_id,
        #         detachment=entry.junior_detachment,
        #         place=q3_place,
        #     )
        if q4_place:
            logger.info(f'Для {entry} посчитали Q4 место - {q4_place}')
            Q4Ranking.objects.create(
                competition_id=competition_id,
                detachment=entry.junior_detachment,
                place=q4_place,
            )
    for tandem_entry in tandem_entries:
        # q3_place_1 = get_q3_q4_place(tandem_entry.junior_detachment, 'university')
        # q3_place_2 = get_q3_q4_place(tandem_entry.detachment, 'university')
        q4_place_1 = get_q3_q4_place(tandem_entry.junior_detachment, 'safety')
        q4_place_2 = get_q3_q4_place(tandem_entry.detachment, 'safety')
        # if q3_place_1 and q3_place_2:
        #     final_place = round_math((q3_place_1 + q3_place_2) / 2)
        #     logger.info(f'Для ТАНДЕМ {tandem_entry} посчитали Q3 место - {final_place}')
        #     Q3TandemRanking.objects.create(
        #         competition_id=competition_id,
        #         detachment=tandem_entry.detachment,
        #         junior_detachment=tandem_entry.junior_detachment,
        #         place=final_place
        #     )
        if q4_place_1 and q4_place_2:
            final_place = round_math((q4_place_1 + q4_place_2) / 2)
            logger.info(f'Для ТАНДЕМ {tandem_entry} посчитали Q4 место - {final_place}')
            Q4TandemRanking.objects.create(
                competition_id=competition_id,
                detachment=tandem_entry.detachment,
                junior_detachment=tandem_entry.junior_detachment,
                place=final_place
            )


def calculate_q15_place(competition_id: int):
    """
    За указание 1 регионального конкурса начисляется 10 баллов.

    За указание 1 окружного конкурса начисляется 30 баллов.

    За указание 1 всероссийского конкурса начисляется 50 баллов.

    Далее баллы по всем указанным конкурсам суммируются, итоговая цифра сравнивается с цифрами из ответов других участников и определяется место. 1 место - самая большая цифра.
    """
    logger.info(
        'Начинаем считать Q15'
    )
    Q15TandemRank.objects.all().delete()
    Q15Rank.objects.all().delete()
    verified_entries = Q15DetachmentReport.objects.filter(
        q15grantwinner__is_verified=True
    ).distinct()
    logger.info(
        f'Получили отчеты: {verified_entries.count()}'
    )

    solo_entries = []
    tandem_entries = []

    for entry in verified_entries:
        participants_entry = CompetitionParticipants.objects.filter(
            junior_detachment=entry.detachment
        ).first()
        partner_entry = None
        if participants_entry and not participants_entry.detachment:
            category = solo_entries
            logger.info(f'Отчет {entry} - соло участник')
        elif participants_entry:
            logger.info(f'Отчет {entry} - тандем участник')
            category = tandem_entries
            if participants_entry:
                partner_entry = Q15DetachmentReport.objects.filter(
                    detachment=participants_entry.detachment,
                    competition_id=competition_id,
                ).first()
                if partner_entry:
                    logger.info(
                        f'Для отчета {entry} найден '
                        f'партнерский отчет: {partner_entry}'
                    )
        elif not participants_entry:
            participants_entry = CompetitionParticipants.objects.filter(
                detachment=entry.detachment
            ).first()
            partner_entry = entry
            if participants_entry:
                category = tandem_entries
                entry = Q15DetachmentReport.objects.filter(
                    detachment=participants_entry.junior_detachment,
                    competition_id=competition_id,
                ).first()
                if entry:
                    logger.info(
                        f'Для отчета {partner_entry} найден '
                        f'партнерский отчет: {entry}'
                    )

        if entry:
            logger.info('Отчет старшего отряда:')
            entry_grant_data = Q15GrantWinner.objects.filter(detachment_report=entry)
            entry.score = calculate_q15_score(entry_grant_data)
            entry.save()

        if partner_entry and entry:
            partner_entry_grant_data = Q15GrantWinner.objects.filter(detachment_report=partner_entry)
            partner_entry.score = calculate_q15_score(partner_entry_grant_data)
            partner_entry.save()
            logger.info(f'Сумма тандема для отчетов {partner_entry} и {entry} - {entry.score + partner_entry.score}')
            tuple_to_append = (
                entry, partner_entry, entry.score + partner_entry.score
            )
            if tuple_to_append not in category:
                category.append(tuple_to_append)
        elif entry and not partner_entry:
            logger.info(f'Сумма соло отчета {entry} - {entry.score}')
            category.append((entry, entry.score))

    if solo_entries:
        logger.info('Есть записи для соло-участников. Удаляем записи из таблицы Q15 Ranking')
        Q15Rank.objects.all().delete()
        solo_entries.sort(key=lambda entry: entry[1], reverse=True)
        last_score = None
        last_place = 0
        current_place = 1

        for entry in solo_entries:
            if entry[1] != last_score:
                last_place = current_place
                current_place += 1
            logger.info(f'Отчет {entry[0]} занимает {last_place} место')
            Q15Rank.objects.create(
                detachment=entry[0].detachment,
                place=last_place,
                competition_id=competition_id
            )
            last_score = entry[1]

    if tandem_entries:
        logger.info('Есть записи для тандем-участников. Удаляем записи из таблицы Q15 TandemRanking')
        Q15TandemRank.objects.all().delete()
        tandem_entries.sort(key=lambda entry: entry[2], reverse=True)
        last_score = None
        last_place = 0
        current_place = 1

        for entry in tandem_entries:
            if entry[2] != last_score:
                last_place = current_place
                current_place += 1
            logger.info(f'Отчеты {entry[0]} и {entry[1]} занимают {last_place} место')
            Q15TandemRank.objects.create(
                junior_detachment=entry[0].detachment,
                detachment=entry[1].detachment,
                place=last_place,
                competition_id=competition_id
            )
            last_score = entry[2]

def calculate_q15_score(grant_winners_data: List[Q15GrantWinner]):
    status_scores_mapping = {
        'Региональный': 10,
        'Окружной': 30,
        'Всероссийский': 50
    }
    score = 0
    if grant_winners_data:
        for grant_data in grant_winners_data:
            print(f'Grant_data status: {grant_data.status}, need to add score: {status_scores_mapping.get(grant_data.status, 0)}')
            score += status_scores_mapping.get(grant_data.status, 0)
    return score

def calculate_q5_place(competition_id: int):
    """
    Кол-во участников, прошедших профессиональное обучение
    делится на количество участников в отряде на дату 15 июня 2024
    года, далее результат умножается на 100%.

    Значение:
    более 95% - 1 место
    от 90% до 95% - 2 место
    от 85% до 90% - 3 место
    от 80% до 85% - 4 место
    от 75% до 80% - 5 место
    от 70% до 75% - 6 место
    от 65% до 70% - 7 место
    от 60% до 65% - 8 место
    от 55% до 60% - 9 место
    от 50% до 55% - 10 место
    от 45% до 50% - 11 место
    от 40% до 45% - 12 место
    от 35% до 40% - 13 место
    от 30% до 35% - 14 место
    от 25% до 30% - 15 место
    от 20% до 25% - 16 место
    от 15% до 20% - 17 место
    от 10% до 15% - 18 место
    от 5% до 10% - 19 место
    от 0% до 5% - 20 место
    """
    today = date.today()
    cutoff_date = date(2024, 6, 30)

    logger.info(
        'Удаляем все записи из Q5Ranking, Q5TandemRanking'
    )
    Q5TandemRanking.objects.all().delete()
    Q5Ranking.objects.all().delete()
    solo_entries = CompetitionParticipants.objects.filter(
        competition_id=competition_id,
        junior_detachment__isnull=False,
        detachment__isnull=True
    )
    tandem_entries = CompetitionParticipants.objects.filter(
        competition_id=competition_id,
        junior_detachment__isnull=False,
        detachment__isnull=False
    )
    logger.info(f'solo entries: {solo_entries}, tandem entries: {tandem_entries}')
    for entry in solo_entries:
        try:
            entry_report = entry.junior_detachment.q5detachmentreport_detachment_reports.get(competition_id=competition_id)
        except Q5DetachmentReport.DoesNotExist:
            continue
        logger.info(f'detachment report for solo entry: {entry_report}')
        if not entry_report:
            continue
        if today <= cutoff_date:
            logger.info(
                f'Сегодняшняя дата {today} меньше '
                f'cutoff date: {cutoff_date}. '
                f'Обновляем кол-во участников.'
            )
            calculate_june_detachment_members(entry_report)
        educated_participants_count = Q5EducatedParticipant.objects.filter(is_verified=True, detachment_report=entry_report).count()
        if educated_participants_count > 0:
            Q5Ranking.objects.create(
                competition_id=competition_id,
                detachment=entry_report.detachment,
                place=get_q5_place(educated_participants_count, entry_report.june_15_detachment_members)
            )
    logger.info(f'Q5 Tandem Entries: {tandem_entries}')
    for tandem_entry in tandem_entries:
        tandem_entry_report = None
        junior_tandem_entry_report = None
        is_tandem_entry_report = False
        is_junior_tandem_entry_report = False
        logger.info(f'Проверяем тандем Q5: {tandem_entry.detachment}, {tandem_entry.junior_detachment}')
        try:
            junior_tandem_entry_report = tandem_entry.junior_detachment.q5detachmentreport_detachment_reports.get(
                competition_id=competition_id)
        except Q5DetachmentReport.DoesNotExist:
            pass
        try:
            tandem_entry_report = tandem_entry.detachment.q5detachmentreport_detachment_reports.get(competition_id=competition_id)
            if tandem_entry_report and not junior_tandem_entry_report:
                logger.info(
                    f'Для {tandem_entry.detachment} найден отчет, но не найден для {tandem_entry.junior_detachment}'
                )
                is_tandem_entry_report = True
            elif junior_tandem_entry_report and tandem_entry_report:
                logger.info(
                    f'Для {tandem_entry.detachment} и {tandem_entry.junior_detachment} найдены отчеты'
                )
                is_tandem_entry_report = True
                is_junior_tandem_entry_report = True
        except Q5DetachmentReport.DoesNotExist:
            if not tandem_entry_report and not junior_tandem_entry_report:
                logger.info(
                    f'Для {tandem_entry.detachment} и {tandem_entry.junior_detachment} не найдены отчеты'
                )
                continue
            elif junior_tandem_entry_report and not tandem_entry_report:
                logger.info(
                    f'Для {tandem_entry.junior_detachment} найден отчет, но не найден для {tandem_entry.detachment}'
                )
                is_junior_tandem_entry_report = True

        if not tandem_entry_report and not junior_tandem_entry_report:
            logger.info(
                f'Скип (для обоих не найдены отчеты)'
            )
            continue

        if today <= cutoff_date:
            logger.info(
                f'Сегодняшняя дата {today} меньше '
                f'cutoff date: {cutoff_date}. '
                f'Обновляем кол-во участников.'
            )
            calculate_june_detachment_members(tandem_entry_report, junior_tandem_entry_report)

        educated_participants_count_junior = Q5EducatedParticipant.objects.filter(
            is_verified=True,
            detachment_report=junior_tandem_entry_report
        ).count()
        educated_participants_count_detachment = Q5EducatedParticipant.objects.filter(
            is_verified=True,
            detachment_report=tandem_entry_report
        ).count()
        if is_junior_tandem_entry_report and not is_tandem_entry_report:
            final_place = round_math((
                get_q5_place(0, 1) +
                get_q5_place(educated_participants_count_junior, junior_tandem_entry_report.june_15_detachment_members)
            ) / 2)
        elif not junior_tandem_entry_report and not is_junior_tandem_entry_report:
            final_place = round_math((
                get_q5_place(0, 1) +
                get_q5_place(educated_participants_count_detachment, tandem_entry_report.june_15_detachment_members)
            ) / 2)
        else:
            final_place = round_math((
                get_q5_place(educated_participants_count_junior, junior_tandem_entry_report.june_15_detachment_members) +
                get_q5_place(educated_participants_count_detachment, tandem_entry_report.june_15_detachment_members)
            ) / 2)
        logger.info(f'Q5 Final Place for {tandem_entry}')
        logger.info(f'educated_participants_count_junior + educated_participants_count_detachment = {educated_participants_count_junior + educated_participants_count_detachment}')
        if educated_participants_count_junior + educated_participants_count_detachment > 0:
            Q5TandemRanking.objects.create(
                competition_id=competition_id,
                detachment=tandem_entry.detachment,
                junior_detachment=tandem_entry.junior_detachment,
                place=final_place
            )


def get_q5_place(participants_count: int, june_15_detachment_members: int) -> int:
    percentage = (participants_count / june_15_detachment_members) * 100

    if percentage > 95:
        return 1
    elif 90 <= percentage <= 95:
        return 2
    elif 85 <= percentage < 90:
        return 3
    elif 80 <= percentage < 85:
        return 4
    elif 75 <= percentage < 80:
        return 5
    elif 70 <= percentage < 75:
        return 6
    elif 65 <= percentage < 70:
        return 7
    elif 60 <= percentage < 65:
        return 8
    elif 55 <= percentage < 60:
        return 9
    elif 50 <= percentage < 55:
        return 10
    elif 45 <= percentage < 50:
        return 11
    elif 40 <= percentage < 45:
        return 12
    elif 35 <= percentage < 40:
        return 13
    elif 30 <= percentage < 35:
        return 14
    elif 25 <= percentage < 30:
        return 15
    elif 20 <= percentage < 25:
        return 16
    elif 15 <= percentage < 20:
        return 17
    elif 10 <= percentage < 15:
        return 18
    elif 5 <= percentage < 10:
        return 19
    else:
        return 20


def get_q3_q4_place(detachment: Detachment, category: str):
    commander_score = Attempt.objects.filter(
        user=detachment.commander,
        category=category,
        timestamp__lt=date(2024, 5, 16)
    ).aggregate(Max('score'))['score__max'] or 0
    logger.info(f'у командира {detachment} {detachment.commander} очков - {commander_score}')
    logger.info(f'Command score for entry {CompetitionParticipants} is {commander_score}')

    if category == 'university':
        # Получаем результаты для комиссара отряда
        commissioner_score = 0
        commissioners = UserDetachmentPosition.objects.filter(
            position__name=settings.COMMISSIONER_POSITION_NAME,
            headquarter=detachment
        )
        for commissioner in commissioners:
            commissioner_max_score = Attempt.objects.filter(
                user=commissioner.user,
                category=category,
                timestamp__lt=date(2024, 5, 16)
            ).aggregate(Max('score'))['score__max']
            if commissioner_max_score:
                commissioner_score = max(commissioner_score,
                                         commissioner_max_score)

        # Рассчитываем средний балл
        average_score = (
                                commander_score + commissioner_score
                        ) / 2 if commander_score + commissioner_score > 0 else 0
    else:
        # Получаем результаты для всех участников отряда
        score = 0
        participants = UserDetachmentPosition.objects.filter(
            headquarter=detachment
        )
        logger.info(f'{participants.count()} участников для отряда {detachment}')
        for participant in participants:
            participant_max_score = Attempt.objects.filter(
                user=participant.user,
                category=category,
                timestamp__lt=date(2024, 5, 16)
            ).aggregate(Max('score'))['score__max']
            logger.info(f'у участника {participant} очков - {participant_max_score}')
            if participant_max_score:
                score += participant_max_score

        # Рассчитываем средний балл
        average_score = (commander_score + score) / (len(participants) + 1)
        logger.info(
            f'Средний балл отряда - {average_score}. '
            f'Рассчитано по формуле {commander_score + score} / {len(participants)+1}'
        )

    # Определяем место
    place = determine_q3_q4_place(average_score)
    return place


def determine_q3_q4_place(average_score):
    if average_score > 95:
        return 1
    elif 90 <= average_score <= 95:
        return 2
    elif 85 <= average_score < 90:
        return 3
    elif 80 <= average_score < 85:
        return 4
    elif 75 <= average_score < 80:
        return 5
    elif 70 <= average_score < 75:
        return 6
    elif 65 <= average_score < 70:
        return 7
    elif 60 <= average_score < 65:
        return 8
    else:
        return 9


def calculate_q19_place(report: Q19Report) -> int:
    if report.safety_violations == 'Имеются':
        return 2
    return 1
