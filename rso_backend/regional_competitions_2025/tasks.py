import logging
import os
import traceback
from datetime import date, timedelta

from celery import shared_task
from django_celery_beat.models import PeriodicTask

from headquarters.models import RegionalHeadquarter
from regional_competitions.constants import EMAIL_REPORT_PART_1_MESSAGE, \
    EMAIL_REPORT_PART_2_MESSAGE
from regional_competitions.models import (
    RegionalR1, RegionalR101, RegionalR102, RegionalR11, RegionalR12, RegionalR14, RegionalR2, RegionalR3, RegionalR4, RegionalR5,
    StatisticalRegionalReport, REPORTS_IS_SENT_MODELS, r6_models_factory,
    r9_models_factory
)
from regional_competitions.r_calculations import calc_r_ranking, calculate_r11_score, calculate_r13_score, calculate_r14
from regional_competitions.utils import generate_pdf_report_part_1, send_email_with_attachment, get_emails, \
    generate_pdf_report_part_2

logger = logging.getLogger('regional_tasks')


@shared_task
def send_email_report_part_1(report_id: int):
    try:
        logger.info(f'Подготавливаем PDF-файл с отправкой на email для report id {report_id}')
        report = StatisticalRegionalReport.objects.get(pk=report_id)
        logger.info(f'Нашли отчет с данным ID: {report}')
        pdf_file = generate_pdf_report_part_1(report)
        send_email_with_attachment(
            subject='Получен отчет о деятельности регионального отделения РСО за 2024 год - часть 1',
            message=EMAIL_REPORT_PART_1_MESSAGE,
            recipients=get_emails(report),
            file_path=pdf_file
        )
        os.remove(pdf_file)
    except Exception as e:
        err_traceback = traceback.format_exc()
        logger.critical(f'UNEXPECTED ERROR send_email_report_part_1: {e}.\n{err_traceback}')


@shared_task
def send_email_report_part_2(regional_headquarter_id: int):
    try:
        regional_headquarter = RegionalHeadquarter.objects.get(id=regional_headquarter_id)
    except RegionalHeadquarter.DoesNotExist:
        logger.critical(f'Не удалось найти РШ с id {regional_headquarter_id} для отправки отчета 2 ч.')
        return
    try:
        logger.info(
            f'Региональный штаб {regional_headquarter} отправил часть '
            f'показателей по 2-й части отчета на верификацию... Проверяем отправку'
        )
        not_sent_exists = False
        for model in REPORTS_IS_SENT_MODELS:
            if not hasattr(model, 'is_sent'):
                continue

            instance = model.objects.filter(
                regional_headquarter_id=regional_headquarter_id,
                is_sent=True
            ).last()
            if not instance:
                # not_sent_exists = True
                # logger.warning(
                #     f'Региональный штаб {regional_headquarter} НЕ! '
                #     f'приступил к заполнению {model._meta.verbose_name}'
                # )
                continue

            if not instance.is_sent:
                not_sent_exists = True
                logger.warning(
                    f'Региональный штаб {regional_headquarter} НЕ! отправил '
                    f'{model._meta.verbose_name} на верификацию'
                )

        if not_sent_exists:  # !!! Можно добавить not (для удобного тестирования генерации файла)
            logger.warning(
                f'Не отправляем письмо региональному штабу {regional_headquarter}, '
                f'т.к. есть неотправленные отчеты'
            )
            return

        logger.info(f'Подготавливаем PDF-файл 2 части отчета для регионального штаба {regional_headquarter}')
        pdf_file_p2 = generate_pdf_report_part_2(regional_headquarter_id)
        logger.info(f'Подготавливаем PDF-файл 1 части отчета для регионального штаба {regional_headquarter}')
        statistical_report = StatisticalRegionalReport.objects.filter(
            regional_headquarter_id=regional_headquarter_id
        ).last()
        pdf_file_p1 = None
        if statistical_report:
            pdf_file_p1 = generate_pdf_report_part_1(statistical_report.id)
        else:
            logger.warning(
                f'PDF-файл 1 части отчета для регионального штаба {regional_headquarter} не найден. '
                f'Отправляем только вторую часть'
            )
        logger.info(f'Отправляем PDF-файлы для регионального штаба {regional_headquarter}')
        send_email_with_attachment(
            subject='Получен отчет о деятельности регионального отделения РСО за 2024 год - часть 2',
            message=EMAIL_REPORT_PART_2_MESSAGE,
            recipients=get_emails(regional_headquarter),
            file_path=pdf_file_p2,
            additional_file_path=pdf_file_p1
        )
        os.remove(pdf_file_p2)
        if pdf_file_p1:
            os.remove(pdf_file_p1)
        logger.info(
            f'ПДФ успешно отправлен региональному штабу {regional_headquarter}. '
            f'Удалили файл и удаляем периодическую задачу.'
        )

        try:
            PeriodicTask.objects.get(name=f'Send Email to reg hq id {regional_headquarter_id}').delete()
        except PeriodicTask.DoesNotExist:
            logger.warning(
                f'Не удалось удалить периодическую задачу для регионального штаба {regional_headquarter}'
            )

    except Exception as e:
        err_traceback = traceback.format_exc()
        logger.critical(f'UNEXPECTED ERROR send_email_report_part_2: {e}.\n{err_traceback}')


@shared_task
def send_mail(subject: str, message: str, recipients: list, file_path: str):
    send_email_with_attachment(subject=subject, message=message, recipients=recipients, file_path=file_path)


@shared_task
def calculate_r11_report_task():
    """
    Считает отчет по 11 показателю.

    Подсчет до 15 октября 2024 года включительно.
    """
    today = date.today()
    cutoff_date = date(2024, 10, 15)

    if today <= cutoff_date + timedelta(days=1):
        calculate_r11_score()
    else:
        logger.warning('Истек срок выполнения подсчета по 11 показателю')


@shared_task
def calculate_r13_report_task():
    """
    Считает отчет по 13 показателю.

    Считает вплоть до 15 октября 2024 года включительно.
    """
    today = date.today()
    cutoff_date = date(2024, 10, 15)

    if today <= cutoff_date + timedelta(days=1):
        calculate_r13_score()
    else:
        logger.warning('Истек срок выполнения подсчета по 13 показателю')


@shared_task
def calculate_r14_report_task():
    """
    Считает отчет по 14 показателю.

    Считает вплоть до 15 октября 2024 года включительно.
    """
    today = date.today()
    cutoff_date = date(2024, 11, 21)

    if today <= cutoff_date + timedelta(days=1):
        calculate_r14()
    else:
        logger.warning('Истек срок выполнения подсчета по 14 показателю')


@shared_task
def calc_places_r1():
    logger.info('Выполняется подсчет rank1 показателя')
    calc_r_ranking([RegionalR1], 'r1_place', 'r1_score')


@shared_task
def calc_places_r2():
    # показатель считается на основе верифицированного первого, без верификации
    logger.info('Выполняется подсчет rank2 показателя')
    calc_r_ranking([RegionalR2], 'r2_place', 'r2_score', no_verification=True)


@shared_task
def calc_places_r3():
    # показатель считается на основе верифицированного первого, без верификации
    logger.info('Выполняется подсчет rank3 показателя')
    calc_r_ranking([RegionalR3], 'r3_place', 'score', no_verification=True)


@shared_task
def calc_places_r4():
    logger.info('Выполняется подсчет rank4 показателя')
    calc_r_ranking([RegionalR4], 'r4_place', 'r4_score')


@shared_task
def calc_places_r5():
    logger.info('Выполняется подсчет rank5 показателя')
    calc_r_ranking([RegionalR5], 'r5_place', 'r5_score')


@shared_task
def calc_places_r6():
    logger.info('Выполняется подсчет rank6 показателя')
    models = [model for model_name, model in r6_models_factory.models.items() if not model_name.endswith('Link')]
    calc_r_ranking(models, 'r6_place', 'r6_score')


# @shared_task
# def calc_places_r7():
#     logger.info('Выполняется подсчет rank7 показателя')
#     models = [model for model_name, model in r7_models_factory.models.items() if not model_name.endswith('Link')]
#     calc_r_ranking(models, 'r7_place', 'r7_score')


@shared_task
def calc_places_r9():
    # ~~чем меньше score - тем выше в рейтинге~~
    # логика изменилась, чем выше score - тем выше в рейтинге
    logger.info('Выполняется подсчет rank9 показателя')
    models = [model for model_name, model in r9_models_factory.models.items() if not model_name.endswith('Link')]
    calc_r_ranking(models, 'r9_place', 'r9_score')


@shared_task
def calc_places_r10():
    # ~~чем меньше score - тем выше в рейтинге~~ + две модели по одному показателю
    # логика изменилась, чем выше score - тем выше в рейтинге
    logger.info('Выполняется подсчет rank10 показателя')
    calc_r_ranking([RegionalR101, RegionalR102], 'r10_place', 'r10_score')


@shared_task
def calc_places_r11():
    logger.info('Выполняется подсчет rank11 показателя')
    calc_r_ranking([RegionalR11], 'r11_place', 'r11_score')


@shared_task
def calc_places_r12():
    logger.info('Выполняется подсчет rank12 показателя')
    calc_r_ranking([RegionalR12], 'r12_place', 'r12_score')


@shared_task
def calc_places_r14():
    logger.info('Выполняется подсчет rank14 показателя')
    calc_r_ranking([RegionalR14], 'r14_place', 'r14_score')
