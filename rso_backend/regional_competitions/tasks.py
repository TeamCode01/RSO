import logging
import os
import traceback
from datetime import date, timedelta

from celery import shared_task
from django_celery_beat.models import PeriodicTask

from headquarters.models import RegionalHeadquarter
from regional_competitions.constants import EMAIL_REPORT_PART_1_MESSAGE, \
    EMAIL_REPORT_PART_2_MESSAGE
from regional_competitions.models import StatisticalRegionalReport, REPORTS_IS_SENT_MODELS
from regional_competitions.r_calculations import calculate_r11_score, calculate_r13_score, calculate_r14
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
            f'показателей по 2-й части отчета на верификацию...'
        )
        not_sent_exists = False
        for model in REPORTS_IS_SENT_MODELS:
            if not hasattr(model, 'is_sent'):
                continue

            logger.info(f'Проверяем {model._meta.verbose_name} для РШ {regional_headquarter}')

            try:
                instance = model.objects.get(regional_headquarter_id=regional_headquarter_id)
            except model.DoesNotExist:
                not_sent_exists = True
                logger.warning(
                    f'Региональный штаб {regional_headquarter} НЕ! '
                    f'приступил к заполнению {model._meta.verbose_name}'
                )
                continue

            if instance.is_sent:
                logger.info(
                    f'Региональный штаб {regional_headquarter} отправил {model._meta.verbose_name} на верификацию'
                )
            else:
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
            recipients=get_emails(regional_headquarter_id),
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
    cutoff_date = date(2024, 10, 15)

    if today <= cutoff_date + timedelta(days=1):
        calculate_r14()
    else:
        logger.warning('Истек срок выполнения подсчета по 14 показателю')
