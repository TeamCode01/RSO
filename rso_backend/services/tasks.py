import logging
from datetime import datetime as dt

from celery import shared_task

from services.models import FrontError

logger = logging.getLogger('tasks')


@shared_task
def delete_front_logs():
    """Удаляет логи отчетов за прошлую неделю."""

    last_week = dt.now() - dt(days=7)
    FrontError.objects.filter(created__lt=last_week).delete()
    logger.info('Успешно удалены логи отчетов за прошлую неделю.')
