import logging
import traceback
from datetime import date, timedelta

from celery import shared_task

from regional_competitions.constants import EMAIL_REPORT_PART_1_MESSAGE
from regional_competitions.models import StatisticalRegionalReport
from regional_competitions.r_calculations import calculate_r14
from regional_competitions.utils import generate_pdf_report_part_1, send_email_with_attachment, get_emails

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
    except Exception as e:
        err_traceback = traceback.format_exc()
        logger.critical(f'UNEXPECTED ERROR send_email_report_part_1: {e}.\n{err_traceback}')


@shared_task
def send_email_report_part_2(report_id: int):
    pass


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
