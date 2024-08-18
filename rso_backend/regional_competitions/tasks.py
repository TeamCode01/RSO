import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from django.conf import settings

from regional_competitions.r_calculations import calculate_r14

logger = logging.getLogger('tasks')


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
