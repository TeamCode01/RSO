import logging
import os

from celery import Celery, shared_task
from django.core.management import call_command


logger = logging.getLogger('tasks')

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'rso_backend.settings'
)

app = Celery('rso_backend')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


@shared_task
def run_dbbackup_task():
    logger.info('Start db backup')
    call_command('dbbackup')
    logger.info('End db backup')
