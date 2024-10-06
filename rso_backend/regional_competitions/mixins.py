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
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))

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
            if key.isdigit():
                key = int(key)

            if i == len(keys) - 1:
                value = self.process_value(value)
                current[key] = value
            else:
                if isinstance(key, int):
                    if not isinstance(current, list):
                        current[keys[i - 1]] = []
                        current = current[keys[i - 1]]
                    while len(current) <= key:
                        current.append({})
                    current = current[key]
                else:
                    if isinstance(current, dict):
                        if key not in current:
                            current[key] = {}
                        current = current[key]
        return data

    def process_value(self, value):
        """
        Обрабатывает значение, проверяя, является ли оно ссылкой на существующий файл в /media/.

        :param value: Значение для проверки.
        :return: Файл или исходное значение.
        """
        if isinstance(value, str) and '/media/' in value:
            file_object = self.get_file_from_media(value)
            if file_object:
                return file_object
        return value

    def get_file_from_media(self, link):
        """
        Пытается найти файл на сервере в папке /media/.

        :param link: Ссылка на файл.
        :return: Объект файла или None, если файл не найден.
        """
        media_url = settings.MEDIA_URL
        if media_url.endswith('/'):
            media_url = media_url[:-1]


        parsed_link = urlparse(link)
        link_path = parsed_link.path

        if link_path.startswith(media_url):
            relative_path = link_path[len(media_url):]

            if relative_path.startswith('/'):
                relative_path = relative_path[1:]

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
                        return uploaded_file
                except IOError as e:
                    pass
        return None

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
        return self.remove_duplicate_keys(data)

    def update(self, request, *args, **kwargs):
        """
        Переопределяет метод обновления, обрабатывая QueryDict перед передачей в сериализатор.

        :param request: Запрос с данными.
        :return: Ответ с данными после обновления.
        """
        data = self.parse_querydict(request.data)
        serializer = self.get_serializer(self.get_object(), data=data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Переопределяет метод создания, обрабатывая QueryDict перед передачей их в сериализатор.

        :param request: Запрос с данными.
        :return: Ответ с созданными данными.
        """
        data = self.parse_querydict(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data)
