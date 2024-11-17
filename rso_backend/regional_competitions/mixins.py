import re
import os
from urllib.parse import urlparse, unquote

from django.http import Http404
from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.viewsets import GenericViewSet
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from rest_framework.response import Response

from headquarters.models import RegionalHeadquarter
from regional_competitions.utils import get_report_number_by_class_name


class RegionalRMixin(RetrieveModelMixin, CreateModelMixin, GenericViewSet):

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get('pk')
        objects = queryset.filter(regional_headquarter_id=pk)
        if objects.exists():
            latest_object = objects.order_by('-id')[0]
            return latest_object
        raise Http404("Страница не найдена")

    def get_report_number(self):
        return get_report_number_by_class_name(self)

    def perform_create(self, serializer):
        regional_hq = RegionalHeadquarter.objects.get(commander=self.request.user)

        if 'verified_by_dhq' in serializer.Meta.fields:
            existing_reports = self.get_queryset().filter(regional_headquarter=regional_hq)
            verified_by_dhq = existing_reports.exists()
            print(f'{verified_by_dhq=}')
            serializer.save(
                regional_headquarter=regional_hq,
                verified_by_dhq=verified_by_dhq
            )
        else:
            serializer.save(regional_headquarter=regional_hq)

    def perform_update(self, request, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))


class RegionalRMeMixin(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    pass


class ListRetrieveCreateMixin(RetrieveModelMixin, CreateModelMixin, ListModelMixin, GenericViewSet):
    pass


class FormDataNestedFileParser:
    """
    Миксин для обработки вложенных данных при отправке их при помощи multipart/form-data content-type.
    """

    def extract_keys(self, key):
        """
        Извлекает ключи из строкового представления вложенного ключа, например, 'events[0][links][0][link]'.

        :param key: Ключ из QueryDict.
        :return: Список ключей.
        """
        return re.findall(r'([^\[\]]+)', key)

    def assign_value(self, data, keys, value):
        """
        Присваивает значение в словарь или список, используя извлеченные ключи.

        :param data: Словарь для обновления.
        :param keys: Список ключей.
        :param value: Значение, которое нужно присвоить.
        :return: Обновленный словарь или список с присвоенным значением.
        """
        current = data
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            if key.isdigit():
                key = int(key)

            if is_last:
                value = self.process_value(value)
                if isinstance(current, list) and isinstance(key, int):
                    while len(current) <= key:
                        current.append(None)
                    current[key] = value
                else:
                    current[key] = value
            else:
                next_key = keys[i + 1] if i + 1 < len(keys) else None

                next_is_index = isinstance(next_key, int) or (isinstance(next_key, str) and next_key.isdigit())

                if isinstance(key, int):
                    if not isinstance(current, list):
                        if isinstance(current, dict):
                            if key in current:
                                temp = current[key]
                            else:
                                temp = {}
                            current = [temp] if key == 0 else [{} for _ in range(key)] + [temp]
                            data[keys[0]] = current
                        else:
                            current = []
                            data[keys[0]] = current

                    while len(current) <= key:
                        current.append({})
                    current = current[key]
                else:
                    if key not in current or not isinstance(current[key], (dict, list)):
                        current[key] = [] if next_is_index else {}
                    current = current[key]
        return data

    def process_value(self, value):
        """
        Обрабатывает значение, проверяя, является ли оно ссылкой на существующий файл в /media/.
        """
        if not hasattr(self, 'files_to_delete'):
            self.files_to_delete = []

        if isinstance(value, str) and '/media/' in value:
            result = self.get_file_from_media(value)
            if result:
                uploaded_file, file_path = result
                self.files_to_delete.append(file_path)
                return uploaded_file
        return value

    def get_file_from_media(self, link):
        media_url = settings.MEDIA_URL.rstrip('/')
        parsed_link = urlparse(link)
        link_path = parsed_link.path

        if link_path.startswith(media_url):
            relative_path = link_path[len(media_url):].lstrip('/')
            relative_path = unquote(relative_path)
            file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        file_name = os.path.basename(file_path)
                        file_content = f.read()
                        uploaded_file = SimpleUploadedFile(
                            name=file_name,
                            content=file_content,
                            content_type='application/octet-stream'
                        )
                    return uploaded_file, file_path
                except IOError as e:
                    print(f"Ошибка при чтении файла {file_path}: {e}")
            else:
                print(f"Файл не найден по пути: {file_path}")
        else:
            print("Путь ссылки не начинается с MEDIA_URL")
        return None

    def delete_old_files(self):
        """
        Удаляет старые файлы, пути к которым хранятся в self.files_to_delete.
        """
        for file_path in getattr(self, 'files_to_delete', []):
            try:
                os.remove(file_path)
                print(f"Удален файл: {file_path}")
            except OSError as e:
                print(f"Ошибка при удалении файла {file_path}: {e}")
        self.files_to_delete = []

    def remove_duplicate_keys(self, data):
        """
        Рекурсивно удаляет дублирующиеся ключи внутри структуры данных.

        :param data: Словарь или список для обработки.
        :return: Обновленный словарь или список без дублирующихся ключей.
        """
        if isinstance(data, dict):
            for key, value in list(data.items()):
                data[key] = self.remove_duplicate_keys(value)
                if isinstance(value, dict) and key in value:
                    data[key] = value[key]
        elif isinstance(data, list):
            data = [self.remove_duplicate_keys(item) for item in data]
        return data

    def parse_querydict(self, query_dict):
        """
        Парсит QueryDict, извлекая вложенные данные и удаляя дублирующиеся ключи.

        :param query_dict: QueryDict с данными из запроса.
        :return: Очищенный от дублирующихся ключей словарь с данными.
        """
        data = {}
        for key, value in query_dict.items():
            keys = self.extract_keys(key)
            data = self.assign_value(data, keys, value)
        result = self.remove_duplicate_keys(data)
        return result

    def update(self, request, *args, **kwargs):
        """
        Переопределяет метод обновления, обрабатывая QueryDict перед передачей в сериализатор.
        """
        self.files_to_delete = []
        data = self.parse_querydict(request.data)
        serializer = self.get_serializer(self.get_object(), data=data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        self.delete_old_files()
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Переопределяет метод создания, обрабатывая QueryDict перед передачей их в сериализатор.
        """
        self.files_to_delete = []
        data = self.parse_querydict(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        self.delete_old_files()
        return Response(serializer.data)
