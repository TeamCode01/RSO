from regional_competitions.constants import ROUND_2_SIGNS, CONVERT_TO_MB
from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.viewsets import GenericViewSet


class RegionalRMixin(RetrieveModelMixin, ListModelMixin, CreateModelMixin, GenericViewSet):
    pass


class RegionalRMeMixin(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    pass


class FileScanSizeMixin():
    """Миксин для добавления свойств размера и типа файла
    к моделям с полем scan_file.

    Не забудь добавить поля file_size и file_type в сериализатор.

    file_size отображается в мегабайтах.
    """
    @property
    def file_type(self):
        return self.scan_file.name.split('.')[-1]

    @property
    def file_size(self):
        return round(self.scan_file.size / (CONVERT_TO_MB), ROUND_2_SIGNS)
