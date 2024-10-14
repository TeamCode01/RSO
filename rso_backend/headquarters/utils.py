import os
import shutil
from datetime import datetime as dt

from django.conf import settings

import pandas as pd
from sqlalchemy import create_engine, text

from users.models import UserVerificationRequest


def image_path(instance, filename):
    """Функция для формирования пути сохранения изображения.

    :param instance: Экземпляр модели.
    :param filename: Имя файла. Добавляем к имени текущую дату и время.
    :return: Путь к изображению.
    Сохраняем в filepath/{instance.id}/filename
    """

    filename = (
            dt.today().strftime('%Y%m%d%') + '_' + filename[:15] +
            filename[-5:]
    )
    filepath = 'images/headquarters'
    return os.path.join(filepath, instance.name[:15], filename)


def headquarter_media_folder_delete(instance):
    """Функция для удаления папки с изображениями.

    Удаляет папку media для всех моделей - наследников Unit.
    :param instance: Экземпляр модели.
    """

    try:
        emblem_path = os.path.dirname(instance.emblem.path)
        shutil.rmtree(emblem_path)
        return
    except ValueError:
        pass
    try:
        banner_path = os.path.dirname(instance.banner.path)
        shutil.rmtree(banner_path)
    except ValueError:
        pass


def headquarter_image_delete(instance, model):
    """Функция для удаления изображения.

    Удаляет изображение для всех моделей - наследников Unit.
    :param instance: Экземпляр модели.
    """

    if instance.pk:
        try:
            old_instance = model.objects.get(pk=instance.pk)
            try:
                if old_instance.banner != instance.banner:
                    os.remove(old_instance.banner.path)
            except (ValueError, FileNotFoundError):
                pass
            try:
                if old_instance.emblem != instance.emblem:
                    os.remove(old_instance.emblem.path)
            except (ValueError, FileNotFoundError):
                pass
        except model.DoesNotExist:
            pass


def get_detachment_members_to_verify(detachment):
    user_ids_in_verification_request = (
        UserVerificationRequest.objects.values_list(
            'user_id', flat=True
        )
    )
    members_to_verify = detachment.members.filter(
        user__id__in=user_ids_in_verification_request
    ).select_related('user__media')
    return members_to_verify


def get_regional_hq_members_to_verify(regional_headquarter):
    return UserVerificationRequest.objects.filter(
            user__region=regional_headquarter.region,
        ).select_related('user__media')


def check_existing_record(engine, headquarter_id, user_id, position_id):
    """Проверка наличия записей членства ЦШ.

    Проверка используется для обхода ошибки при попытке через action админки
    добавить юзера, который уже есть в ЦШ. Юзер будет пропущен.
    """

    with engine.connect() as connection:
        query = text(
            'SELECT * FROM headquarters_usercentralheadquarterposition'
            ' WHERE headquarter_id = :headquarter_id AND user_id = :user_id'
        )
        result = connection.execute(
            query,
            {
                'headquarter_id': headquarter_id,
                'user_id': user_id,
                'position_id': position_id
            }
        )
        existing_record = result.fetchone()
        return existing_record is not None


def create_central_hq_member(
        headquarter_id,
        user_id,
        position_id=settings.DEFAULT_POSITION_ID,
        is_trusted=False,
):
    """Создание записи в таблице членов ЦШ прямым SQL-запросом."""

    if not settings.DEBUG:
        db_connection_string = f'postgresql://{os.getenv("POSTGRES_USER", "django").strip()}: \
                                {os.getenv("POSTGRES_PASSWORD", "django").strip()}@ \
                                {os.getenv("DB_HOST", "db").strip()}: \
                                {os.getenv("DB_PORT", 5432).strip()}/ \
                                {os.getenv("POSTGRES_DB", "django").strip()}'

    else:
        db_connection_string = 'sqlite:///_db.sqlite3'

    engine = create_engine(db_connection_string)

    if not check_existing_record(engine, headquarter_id, user_id, position_id):
        data = {
            'is_trusted': is_trusted,
            'headquarter_id': headquarter_id,
            'position_id': position_id,
            'user_id': user_id
        }
        df = pd.DataFrame([data])

        df.to_sql(
            'headquarters_usercentralheadquarterposition',
            engine,
            if_exists='append',
            index=False
        )

    engine.dispose()
