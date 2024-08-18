from functools import wraps
from io import BytesIO
from urllib.parse import unquote

from django.core.exceptions import FieldDoesNotExist
from django.core.files.base import ContentFile
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from openpyxl import Workbook
from rest_framework import status

# from regional_competitions.r_calculations import calculate_r5_score
from rest_framework import serializers


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
    if link.__class__.__name__[11].isdigit():
        return link.__class__.__name__[9:12]
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
    return f'regional_comp/regulations/{instance.__class__.__name__}/{instance.regional_headquarter.id}/{filename[0][:25]}.{filename[1]}'


def get_verbose_names_and_values(serializer):
    """Возвращает словарь с названиями полей и значениями полей из сериализатора."""

    verbose_names_and_values = {}
    model_meta = serializer.Meta.model._meta
    instance = serializer.instance

    for field_name in serializer.Meta.fields:
        field = serializer.fields[field_name]
        field_value = getattr(instance, field_name, None)

        if isinstance(field, serializers.ListSerializer):
            # Если поле является списком сериализаторов (many=True)
            nested_serializer_class = field.child.__class__
            nested_verbose_names_and_values = []

            for nested_instance in field_value.all():  # Проходим по всем связанным объектам
                nested_serializer = nested_serializer_class(nested_instance)
                nested_verbose_names_and_values.append(get_verbose_names_and_values(nested_serializer))

            verbose_names_and_values[field_name] = nested_verbose_names_and_values

        elif isinstance(field, serializers.ModelSerializer):
            # Если поле является вложенным сериализатором (один объект)
            nested_serializer = field.__class__(field_value)
            nested_verbose_names_and_values = get_verbose_names_and_values(nested_serializer)

            for nested_field_name, nested_verbose_name_and_value in nested_verbose_names_and_values.items():
                verbose_names_and_values[f"{field_name}.{nested_field_name}"] = nested_verbose_name_and_value

        else:
            try:
                verbose_name = model_meta.get_field(field_name).verbose_name
                if hasattr(field_value, '__str__'):
                    field_value = str(field_value)
                verbose_names_and_values[field_name] = (verbose_name, field_value)
            except FieldDoesNotExist:
                pass
            except AttributeError:
                verbose_names_and_values[field_name] = (field_name, field_value)

    return verbose_names_and_values


def get_headers_values(fields_dict: dict, prefix: str = '') -> dict:
    """Формирует плоский словарь для заголовков и значений листа Excel."""

    #TODO: убрать полный путь для названий файлов
    #TODO: True, False и None заменить на человекочитаемые значения
    flat_dict = {}

    for value in fields_dict.values():
        if isinstance(value, list):
            for item in value:
                nested_prefix = f'{prefix}{item["id"][0]}_{item["id"][1]}.'
                nested_dict = get_headers_values(fields_dict=item, prefix=nested_prefix)
                flat_dict.update(nested_dict)
        elif isinstance(value, tuple):
            flat_dict[f'{prefix}{value[0]}'] = value[1]

    return flat_dict


def get_report_xlsx(self):
    """Выгрузка отчёта в формате Excel."""
    serializer = self.get_serializer(self.get_object())
    flat_data_dict = get_headers_values(
        get_verbose_names_and_values(serializer)
    )
    title = self.get_report_number()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = title

    worksheet.append(list(flat_data_dict.keys()))
    worksheet.append(list(flat_data_dict.values()))

    file_content = BytesIO()
    workbook.save(file_content)
    file_content.seek(0)
    response = HttpResponse(
        file_content.read(),
        content_type=(
            'application/vnd.openxmlformats-officedocument'
            '.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = (f'attachment; filename={title}.xlsx')
    return response
