import re
from django.http import Http404
from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.viewsets import GenericViewSet
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
                current[key] = value
            else:
                if isinstance(key, int):
                    if not isinstance(current, list):
                        current = current.setdefault(keys[i - 1], [])
                    while len(current) <= key:
                        current.append({})
                    current = current[key]
                else:
                    if isinstance(current, dict):
                        if key not in current:
                            current[key] = {}
                        current = current[key]
        return data

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
        Переопределяет метод создания, обрабатывая QueryDict перед передачей в сериализатор.

        :param request: Запрос с данными.
        :return: Ответ с созданными данными.
        """
        data = self.parse_querydict(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data)
