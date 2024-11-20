import logging
from datetime import datetime

from headquarters.models import RegionalHeadquarter

from regional_competitions.constants import MSK_ID, SPB_ID, ro_members_in_rso_vk
from regional_competitions.models import (Ranking, RegionalR1, RegionalR11, RegionalR4, RegionalR12, RegionalR13,
                                          RegionalR14, RegionalR16)
from regional_competitions.utils import get_fees, log_exception

logger = logging.getLogger('regional_tasks')


@log_exception
def calculate_r1_score(report: RegionalR1):
    """Расчет очков для отчета 1 показателя."""
    report.score = report.amount_of_money
    report.save()


@log_exception
def calculate_r2_score(report):
    """Расчет очков по 2 показателю.

    P=(x/50)/(y/z)
    x - Уплаченные членские взносы из первого показателя;
    50 - коэффициент для определения количества человек, уплативших взносы;
    y - Численность студентов очной формы обучения субъекта РФ (константа, которую сбросит ЦШ);
    z - Коэффициент для региональной поправки. Для МСК равен 2, для СПБ равен 1,5, для остальных регионов равен 1.

    !!! Расчёт вызывается через админку.
    """

    if type(report.full_time_students) is not int:
        logger.info(f'Не удалось получить численность студентов для рег штаба {report.regional_headquarter.id}')
        return
    ro_id = report.regional_headquarter.id
    ro_region = report.regional_headquarter.region.id

    logger.info(f'Выполняется подсчет очков r2 для рег штаба {ro_id}')
    amount_of_money = get_fees(report, RegionalR1)
    if not amount_of_money:
        logger.info(f'Не удалось получить сумму взносов в r2 из r1 для рег штаба {ro_id}')
        return
    regional_coef = 2 if ro_region == MSK_ID else 1.5 if ro_region == SPB_ID else 1
    ro_score = (amount_of_money / 50) / (report.full_time_students / regional_coef)
    report.score = ro_score
    report.save()
    logger.info(f'Подсчитали очки 2-го показателя для рег штаба {ro_id}. Очки: {ro_score}')


@log_exception
def calculate_r3_score(report):
    """Расчет очков по 3 показателю.

    P3= ((X1-X2)/X2)*100%, где
    X1- численность членов РО РСО за 2024 г., оплативших ЧВ (по данным ЦШ) (сумма из 1 показателя/50)
    X2- Численность членов РО РСО за 2023 г., оплативших ЧВ (по данным ЦШ)

    Расчёт вызывается через админку и 15 октября 2024 года.
    """
    logger.info(f'Выполняется подсчет очков r3 для РШ {report.regional_headquarter}')
    amount_of_money = get_fees(report, RegionalR1)
    ro_score = (
        (amount_of_money / 50) / 
        (report.amount_of_membership_fees_2023 if report.amount_of_membership_fees_2023 > 0 else 1)
    )
    report.score = ro_score
    report.save()
    logger.info(f'Подсчитали очки 3-го показателя для РШ {report.regional_headquarter}: {ro_score}')


@log_exception
def calculate_r4_score(report: RegionalR4):
    """Расчет очков по 4 показателю.

    P=(х1*y1)+(xn*yn)
    P=(х1*y1)+(xn*yn*0.8)

    «х1…xn» - количество человек, принявших участие в каждом мероприятии или проекте;
    «у1…yn» - количество дней проведения каждого мероприятия или проекта

    Количество дней проведения мероприятия рассчитываем сами, как разницу между датой окончания и датой начала.
    """
    if not report.verified_by_chq:
        logger.info('пропускаем подсчет - не верифицирован')
        return
    logger.info('Выполняется Расчет очков для отчета 4 показателя')
    events = report.events.all()
    logger.info(f'Для отчета {report.id} {report.regional_headquarter} найдено {events.count()} мероприятий')
    report.score = 0
    for event in events:
        if not event.end_date or not event.start_date:
            continue
        days_count = (event.end_date - event.start_date).days + 1
        report.score += (days_count * event.participants_number) * (0.8 if event.is_interregional else 1)
        logger.info(
            f'Мероприятие {event} длилось {days_count} дней с кол-вом участников в {event.participants_number} человек. '
            f'Мероприятие {"" if event.is_interregional else "не"} является межрегиональным. Отчет {report.id} теперь '
            f'имеет {report.score} очков.'
        )
    logger.info(
        f'Все мероприятия по 4 показателю рассчитаны. '
        f'Финальное кол-во очков для отчета {report.id} {report.regional_headquarter} по 4 показателю: {report.score}'
    )
    report.save()


@log_exception
def calculate_r5_score(report):
    """Расчет очков по 5 показателю."""

    logger.info('Выполняется подсчет отчета по r5 показателю')

    ro_id = report.regional_headquarter.id
    logger.info(f'Выполняется подсчет очков r5 для рег штаба {ro_id}')
    ro_score = 0

    # Получаем список кортежей с данными мероприятий.
    ro_events = report.events.values_list(
        'participants_number',
        'ro_participants_number',
        'start_date',
        'end_date'
    )

    # вычисляем сумму очков
    for item in ro_events:
        if type(item[0]) is not int or type(item[1]) is not int:
            item[0] = item[1] = 0
        date_start = item[2]
        date_end = item[3]
        if not date_end or not date_start:
            continue
        days_diff = (date_end - date_start).days + 1
        ro_score += (item[0] - item[1]) * days_diff

    report.score = ro_score
    report.save()
    logger.info(f'Подсчитали очки 5-го показателя для рег штаба {ro_id}. Очки: {ro_score}')


@log_exception
def calculate_r6_score(report):
    """Расчет очков по 6 показателю."""
    report.score = report.number_of_members if report.number_of_members else 0
    report.save()


@log_exception
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


@log_exception
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
    report.score = 0
    report.score += 1 if report.event_happened else 0
    report.save()



@log_exception
def calculate_r11_score():
    """
    Расчет очков для 11-го показателя.

    P=(x/k)+(x/2y)

    x- количество человек, входящих в группу РСО в социальной сети «Вконтакте»
    в результате проведенного опроса (анкетирования) - этот показатель ЦШ предоставляет нам централизованно.
    y - количество человек, входящих в группу РО РСО в социальной сети «Вконтакте» (подтверждение - скриншот).
    к - количество членов РО РСО в соответствии с объемом уплаченных членских взносов. (из первого показателя).
    Подтвержденный 1 показатель. (цифра из первого показателя/50)

    Примечание: Если К больше или равно 1500 и  Х > Y, то слагаемое № 2 приравнивается к 0.
    Сравнение итогов между РО, самая большая цифра - 1 место.
    """

    r1_ro_ids = set(RegionalR1.objects.filter(
        verified_by_chq=True,
        score__gt=0
    ).values_list('regional_headquarter_id', flat=True))

    r11_ro_ids = set(RegionalR11.objects.filter(score=0).values_list('regional_headquarter_id', flat=True))
    ro_ids = r1_ro_ids.intersection(r11_ro_ids)

    r1_reports = RegionalR1.objects.filter(
        regional_headquarter_id__in=ro_ids,
        verified_by_chq=True,
        score__gt=0
    )

    r11_reports = RegionalR11.objects.filter(
        regional_headquarter_id__in=ro_ids,
        verified_by_chq=True,
        score=0
    )

    r1_scores = {report.regional_headquarter_id: report.score for report in r1_reports}

    updated_r11_reports = []
    for report in r11_reports:
        if type(report.participants_number) is not int:
            report.participants_number = 0

        ro_id = report.regional_headquarter.id
        rso_vk_members = ro_members_in_rso_vk.get(ro_id, 0)

        logger.info(f'Выполняется подсчет очков r11 для рег штаба {ro_id}')

        members_with_fees = r1_scores.get(report.regional_headquarter_id, 1) / 50

        if members_with_fees >= 1500 and rso_vk_members > report.participants_number:
            ro_score = (rso_vk_members / members_with_fees)
        else:
            # Проверка на ноль для participants_number
            if report.participants_number == 0:
                second_term = 0
                logger.warning(
                    f'Количество участников равно нулю для рег штаба {ro_id}. Установлено значение второго слагаемого в 0.')
            else:
                second_term = (rso_vk_members / (2 * report.participants_number))

            ro_score = (rso_vk_members / members_with_fees) + second_term

        report.score = round(ro_score, 2)
        logger.info(f'Подсчитали очки 11-го показателя для рег штаба {ro_id}. Очки: {ro_score}')
        updated_r11_reports.append(report)

    try:
        # TODO: исправить эксепшн
        updated_r11_reports = RegionalR11.objects.bulk_update(updated_r11_reports, ['score'])
    except Exception as e:
        logger.error(f'Расчет r11 показателя завершен с ошибкой: {e}')

    logger.info(f'Расчет r11 показателя завершен, обновлено {updated_r11_reports} отчетов')


@log_exception
def calculate_r12_score(report: RegionalR12):
    """Расчет очков по 12 показателю."""
    report.score = report.amount_of_money
    report.save()


@log_exception
def calculate_r13_score():
    """
    Расчет очков по 13 показателю.

    Расчет производится после верификации 1 показателя, т.к.
    рассчитывается на основании верифицированных данных из него.
    """
    # берем все id штабов верифицированного 1 показателя
    r1_ro_ids = set(RegionalR1.objects.filter(
        verified_by_chq=True, score__gt=0).values_list('regional_headquarter_id', flat=True)
    )
    # берем все id штабов верифицированного 13 показателя, с не рассчитанными очками(равными 0)
    r13_ro_ids = set(RegionalR13.objects.filter(score=0).values_list('regional_headquarter_id', flat=True))
    # находим id штабов, с верифицированным 1 показателем и не рассчитанными очками в 13 показателе
    ro_ids = r1_ro_ids.intersection(r13_ro_ids)
    # находим отчеты по 1 показателю
    r1_reports = RegionalR1.objects.filter(regional_headquarter_id__in=ro_ids, verified_by_chq=True, score__gt=0)
    # находим отчеты по 13 показателю
    r13_reports = RegionalR13.objects.filter(regional_headquarter_id__in=ro_ids, verified_by_chq=True, score=0)
    # делаем словарь с ключ - id штаба, значение - сумма очков по 1 показателю
    r1_scores = {report.regional_headquarter_id: report.score for report in r1_reports}
    # считаем и массово присваем очки по 13 показателю.
    # формула - number_of_members_r13/(score_r1/500)
    updated_r13_reports = []
    for report in r13_reports:
        if type(report.number_of_members) is not int:
            report.number_of_members = 0
        report.score = report.number_of_members / (
            r1_scores[report.regional_headquarter_id] / 500
        ) if report.number_of_members > 0 else 0
        updated_r13_reports.append(report)
    try:
        updated_r13_reports = RegionalR13.objects.bulk_update(updated_r13_reports, ['score'])
    except Exception as e:
        logger.error(f'Расчет r13 показателя завершен с ошибкой: {e}')

    logger.info(f'Расчет r13 показателя завершен, обновлено {updated_r13_reports} отчетов')


def calculate_r14():
    """Расчет очков по 14 показателю."""
    logger.info('Выполняется подсчет отчета по r14 показателю')
    reports_to_create = []  #Список для создания отчетов перенесла в начало функции

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

        for ro in ro_reports:
            amount_of_money = ro['regionalr12__amount_of_money'] or 1
            number_of_members = ro['regionalr13__number_of_members'] or 0
            if number_of_members and amount_of_money:
                score = round(number_of_members / amount_of_money, 2)
            else:
                score = 0  # Если одно из значений None или 0, устанавливаем score 0
            reports_to_create.append(RegionalR14(
                regional_headquarter_id=ro['id'],
                report_12_id=ro['regionalr12__id'],
                report_13_id=ro['regionalr13__id'],
                score=score,
            ))

    except Exception as e:
        logger.exception(f'Не удалось подсчитать отчет по r14 показателю: {e}')

    logger.info(f'Создаем {len(reports_to_create)} отчетов по r14 показателю')
    try:
        new_reports = RegionalR14.objects.bulk_create(reports_to_create)
    except Exception as e:
        logger.exception(f'Не удалось создать отчеты по r14 показателю: {e}')

    logger.info(f'Завершен подсчет отчета по r14 показателю. Создано {len(new_reports)} отчетов')


@log_exception
def calculate_r16_score(report: RegionalR16):
    """Расчет очков по 16 показателю.


    """
    points = {'Всероссийский': 2, 'Окружной': 1.5, 'Межрегиональный': 1}
    logger.info(
        f'Рассчитываем 16 показатель для {report.regional_headquarter} отчет '
        f'по {report.__class__._meta.verbose_name} - id {report.id}. '
    )
    projects = report.projects.all()
    report.score = 0
    for project in projects:
        try:
            report.score += points[project.project_scale]
        except KeyError:
            continue
        logger.info(
           f'Найден трудовой проект для id {report.id} - {project.name}. Масштаб проекта: {project.project_scale}'
        )
    report.save()


def calc_r_ranking(report_models: list, ranking_field_name: str, score_field_name: str, reverse=True, no_verification=False):
    """
    Расчет места для региональных отчетов.

    :param report_models: Список с моделями отчетов, по которым суммируются score
    :param ranking_field_name: Имя поля в модели Ranking, куда записываем место
    :param score_field_name: Имя поля в модели Ranking, куда записываем общие очки
    :param reverse: Если True, то чем больше очков, тем выше место, по дефолту True
    :param no_verification: Если True, то берутся все записи из модели, без фильтрации по verified_by_chq=True
    """
    entries = {}
    try:
        # вытащим все записи из моделей
        for report_model in report_models:
            if no_verification is False:
                model_entries = report_model.objects.filter(
                    verified_by_chq=True,
                ).values(
                    'regional_headquarter_id',
                    'score',
                )
            else:
                model_entries = report_model.objects.values(
                    'regional_headquarter_id',
                    'score',
                )
            # пройдемся по каждой записи всех моделей, просуммируем score
            # наполним entries словарем с ключом - id штаба, значениями - суммы очков
            for model_entry in model_entries:
                entry = entries.get(model_entry['regional_headquarter_id'])
                if entry is None:
                    entries[model_entry['regional_headquarter_id']] = model_entry['score']
                else:
                    entries[model_entry['regional_headquarter_id']] += model_entry['score']

        # отсортируем словарь по возрастанию или убыванию в зависимости от reverse (по дефолту по возрастанию)
        sorted_entries = sorted(entries.items(), key=lambda x: x[1], reverse=reverse)  # отсортированный список кортежей (id штаба, общий score)

        # присвоим места, тащим все записи модели учета рейтинга Ranking
        # присвоим места согласно порядку сортировки, если score одинаковые - присвоим одинаковое место
        # если записи нет - создаем ее
        ranking_entries = Ranking.objects.filter(
            regional_headquarter_id__in=[entry[0] for entry in sorted_entries],
        )

        temp_place = 0
        temp_score = float('-inf') if reverse else float('inf')
        to_create_entries = []
        to_update_entries = []
        for entry in sorted_entries:
            ranking_entry = ranking_entries.filter(regional_headquarter_id=entry[0]).first()
            # считаем место, если очки одинаковые с прежней записью - присвоим одинаковое место
            if temp_score == entry[1]:
                place = temp_place
            else:
                temp_score = entry[1]
                temp_place += 1
                place = temp_place

            # если у рег штаба еще нет записи в таблице - создаем ее
            if not ranking_entry:
                ranking_entry = Ranking(regional_headquarter_id=entry[0])
                setattr(ranking_entry, ranking_field_name, place)
                setattr(ranking_entry, score_field_name, entry[1])
                to_create_entries.append(ranking_entry)
            else:
                setattr(ranking_entry, ranking_field_name, place)
                setattr(ranking_entry, score_field_name, entry[1])
                to_update_entries.append(ranking_entry)

        new_entries = Ranking.objects.bulk_create(to_create_entries)
        count_updated = Ranking.objects.bulk_update(to_update_entries, [ranking_field_name, score_field_name])

        logger.info(f'{ranking_field_name} - обновлено {count_updated} записей')
        logger.info(f'{ranking_field_name} - создано {len(new_entries)} записей')

        return new_entries

    except Exception as e:
        logger.critical(f'UNEXPECTED ERROR calc_r_ranking: {e}')


def update_all_ranking_places():
    """
    Обновляет итоговые показатели (места и суммы мест) для всех записей модели Ranking.
    """
    from regional_competitions.models import Ranking

    queryset = Ranking.objects.all()
    rankings = list(queryset)

    k_indexes = [6, 7, 8, 9, 10, 11, 13, 16]
    for ranking in rankings:
        ranking.sum_overall_place = sum(
            getattr(ranking, f'r{i}_place') or 0 for i in range(1, 17)
        )
        ranking.sum_k_place = sum(
            getattr(ranking, f'r{i}_place') or 0 for i in k_indexes
        )

    # Сортируем по sum_overall_place
    rankings.sort(key=lambda x: x.sum_overall_place)

    # Присваиваем overall_place с учётом одинаковых сумм
    current_place = 1
    for idx, ranking in enumerate(rankings):
        if idx > 0 and ranking.sum_overall_place != rankings[idx - 1].sum_overall_place:
            current_place += 1
        ranking.overall_place = current_place

    # Сортируем по sum_k_place
    rankings.sort(key=lambda x: x.sum_k_place)

    # Присваиваем k_place с учётом одинаковых сумм
    current_place = 1
    for idx, ranking in enumerate(rankings):
        if idx > 0 and ranking.sum_k_place != rankings[idx - 1].sum_k_place:
            current_place += 1
        ranking.k_place = current_place

    Ranking.objects.bulk_update(
        rankings,
        ['overall_place', 'k_place', 'sum_overall_place', 'sum_k_place']
    )
