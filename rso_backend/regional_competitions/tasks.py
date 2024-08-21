import logging
import os
import traceback
from datetime import date, timedelta

from celery import shared_task
from django_celery_beat.models import PeriodicTask

from regional_competitions.constants import EMAIL_REPORT_PART_1_MESSAGE, \
    EMAIL_REPORT_PART_2_MESSAGE
from regional_competitions.models import StatisticalRegionalReport, REPORTS_IS_SENT_MODELS
from regional_competitions.r_calculations import calculate_r14
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
        logger.info(
            f'Региональный штаб ID {regional_headquarter_id} отправил часть '
            f'показателей по 2-й части отчета на верификацию...'
        )
        not_sent_exists = False
        for model in REPORTS_IS_SENT_MODELS:
            if not hasattr(model, 'is_sent'):
                continue

            logger.info(f'Проверяем {model._meta.verbose_name} для РШ ID {regional_headquarter_id}')

            try:
                instance = model.objects.get(regional_headquarter_id=regional_headquarter_id)
            except model.DoesNotExist:
                not_sent_exists = True
                logger.warning(
                    f'Региональный штаб ID {regional_headquarter_id} НЕ! '
                    f'приступил к заполнению {model._meta.verbose_name}'
                )
                continue

            if instance.is_sent:
                logger.info(
                    f'Региональный штаб ID {regional_headquarter_id} отправил {model._meta.verbose_name} на верификацию'
                )
            else:
                not_sent_exists = True
                logger.warning(
                    f'Региональный штаб ID {regional_headquarter_id} НЕ! отправил '
                    f'{model._meta.verbose_name} на верификацию'
                )

        if not not_sent_exists:  # !!! Можно добавить not (для удобного тестирования генерации файла)
            logger.warning(
                f'Не отправляем письмо региональному штабу ID {regional_headquarter_id}, '
                f'т.к. есть неотправленные отчеты'
            )
            return

        logger.info(f'Подготавливаем PDF-файл для регионального штаба ID {regional_headquarter_id}')
        pdf_file = generate_pdf_report_part_2(regional_headquarter_id)
        logger.info(f'Отправляем PDF-файл для регионального штаба ID {regional_headquarter_id}')
        send_email_with_attachment(
            subject='Получен отчет о деятельности регионального отделения РСО за 2024 год - часть 2',
            message=EMAIL_REPORT_PART_2_MESSAGE,
            recipients=get_emails(regional_headquarter_id),
            file_path=pdf_file
        )
        os.remove(pdf_file)
        logger.info(
            f'ПДФ успешно отправлен региональному штабу ID {regional_headquarter_id}. '
            f'Удалили файл и удаляем периодическую задачу.'
        )
        try:
            PeriodicTask.objects.get(name=f'Send Email to reg hq id {regional_headquarter_id}').delete()
        except PeriodicTask.DoesNotExist:
            logger.warning(
                f'Не удалось удалить периодическую задачу для регионального штаба ID {regional_headquarter_id}'
            )
    except Exception as e:
        err_traceback = traceback.format_exc()
        logger.critical(f'UNEXPECTED ERROR send_email_report_part_2: {e}.\n{err_traceback}')


@shared_task
def calculate_q14_report_task():
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
