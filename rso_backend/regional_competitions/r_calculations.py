import logging

from headquarters.models import RegionalHeadquarter
from regional_competitions.models import RegionalR12, RegionalR13, RegionalR14


logger = logging.getLogger('tasks')


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
