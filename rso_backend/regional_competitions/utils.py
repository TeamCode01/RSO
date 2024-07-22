from functools import wraps

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status


def swagger_schema_for_retrieve_method(serializer_cls):
    """Создает декоратор для метода retrieve, генерирующий Swagger схему."""

    def decorator(func):
        @swagger_auto_schema(responses={status.HTTP_200_OK: serializer_cls})
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        return wrapped

    return decorator


def swagger_schema_for_district_review(serializer_cls):
    def decorator(func):
        @swagger_auto_schema(methods=['PATCH'], request_body=serializer_cls)
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator


def swagger_schema_for_central_review(serializer_cls):
    def decorator(func):
        @swagger_auto_schema(methods=['PATCH', 'DELETE'], request_body=serializer_cls)
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator


def swagger_schema_for_create_and_update_methods(serializer_cls):
    def decorator(func):
        @swagger_auto_schema(request_body=serializer_cls)
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        return wrapped
    return decorator


def get_report_number_by_class_name(link):
    """
    Получает номер отчета для классов с названием,
    соответствующего шаблону `RegionalR<номер_отчета>`.
    """
    if link.__class__.__name__[10].isdigit():
        return link.__class__.__name__[9:11]
    return link.__class__.__name__[9]


def regional_comp_regulations_files_path(instance, filename) -> str:
    """Функция для формирования пути сохранения файлов конкурса РШ.

    :param instance: Экземпляр модели.
    :param filename: Имя файла. Добавляем к имени текущую дату и время.
    :return: Путь к изображению.
    Сохраняем в users/{user_id}/photo
    """
    filename = filename.split('.')
    return f'regional_comp/regulations/{instance.id}/{filename[0][:25]}.{filename[1]}'
