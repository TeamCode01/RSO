import logging
from datetime import datetime

from headquarters.models import RegionalHeadquarter

from regional_competitions.models import (RegionalR5, RegionalR5Event,
                                          RegionalR12, RegionalR13,
                                          RegionalR14)

logger = logging.getLogger('tasks')


def calculate_r5_score():
    """Считает  очки по 5 показателю.

    P= ((x1-z1)*y1+((xn-zn)yn
    ((xn-zn)yn - вычисление очков для всех мероприятий у РО.

    Три поля ввода:
    x- количество человек, принявших участие в проекте, всего(participants_number)
    z- количество человек из своего региона, принявших участие в проекте(ro_participants_number)
    y- количество дней проведения проекта(end_date - start_date)
    Количество дней проведения мероприятия рассчитываем сами, как разницу между датой окончания и датой начала.

    Все цифры в формулу берутся из корректировок ЦШ.

    """
    
    #TODO: написать функцию расчёта мест, создать таску.
    
    logger.info('Выполняется подсчет отчета по r5 показателю')

    # в переменную записываем id рег штабов, у которых уже есть верифицированный отчет по 5 показателю
    verified_reports_ro_ids = RegionalR5.objects.filter(verified_by_chq=True).values_list(
        'regional_headquarter__id', flat=True
    )
    if verified_reports_ro_ids:
        logger.info(f'Найдено {len(verified_reports_ro_ids)} верифицированных отчетов по 5 показателю')
    else:
        logger.info('Ни одного верифицированного отчета по 5 показателю не найдено')
        return None

    for ro_id in verified_reports_ro_ids:
        logger.info(f'Выполняется подсчет очков для рег штаба {ro_id}')
        ro_score = 0
        # в ro_events получаем список кортежей.
        # Пример - [(34, 18, 2024-07-29, 2024-07-29), (4, 2, 2024-08-29, 2024-08-29),]
        ro_events = RegionalR5Event.objects.filter(
            regional_r5__regional_headquarter__id=ro_id
        ).values_list(
            'participants_number',
            'ro_participants_number',
            'start_date',
            'end_date'
        )
        # вычисляем сумму очков, после цикла записываем в таблицу
        for item in ro_events:

            date_start = datetime.strptime(item[2], '%Y-%m-%d').date()
            date_end = datetime.strptime(item[3], '%Y-%m-%d').date()

            days_diff = (date_end - date_start).days + 1
            ro_score += (item[0] - item[1]) * days_diff
        instance = RegionalR5.objects.get(regional_headquarter__id=ro_id)
        instance.score = ro_score
        instance.save()
        logger.info(f'Подсчитали очки для рег штаба {ro_id}. Очки: {ro_score}')

    logger.info('Подсчет очков по 5 показателю завершен')


def calculate_r14():
    """Считает отчет по 14 показателю."""
    logger.info('Выполняется подсчет отчета по r14 показателю')
    try:
        # тащим id всех рег штабов, у которых уже есть отчет по 14 показателю
        existing_ro_ids = RegionalR14.objects.values_list('report_12__regional_headquarter__id', flat=True)

        # тащим id штабов, у которых есть верифицированные отчеты по 12 и 13 показателям
        ro_ids_with_12_reports = RegionalR12.objects.filter(
            verified_by_chq=True,
        ).values_list('regional_headquarter__id', flat=True)

        ro_ids_with_13_reports = RegionalR13.objects.filter(
            verified_by_chq=True,
        ).values_list('regional_headquarter__id', flat=True)

        # находим id ро, у которых нет 14 отчета, но есть 12 и 13 отчеты
        ro_ids_without_14_reports = set(ro_ids_with_12_reports) & set(ro_ids_with_13_reports) - set(existing_ro_ids)
        if not ro_ids_without_14_reports:
            logger.info('Нет региональных штабов, у которых нет отчета по r14 показателю')
            return

        # тащим всю необходимую инфу для формирования отчета
        ro_reports = RegionalHeadquarter.objects.filter(
            id__in=ro_ids_without_14_reports
        ).values(
            'id', 'regionalr12__id', 'regionalr13__id', 'regionalr12__amount_of_money', 'regionalr13__number_of_members'
        )

        reports_to_create = []
        for ro in ro_reports:
            reports_to_create.append(RegionalR14(
                report_12_id=ro['regionalr12__id'],
                report_13_id=ro['regionalr13__id'],
                score=round(ro['regionalr13__number_of_members'] / ro['regionalr12__amount_of_money'], 2),
            ))

    except Exception as e:
        logger.exception(f'Не удалось подсчитать отчет по r14 показателю: {e}')

    logger.info(f'Создаем {len(reports_to_create)} отчетов по r14 показателю')
    try:
        new_reports = RegionalR14.objects.bulk_create(reports_to_create)
    except Exception as e:
        logger.exception(f'Не удалось создать отчеты по r14 показателю: {e}')

    logger.info(f'Завершено подсчет отчета по r14 показателю. Создано {len(new_reports)} отчетов')
