import logging
from datetime import datetime

from headquarters.models import RegionalHeadquarter
from regional_competitions_2025.constants import (MEMBER_FEE, MSK_ID, SPB_ID,
                                                  ro_members_in_rso_vk)
from regional_competitions_2025.models import (BaseRegionalR6, Ranking,
                                               RegionalR1, RegionalR3,
                                               RegionalR4, RegionalR11,
                                               RegionalR12, RegionalR13,
                                               RegionalR14)
from regional_competitions_2025.utils import (get_current_year,
                                              get_participants, log_exception)

logger = logging.getLogger('regional_tasks')


@log_exception
def calculate_r1_score(report: RegionalR1):
    """Расчет очков для отчета 1 показателя."""

    report.score = report.participants_with_payment
    if report.top_must_pay:
        report.score -= report.top_participants
    if report.foreign_must_pay:
        report.score -= report.foreign_participants
    report.save()


@log_exception
def calculate_r2_score(report):
    """Расчет очков по 2 показателю.

    P=x/(y/z)
    x - Члены РО;
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
    participants = get_participants(report, RegionalR1)
    if not participants:
        logger.info(f'Не удалось получить кол-во участников с уплаченными взносами в r2 из r1 для рег штаба {ro_id}')
        return
    regional_coef = 2 if ro_region == MSK_ID else 1.5 if ro_region == SPB_ID else 1
    ro_score = participants / (report.full_time_students / regional_coef)
    report.score = ro_score
    report.save()
    logger.info(f'Подсчитали очки 2-го показателя для рег штаба {ro_id}. Очки: {ro_score}')


def calculate_r3_score(report: RegionalR3):
    """
    Новый расчет очков по 3 показателю:
    P3 = X1 / X2

    Где:
    X1 — трудоустроенные члены РО РСО (employed_members)
    X2 — общее количество членов РО РСО (из RegionalR1.score)
    """
    logger.info(f'Выполняется подсчет P3 для {report.regional_headquarter}')
    x1 = report.employed_members or 0
    regional_r1 = RegionalR1.objects.filter(
        r_competition__year=2025,
        regional_headquarter=report.regional_headquarter
    ).first()
    if not regional_r1:
        logger.warning(f'Региональный отчет R1 за 2025 год для {report.regional_headquarter} не найден. P3 = 0')
        report.score = 0
        report.save()
        return
    x2 = regional_r1.score or 0
    if x2 == 0:
        logger.warning(f'x2 (общее количество членов) = 0 для {report.regional_headquarter}. Деление невозможно. P3 = 0')
        report.score = 0
    else:
        report.score = round(x1 / x2, 4)
    report.save()
    logger.info(f'Подсчитали P3 для РШ {report.regional_headquarter}: {report.score}')


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
    """
    Расчет очков для 6-го показателя.
    Итоговый показатель = number_of_members + 2 * hq_members_count (если is_hq_member=True).
    """
    logger.info(f'Выполняется подсчет P6 для {report.regional_headquarter}')
    members = report.number_of_members or 0
    hq_members = (report.hq_members_count or 0) if report.is_hq_member else 0
    report.score = members + 2 * hq_members
    report.save()
    logger.info(f'Подсчитали P6 для {report.regional_headquarter}: {report.score}')


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
    Z = X/K
    X - количество человек, входящих в группу РСО в социальной сети «Вконтакте» (http://vk.com/rso_official);
    K - количество членов РО РСО. Данное значение берется из показателя №1.  
    После получения коэффициента Z происходит сравнение данных коэффициентов между различными региональными отделениями РСО и определяется место, которое заняло каждое конкретное РО (при этом 1 место занимает РО с наименьшим значением коэффициента Z).
    Обозначим номер занятого места место как Z’ и тогда:
    𝑃11 = Z’+Y, где:
    Y - показатель оценки региональной группы РО РСО в социальной сети «Вконтакте». Определяется на основании комплексного анализа технологической компании «VK» с распределением мест по каждому региональному отделению. 
    """

    r1_ro_ids = set(RegionalR1.objects.filter(
        verified_by_chq=True,
        score__gt=0
    ).values_list('regional_headquarter_id', flat=True))

    r11_ro_ids = set(RegionalR11.objects.filter(
        verified_by_chq=True
    ).values_list('regional_headquarter_id', flat=True))
    ro_ids = r1_ro_ids.intersection(r11_ro_ids)

    r1_reports = RegionalR1.objects.filter(
        regional_headquarter_id__in=ro_ids,
        verified_by_chq=True,
        score__gt=0
    )

    r11_reports = RegionalR11.objects.filter(
        regional_headquarter_id__in=ro_ids,
        verified_by_chq=True,
    )

    r1_scores = {report.regional_headquarter_id: report.score for report in r1_reports}

    z_scores = []
    updated_r11_reports = []
    for report in r11_reports:
        ro_id = report.regional_headquarter_id
        x = ro_members_in_rso_vk.get(ro_id, 0)
        k = r1_scores.get(ro_id, 1)
        y = report.participants_number or 0

        logger.info(f'Выполняется подсчет Z для рег штаба {ro_id}')

        if k == 0:
            logger.warning(f'K = 0 для рег штаба {ro_id}. Установлено Z = 0.')
            z = 0
        else:
            z = round(x / k, 2)

        z_scores.append((report, z))
        report_data = {'report': report, 'y': y}
        updated_r11_reports.append(report_data)

    z_scores.sort(key=lambda x: x[1])
    for rank, (report, z) in enumerate(z_scores, 1):
        for report_data in updated_r11_reports:
            if report_data['report'] == report:
                report_data['z_res'] = rank
                logger.info(f'Рег штаб {report.regional_headquarter_id}: Z = {z}, Z\' = {rank}')

    for report_data in updated_r11_reports:
        report = report_data['report']
        z_res = report_data['z_res']
        y = report_data['y']
        report.score = z_res + y
        logger.info(f'Подсчитали P11 для рег штаба {report.regional_headquarter_id}: P11 = {z_res} + {y} = {report.score}')

    try:
        updated_count = RegionalR11.objects.bulk_update([report_data['report'] for report_data in updated_r11_reports], ['score'])
        logger.info(f'Расчет P11 завершен, обновлено {updated_count} отчетов')
    except Exception as e:
        logger.error(f'Расчет r11 показателя завершен с ошибкой: {e}')


@log_exception
def calculate_r12_score():
    """
    Показатель 𝑃12 – это коэффициент, который рассчитывается путем среднего арифметического трех абсолютных значений. 

    K1 – объем средств, собранных бойцами РО РСО на Всероссийском дне ударного труда. Предоставляет данные - РСО.
    После получения значения K1 происходит сравнение всех значений между различными региональными отделениями РСО и
    определяется место, которое заняло каждое конкретное РО.
    Номер занятого места обозначим K’1 (1 место занимает РО, имеющее наибольшее значение).

    K2 = x/y, где:
    x – количество членов РО РСО, принявших участие во Всероссийском дне ударного труда.
    y – численность членов РО РСО (берём подтвержденную цифру из 1-го показателя/50).
    После получения значения K2 происходит сравнение всех данных значений между различными региональными отделениями РСО
    и определяется место, которое заняло каждое конкретное РО. Номер занятого места обозначим K’2  (1 место занимает РО,
    имеющее наименьшее значение).

    K3 = K1 /x
    После получения значения K3 происходит сравнение всех данных значений между различными региональными отделениями РСО
    и определяется место, которое заняло каждое конкретное РО. Номер занятого места обозначим K’3 (1 место занимает РО,
    имеющее наименьшее значение).

    Финальный подсчет показателя происходит по следующей формуле:

    𝑃12 = (K’1 + K’2 + K’3) / 3
    В этой калькуляции разворачиваем места наоборот, т.е. 1 место - это наибольшее значение. Это нужно для того, чтобы
    в итоговой функции расчета места, мы могли использовать тот же метод, что и для остальных показателей.
    """
    logger.info('Выполняется подсчет очков по r12 показателю')
    sorted_ids_k1 = []
    sorted_ids_k2 = []
    sorted_ids_k3 = []
    k2_dict = {}
    k3_dict = {}
    result_places = {}

    reports_qs = RegionalR12.objects.filter(verified_by_chq=True, r_competition__year=get_current_year())
    sorted_ids_k1 = list(
        reports_qs.order_by('-amount_of_money').values_list('regional_headquarter_id', flat=True)
    )
    for report in reports_qs:
        r1_report = RegionalR1.objects.filter(
            regional_headquarter=report.regional_headquarter, verified_by_chq=True
        ).first()
        if r1_report:
            all_ro_members = r1_report.score
            if all_ro_members == 0:
                continue
            k2_dict[report.regional_headquarter_id] = round(report.amount_of_money / all_ro_members, 4)
        else:
            k2_dict[report.regional_headquarter_id] = 0
        number_of_members = report.number_of_members
        if number_of_members == 0:
            continue
        k3_dict[report.regional_headquarter_id] = round(report.amount_of_money / number_of_members, 4)

    sorted_ids_k2 = sorted(k2_dict.keys(), key=lambda x: k2_dict[x], reverse=True)
    sorted_ids_k3 = sorted(k3_dict.keys(), key=lambda x: k3_dict[x], reverse=True)

    for id in reports_qs.values_list('regional_headquarter_id', flat=True):
        k1_place = sorted_ids_k1.index(id) + 1 if id in sorted_ids_k1 else len(sorted_ids_k1) + 1
        k2_place = sorted_ids_k2.index(id) + 1 if id in sorted_ids_k2 else len(sorted_ids_k2) + 1
        k3_place = sorted_ids_k3.index(id) + 1 if id in sorted_ids_k3 else len(sorted_ids_k3) + 1
        result_places[id] = (k1_place + k2_place + k3_place) / 3
    sorted_result_ids = sorted(result_places.keys(), key=lambda x: result_places[x], reverse=True)

    for report in reports_qs:
        regional_hq_id = report.regional_headquarter_id
        if regional_hq_id not in sorted_result_ids:
            continue
        report.score = sorted_result_ids.index(regional_hq_id)
        report.save()
    logger.info('Расчет r12 показателя завершен')


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
    # формула - number_of_members_r13/(score_r1/50)
    updated_r13_reports = []
    for report in r13_reports:
        if type(report.number_of_members) is not int:
            report.number_of_members = 0
        report.score = report.number_of_members / (
            r1_scores[report.regional_headquarter_id] / MEMBER_FEE
        ) if report.number_of_members > 0 else 0
        updated_r13_reports.append(report)
    try:
        updated_r13_reports = RegionalR13.objects.bulk_update(updated_r13_reports, ['score'])
    except Exception as e:
        logger.error(f'Расчет r13 показателя завершен с ошибкой: {e}')

    logger.info(f'Расчет r13 показателя завершен, обновлено {updated_r13_reports} отчетов')


@log_exception
def calculate_r14_score(report: RegionalR14):
    """Расчет очков по 14 показателю.
    P=l+m+n
    l, m, n - победы линейного студенческого отряда на трудовом проекте по комиссарской деятельности.
    За всероссийский трудовой проект отряду начисляется 2 балла.
    За окружной трудовой проект отряду начисляется 1,5 балла.
    За межрегиональный трудовой проект отряду начисляется 1 балл.
    """
    points = {'Всероссийский': 2, 'Окружной': 1.5, 'Межрегиональный': 1}
    logger.info(
        f'Рассчитываем 14 показатель для {report.regional_headquarter} отчет '
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


def calc_r_ranking(
    report_models: list, ranking_field_name: str, score_field_name: str, reverse=True, no_verification=False
):
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
