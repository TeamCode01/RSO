from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class DataBaseStorage(S3Boto3Storage):
    bucket_name = settings.DATABASE_BUCKET_NAME  # Бакет для хранения бэкапов
    default_acl = 'private'  # Доступ к бэкапам должен быть ограничен
    file_overwrite = False  # Каждый бэкап должен сохраняться отдельно
