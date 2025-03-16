import logging
from datetime import timedelta

from celery import shared_task

from django.utils import timezone

from services.models import FrontError

logger = logging.getLogger('tasks')


@shared_task
def delete_front_logs():
    """Удаляет логи отчетов за прошлую неделю."""

    last_week = timezone.now() - timedelta(days=7)
    FrontError.objects.filter(created_at__lt=last_week).delete()
    logger.info('Успешно удалены логи отчетов за прошлую неделю.')
