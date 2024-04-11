import os
from datetime import datetime as dt

from django.db.models import Q
from django.utils import timezone


def format_filename(filename):
    """Функция для форматирования имени файла."""
    current_time = str(timezone.now().strftime('%Y%m%d%H%M%S'))
    current_time = 'ksk'
    return f"{current_time}_{filename}"


def create_directory_if_not_exists(path):
    """Функция для создания директории, если ее нет."""
    if not os.path.exists(path):
        os.makedirs(path)


def get_certificate_scans_path(instance, filename):
    """
    Функция для получения пути к сканам грамот и сертификатов.

    :param instance: Экземпляр модели.
    :param filename: Имя файла. Добавляем к имени текущую дату и время.
    :return: Путь к изображению.
    Сохраняем в filepath/{instance.__class__.__name__}/filename
    """
    model_name = instance.__class__.__name__
    filename = format_filename(filename)
    filepath = os.path.join('competitions/certificates_scans', model_name)
    create_directory_if_not_exists(filepath)
    return os.path.join(filepath, filename)


def document_path(instance, filename):
    """Функция для формирования пути сохранения сканов документов юзера.

    :param instance: Экземпляр модели.
    :param filename: Имя файла. Добавляем к имени текущую дату и время.
    :return: Путь к скану документа.
    Сохраняем в filepath/{instance.name}/filename
    """

    filename = dt.today().strftime('%Y%m%d%H%M%S') + '_' + filename[:15]
    filepath = 'documents/users'
    return os.path.join(filepath, instance.user.username, filename)


def round_math(num, decimals=0):
    """
    Функция математического округления.

    :param num: округляемое число
    :param decimals: количество знаков после запятой
    :return: округленное число

    Решает проблему округления round(2.5) = 2
    (округления к ближайшему четному)
    """
    if isinstance(num, int):
        return num
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    if not isinstance(decimals, int):
        raise ValueError("decimal places has to be an integer")
    factor = int('1' + '0' * decimals)
    return int(num * factor + 0.5) / factor


def tandem_or_start(competition, detachment, competition_model) -> bool:
    """Вычисление Тандем | Старт."""

    is_tandem = False
    try:
        if ((competition_model.objects.filter(
            competition=competition,
            detachment=detachment
        ).exists())
         or (
            competition_model.objects.filter(
                competition=competition,
                junior_detachment=detachment
            ).exclude(detachment=None)
        )):
            is_tandem = True
    except (competition_model.DoesNotExist, ValueError):
        is_tandem = False
    return is_tandem


def get_place_q2(
        commander_achievment: bool, commissioner_achievement: bool
) -> int:
    """Определение места по показателю 2."""

    PLACE_FIRST = 1
    PLACE_SECOND = 2
    PLACE_THIRD = 3

    place = PLACE_THIRD
    if commander_achievment and commissioner_achievement:
        place = PLACE_FIRST
    if (
        commander_achievment and not commissioner_achievement
    ) or (
        not commander_achievment and commissioner_achievement
    ):
        place = PLACE_SECOND
    return place


def is_main_detachment(
        competition_id, detachment_id, competition_model
) -> bool:
    """Определение типа отряда."""
    if competition_model.objects.filter(
            competition=competition_id,
            detachment=detachment_id
    ).exists():
        return True
    return False


def assign_ranks(scores) -> list:
    """Функция формирования списка мест.

    На вход список кортежей (ID, score).
    На выход список кортежей (ID, rank).
    """

    # Сначала сортируем список кортежей по второму элементу (очкам)
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    # Переменные для отслеживания текущего ранга и предыдущего результата
    current_rank = 1
    previous_score = None
    ranked_scores = []

    # Проходим по отсортированному списку
    for index, (id, score) in enumerate(sorted_scores):
        if score != previous_score:
            # Если очки не совпадают с предыдущими, обновляем текущий ранг
            current_rank = index + 1
        ranked_scores.append((id, current_rank))
        previous_score = score

    # Сортируем результат обратно по ID
    ranked_scores.sort(key=lambda x: x[0])

    return ranked_scores


def find_second_element_by_first(tuple_list, first_element) -> int | None:
    """Функция для поиска второго элемента по первому внутри списка кортежей.

    Используется для возвращения номера парного отряда в Тандеме.
    """

    for item in tuple_list:
        if item[0] == first_element:
            return item[1]
    return None
