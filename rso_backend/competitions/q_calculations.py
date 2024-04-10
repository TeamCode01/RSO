from collections import Counter
from typing import List

from datetime import date
from django.db.models import Max
from django.conf import settings
import logging
from competitions.models import Q13EventOrganization, Q14DetachmentReport, Q14LaborProject, Q14Ranking, Q14TandemRanking, Q16Report, \
    Q17DetachmentReport, Q17EventLink, Q17Ranking, Q17TandemRanking, Q18Ranking, \
    Q18DetachmentReport, CompetitionParticipants, Q18TandemRanking, Q19Ranking, \
    Q19Report, Q19TandemRanking, Q1Report, Q2DetachmentReport, Q2Ranking, Q2TandemRanking, Q7Ranking, Q7Report, \
    Q7TandemRanking, Q3Ranking, Q3TandemRanking, Q4Ranking, Q4TandemRanking, \
    Q5TandemRanking, Q5Ranking, \
    Q5EducatedParticipant, Q5DetachmentReport, Q15TandemRank, Q15Rank, Q15DetachmentReport, Q15GrantWinner, \
    Q6DetachmentReport, Q6Ranking, Q6TandemRanking, Q1Ranking, OverallTandemRanking, OverallRanking
from competitions.utils import assign_ranks, find_second_element_by_first, get_place_q2, tandem_or_start, is_main_detachment
from headquarters.models import UserDetachmentPosition, Detachment
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

    solo_rankings.sort(key=lambda x: x['place'], reverse=True)
    solo_place = len(solo_rankings)
    logger.info(f'Найдены {solo_place} записей для подсчета индивидуального общего места')
    for solo_ranking_entry in solo_rankings:
        OverallRanking.objects.create(
            competition_id=competition_id,
            detachment=solo_ranking_entry['detachment'],
            places_sum=solo_ranking_entry['place'],
            place=solo_place
        )
        solo_place -= 1

    tandem_rankings.sort(key=lambda x: x['place'], reverse=True)
    tandem_place = len(tandem_rankings)
    logger.info(f'Найдены {tandem_place} записей для подсчета общего тандем места')
    for tandem_ranking_entry in tandem_rankings:
        OverallTandemRanking.objects.create(
            competition_id=competition_id,
            detachment=tandem_ranking_entry['detachment'],
            junior_detachment=tandem_ranking_entry['junior_detachment'],
            places_sum=tandem_ranking_entry['place'],
            place=tandem_place
        )
        tandem_place -= 1


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
    )

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
        f'Получили верифицированные отчеты: {verified_entries.count()}')

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
        if today <= cutoff_date:
            logger.info(
                f'Сегодняшняя дата {today} меньше '
                f'cutoff date: {cutoff_date}. '
                f'Обновляем кол-во участников.'
            )
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
                category.append(tuple_to_append)
        elif entry and not partner_entry:
            category.append((entry, entry.score))

    if solo_entries:
        logger.info(
            'Есть записи для соло-участников. Удаляем записи из таблицы Q18 Ranking')
        Q18Ranking.objects.all().delete()
        solo_entries.sort(key=lambda entry: entry[1])
        place = len(solo_entries)
        for entry in solo_entries:
            logger.info(
                f'Отчет {entry[0]} занимает {place} место'
            )
            Q18Ranking.objects.create(
                detachment=entry[0].detachment,
                place=place,
                competition_id=competition_id
            )
            place -= 1

    if tandem_entries:
        logger.info(
            'Есть записи для тандем-участников. Удаляем записи из таблицы Q18 TandemRanking')
        Q18TandemRanking.objects.all().delete()
        tandem_entries.sort(key=lambda entry: entry[2])
        place = len(tandem_entries)
        for entry in tandem_entries:
            logger.info(
                f'Отчеты {entry[0]} и {entry[1]} занимают {place} место'
            )
            Q18TandemRanking.objects.create(
                junior_detachment=entry[0].detachment,
                detachment=entry[1].detachment,
                place=place,
                competition_id=competition_id
            )
            place -= 1


def calculate_q6_place(competition_id):
    today = date.today()
    cutoff_date = date(2024, 4, 15)

    logger.info(f'Сегодняшняя дата: {today}')

    verified_entries = Q6DetachmentReport.objects.filter(is_verified=True, competition_id=competition_id)
    logger.info(
        f'Получили верифицированные отчеты: {verified_entries.count()}')

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
                category = tandem_entries
                entry = Q6DetachmentReport.objects.filter(
                    detachment=participants_entry.junior_detachment,
                    competition_id=competition_id,
                    is_verified=True
                ).first()
                if entry:
                    logger.info(
                        f'Для отчета {partner_entry} найден '
                        f'партнерский отчет: {entry}'
                    )
        if today <= cutoff_date:
            logger.info(
                f'Сегодняшняя дата {today} меньше '
                f'cutoff date: {cutoff_date}. '
                f'Обновляем кол-во участников.'
            )
            calculate_april_detachment_members(entry, partner_entry)

        if entry:
            entry_participants_number = (
                    entry.working_semester_opening_participants +
                    entry.patriotic_action_participants +
                    entry.first_may_demonstration_participants
            )
            entry.score = (entry_participants_number / entry.april_1_detachment_members) + calculate_q6_boolean_scores(entry)
            entry.save()

        if partner_entry and entry:
            partner_entry_participants_number = (
                    entry.working_semester_opening_participants +
                    entry.patriotic_action_participants +
                    entry.first_may_demonstration_participants
            )
            partner_entry.score = (partner_entry_participants_number / partner_entry.april_1_detachment_members) + calculate_q6_boolean_scores(partner_entry)
            partner_entry.save()
            tuple_to_append = (
                entry, partner_entry, entry.score + partner_entry.score
            )
            if tuple_to_append not in category:
                category.append(tuple_to_append)
        elif entry and not partner_entry:
            category.append((entry, entry.score))

    if solo_entries:
        logger.info(
            'Есть записи для соло-участников. Удаляем записи из таблицы Q6 Ranking')
        Q6Ranking.objects.all().delete()
        solo_entries.sort(key=lambda entry: entry[1])
        place = len(solo_entries)
        for entry in solo_entries:
            logger.info(
                f'Отчет {entry[0]} занимает {place} место'
            )
            Q6Ranking.objects.create(
                detachment=entry[0].detachment,
                place=place,
                competition_id=competition_id
            )
            place -= 1

    if tandem_entries:
        logger.info(
            'Есть записи для тандем-участников. Удаляем записи из таблицы Q6 TandemRanking')
        Q6TandemRanking.objects.all().delete()
        tandem_entries.sort(key=lambda entry: entry[2])
        place = len(tandem_entries)
        for entry in tandem_entries:
            logger.info(
                f'Отчеты {entry[0]} и {entry[1]} занимают {place} место'
            )
            Q6TandemRanking.objects.create(
                junior_detachment=entry[0].detachment,
                detachment=entry[1].detachment,
                place=place,
                competition_id=competition_id
            )
            place -= 1


def calculate_q6_boolean_scores(entry: Q6DetachmentReport):
    score = 0
    if entry.first_may_demonstration:
        score += 1
    if entry.creative_festival:
        score += 1
    if entry.patriotic_action:
        score += 1
    if entry.safety_work_week:
        score += 1
    if entry.commander_commissioner_school:
        score += 1
    if entry.working_semester_opening:
        score += 1
    if entry.spartakiad:
        score += 1
    if entry.professional_competition:
        score += 1
    return score


def calculate_june_detachment_members(entry, partner_entry=None):
    entry.june_15_detachment_members = entry.detachment.members.count() + 1
    entry.save()
    if partner_entry:
        partner_entry.june_15_detachment_members = (
            partner_entry.detachment.members.count() + 1
        )
        partner_entry.save()


def calculate_april_detachment_members(entry, partner_entry=None):
    entry.april_1_detachment_members = entry.detachment.members.count() + 1
    entry.save()
    if partner_entry:
        partner_entry.april_1_detachment_members = (
            partner_entry.detachment.members.count() + 1
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
    Таска для расчета рейтингов Q7 - Q12 и Q20.

    Для celery-beat, считает вплоть до 15 октября 2024 года.
    :param competition_id: id конкурса
    :param model_report: модель отчета
    :param model_ranking: модель рейтинга старт
    :param model_tandem_ranking: модель тандем рейтинга
    :param reverse: True - чем больше очков, чем выше место в рейтинге,
                    False - чем меньше очков, тем выше место.
    """
    today = date.today()
    cutoff_date = date(2024, 10, 15)

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
    for index, report in enumerate(sorted_by_score_start_reports):
        to_create_entries.append(
            model_ranking(competition=report.competition,
                          detachment=report.detachment,
                          place=index + 1)
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

    sorted_by_score_tandem_reports = sorted(
        tandem_reports,
        key=lambda x: ((x[0].score + x[1].score) if (x[0] and x[1])
                       else (x[0].score if x[0] is not None
                             else (x[1].score if x[1] is not None
                                   else (0 if reverse else len(tandem_ids))))),
        reverse=reverse
    )

    to_create_entries = []
    for index, report in enumerate(sorted_by_score_tandem_reports):
        if report[0] is None and report[1] is None:
            continue

        if report[0] is not None and report[1] is not None:
            to_create_entries.append(
                model_tandem_ranking(competition=report[0].competition,
                                     junior_detachment=report[0].detachment,
                                     detachment=report[1].detachment,
                                     place=index + 1)
            )

        elif report[0] is not None:
            detachment = participants.get(
                junior_detachment=report[0].detachment,
            ).detachment
            to_create_entries.append(
                model_tandem_ranking(competition=report[0].competition,
                                     junior_detachment=report[0].detachment,
                                     detachment=detachment,
                                     place=index + 1)
            )

        elif report[1] is not None:
            junior_detachment = participants.get(
                detachment=report[1].detachment,
            ).junior_detachment
            to_create_entries.append(
                model_tandem_ranking(competition=report[1].competition,
                                     junior_detachment=junior_detachment,
                                     detachment=report[1].detachment,
                                     place=index + 1)
            )
    model_tandem_ranking.objects.filter(
        competition_id=competition_id).delete()  # шестой запрос к бд
    model_tandem_ranking.objects.bulk_create(
        to_create_entries)  # седьмой запрос к бд


def calculate_q1_score(competition_id):
    """
    Функция для расчета очков по 1 показателю.

    Выполняется только 15.04.2024.
    """
    today = date.today()
    start_date = date(2024, 4, 15)

    if today != start_date:
        return

    participants = CompetitionParticipants.objects.filter(
        competition_id=competition_id
    ).all()  # мб добавить select_related('junior_detachment__members', 'detachment__members')

    if not participants:
        logger.info('Нет участников')
        return

    detachments_data = []

    # Собираем список списков, где
    #       первый элемент - id отряда-участника,
    #       второй - количество участников в отряде,
    #       третий - количество участников с оплаченным членским взносом
    # Добавляем везде единичку, т.к. командира нет в members
    for entry in participants:
        detachments_data.append([
            entry.junior_detachment_id,
            entry.junior_detachment.members.count() + 1,
            entry.junior_detachment.members.filter(
                user__membership_fee=True
            ).count() + 1 if entry.junior_detachment.commander.membership_fee else 0
        ])
        if entry.detachment:
            detachments_data.append([
                entry.detachment_id,
                entry.detachment.members.count() + 1,
                entry.detachment.members.filter(
                    user__membership_fee=True
                ).count() + 1 if entry.detachment.commander.membership_fee else 0
            ])

    # Создаем отчеты каждому отряду с посчитанными score
    #       10 человек в отряде  – за каждого уплатившего 1 балл
    #       11-20 человек – за каждого уплатившего 0.75 балла
    #       21 и более человек – за каждого уплатившего 0.5 балла

    to_create_entries = []

    # score по дефолту 1, иначе в таске как False проходит, не считается
    for data in detachments_data:
        score = 1  # TODO: Если в отряде меньше 10 человек - то score = 1 УТОЧНИТЬ
        if data[1] == 10:
            score = data[2] * 1 + 1
        elif data[1] > 10 and data[1] <= 20:
            score = data[2] * 0.75 + 1
        elif data[1] > 20:
            score = data[2] * 0.5 + 1
        to_create_entries.append(
            Q1Report(competition_id=competition_id,
                     detachment_id=data[0],
                     score=score)
        )

    Q1Report.objects.filter(competition_id=competition_id).delete()
    Q1Report.objects.bulk_create(to_create_entries)


def calculate_q3_q4_place(competition_id: int):
    logger.info(
        'Удаляем все записи из Q3Ranking, Q3TandemRanking, '
        'Q4Ranking, Q4TandemRanking, '
    )
    Q3TandemRanking.objects.all().delete()
    Q3Ranking.objects.all().delete()
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
        q3_place = get_q3_q4_place(entry.junior_detachment, 'university')
        q4_place = get_q3_q4_place(entry.junior_detachment, 'safety')
        if q3_place:
            logger.info(f'Для СОЛО {entry} посчитали Q3 место - {q3_place}')
            Q3Ranking.objects.create(
                competition_id=competition_id,
                detachment=entry.detachment,
                place=q3_place,
            )
        if q4_place:
            logger.info(f'Для {entry} посчитали Q4 место - {q4_place}')
            Q4Ranking.objects.create(
                competition_id=competition_id,
                detachment=entry,
                place=q3_place,
            )
    for tandem_entry in tandem_entries:
        q3_place_1 = get_q3_q4_place(tandem_entry.junior_detachment, 'university')
        q3_place_2 = get_q3_q4_place(tandem_entry.detachment, 'university')
        q4_place_1 = get_q3_q4_place(tandem_entry.junior_detachment, 'safety')
        q4_place_2 = get_q3_q4_place(tandem_entry.detachment, 'safety')
        if q3_place_1 and q3_place_2:
            final_place = round((q3_place_1 + q3_place_2) / 2)
            logger.info(f'Для ТАНДЕМ {tandem_entry} посчитали Q3 место - {final_place}')
            Q3TandemRanking.objects.create(
                competition_id=competition_id,
                detachment=tandem_entry.detachment,
                junior_detachment=tandem_entry.junior_detachment,
                place=final_place
            )
        if q4_place_1 and q4_place_2:
            final_place = round((q4_place_1 + q4_place_2) / 2)
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
    verified_entries = Q15DetachmentReport.objects.filter()
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
        logger.info(
            'Есть записи для соло-участников. Удаляем записи из таблицы Q15 Ranking'
        )
        Q15Rank.objects.all().delete()
        solo_entries.sort(key=lambda entry: entry[1])
        place = len(solo_entries)
        for entry in solo_entries:
            logger.info(
                f'Отчет {entry[0]} занимает {place} место'
            )
            Q15Rank.objects.create(
                detachment=entry[0].detachment,
                place=place,
                competition_id=competition_id
            )
            place -= 1

    if tandem_entries:
        logger.info(
            'Есть записи для тандем-участников. Удаляем записи из таблицы Q15 TandemRanking'
        )
        Q15TandemRank.objects.all().delete()
        tandem_entries.sort(key=lambda entry: entry[2])
        place = len(tandem_entries)
        for entry in tandem_entries:
            logger.info(
                f'Отчеты {entry[0]} и {entry[1]} занимают {place} место'
            )
            Q15TandemRank.objects.create(
                junior_detachment=entry[0].detachment,
                detachment=entry[1].detachment,
                place=place,
                competition_id=competition_id
            )
            place -= 1


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
    cutoff_date = date(2024, 6, 15)

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
        Q5Ranking.objects.create(
            competition_id=competition_id,
            detachment=entry_report.detachment,
            place=get_q5_place(educated_participants_count, entry_report.june_15_detachment_members)
        )
    for tandem_entry in tandem_entries:
        try:
            tandem_entry_report = tandem_entry.detachment.q5detachmentreport_detachment_reports.get(competition_id=competition_id)
            junior_tandem_entry_report = tandem_entry.junior_detachment.q5detachmentreport_detachment_reports.get(competition_id=competition_id)
            logger.info(f'detachment reports for tandem entries: {tandem_entry_report}, {junior_tandem_entry_report}')
        except Q5DetachmentReport.DoesNotExist:
            continue
        if not tandem_entry_report or not junior_tandem_entry_report:
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

        final_place = round((
            get_q5_place(educated_participants_count_junior, junior_tandem_entry_report.june_15_detachment_members) +
            get_q5_place(educated_participants_count_detachment, tandem_entry_report.june_15_detachment_members)
        ) / 2)

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
        category=category
    ).aggregate(Max('score'))['score__max'] or 0
    logger.info(f'Command score for entry {CompetitionParticipants} is {commander_score}')

    if category == 'university':
        # Получаем результаты для комиссара отряда
        commissioner_score = 0
        commissioners = UserDetachmentPosition.objects.filter(
            position__name=settings.COMMISSIONER_POSITION_NAME,
            detachment=detachment
        )
        for commissioner in commissioners:
            commissioner_max_score = Attempt.objects.filter(
                user=commissioner.user,
                category=category
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
            detachment=detachment
        )
        for participant in participants:
            participant_max_score = Attempt.objects.filter(
                user=participant.user,
                category=category
            ).aggregate(Max('score'))['score__max']
            if participant_max_score:
                score += participant_max_score

        # Рассчитываем средний балл
        average_score = (commander_score + score) / (len(participants) + 1)

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
        return None


def calculate_q19_place(report: Q19Report) -> int:
    if report.safety_violations == 'Имеются':
        return 2
    return 1
