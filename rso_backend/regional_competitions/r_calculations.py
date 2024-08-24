import logging
from datetime import datetime

from headquarters.models import RegionalHeadquarter

from regional_competitions.models import (RegionalR4, RegionalR12, RegionalR13,
                                          RegionalR14, r7_models_factory, r9_models_factory,
                                          RegionalR16)

logger = logging.getLogger('tasks')


def calculate_r4_score(report: RegionalR4):
    """Расчет очков по 4 показателю.

    P=(х1*y1)+(xn*yn)
    P=(х1*y1)+(xn*yn*0.8)

    «х1…xn» - количество человек, принявших участие в каждом мероприятии или проекте; 
    «у1…yn» - количество дней проведения каждого мероприятия или проекта

    Количество дней проведения мероприятия рассчитываем сами, как разницу между датой окончания и датой начала.
    """
    logger.info('Выполняется Расчет очков для отчета 4 показателя')
    events = report.events
    logger.info(f'Для отчета {report.id} {report.regional_headquarter} найдено {events.count()} мероприятий')
    for event in events:
        days_count = (event.end_date - event.start_date).days
        report.score += (days_count * event.participants_number) * (0.8 if event.is_interregional else 1)
        logger.info(
            f'Мероприятие {event} длилось {days_count} дней с кол-вом участников в {event.participant_number} человек. '
            f'Мероприятие {"" if event.is_interregional else "не"} является межрегиональным. Отчет {report.id} теперь '
            f'имеет {report.score} очков.'
        )
    logger.info(
        f'Все мероприятия по 4 показателю рассчитаны. '
        f'Финальное кол-во очков для отчета {report.id} {report.regional_headquarter} по 4 показателю: {report.score}'
    )
    report.save()


def calculate_r5_score(report):
    """Расчет очков по 5 показателю.

    P= ((x1-z1)*y1+((xn-zn)yn
    ((xn-zn)yn - вычисление очков для всех мероприятий у РО.

    Три поля ввода:
    x- количество человек, принявших участие в проекте, всего(participants_number)
    z- количество человек из своего региона, принявших участие в проекте(ro_participants_number)
    y- количество дней проведения проекта(end_date - start_date)
    Количество дней проведения мероприятия рассчитываем сами, как разницу между датой окончания и датой начала.

    Все цифры в формулу берутся из корректировок ЦШ.

    """

    # TODO: написать функцию расчёта мест

    logger.info('Выполняется подсчет отчета по r5 показателю')

    ro_id = report.regional_headquarter.id
    logger.info(f'Выполняется подсчет очков для рег штаба {ro_id}')
    ro_score = 0
    # в ro_events получаем список кортежей.
    # Пример - [(34, 18, 2024-07-29, 2024-07-29), (4, 2, 2024-08-29, 2024-08-29),]

    ro_events = report.events.values_list(
        'participants_number',
        'ro_participants_number',
        'start_date',
        'end_date'
    )
    print('ro_events', ro_events)
    # вычисляем сумму очков, после цикла записываем в таблицу
    for item in ro_events:
        print('item', item)
        date_start = datetime.strptime(item[2], '%Y-%m-%d').date()
        date_end = datetime.strptime(item[3], '%Y-%m-%d').date()

        days_diff = (date_end - date_start).days + 1
        ro_score += (item[0] - item[1]) * days_diff
        print('ro_score', ro_score)
    report.score = ro_score
    report.save()
    print(report.score)
    logger.info(f'Подсчитали очки 5го показателя для рег штаба {ro_id}. Очки: {ro_score}')


def calculate_r7_score(report):
    """Расчет очков по 7 показателю.
    
    Р = (4 − m1) + (4 − m2) + (4 − mx)
    Для трудовых проектов множитель - 2.
    """
    logger.info(
        f'Рассчитываем 7 показатель для {report.regional_headquarter} отчет '
        f'по {report.__class__._meta.verbose_name} - id {report.id}. '
        f'Мероприятие {"" if report.__class__.is_labour_project else "не"} является трудовым - множитель 2. '
        f'Место: {report.prize_place}'
    )
    places_dict = {'1': 1, '2': 2, '3': 3, 'Нет': 4}
    report.score = (4 - places_dict[report.prize_place]) * (2 if report.__class__.is_labour_project else 1)
    logger.info(
        f'Финальное кол-во очков для отчета {report.id} {report.regional_headquarter} '
        f'по 7 показателю: {report.score}'
    )
    report.save()


def calculate_r9_r10_score(report):
    """Расчет очков по 9-10 показателям.
    
    Да - 0 баллов.
    Нет - 1 балл.
    """
    logger.info(
        f'Рассчитываем 9 показатель для {report.regional_headquarter} отчет '
        f'по {report.__class__._meta.verbose_name} - id {report.id}. '
        f'Мероприятие состоялось: {report.event_happened}'
    )
    report.score += 1 if report.event_happened else 0
    report.save()


def calculate_r16_score(report: RegionalR16):
    """Расчет очков по 16 показателю.
    

    """
    points = {'Всероссийский': 2, 'Окружной': 1.5, 'Межрегиональный': 1}
    logger.info(
        f'Рассчитываем 16 показатель для {report.regional_headquarter} отчет '
        f'по {report.__class__._meta.verbose_name} - id {report.id}. '
        f'Мероприятие состоялось: {report.event_happened}'
    )
    projects = report.projects
    for project in projects:
       report.score += points[project.project_scale]
       logger.info(
           f'Найден трудовой проект для id {report.id} - {project.name}. Масштаб проекта: {project.project_scale}'
        )
    report.save()


def calculate_r14():
    """Расчет очков по 14 показателю."""
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
